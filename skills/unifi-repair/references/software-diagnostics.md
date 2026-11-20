# Software and console diagnostics

Contents: serial console · U-Boot · boot-log triage · SSH on UniFi OS · "works but misbehaves" faults · eMMC cloning · SPI flash and EEPROM · LCM touchscreen · switches · stress and soak tests

## Serial console

Almost everything is 115200 8N1, 3.3 V logic, header GND/TX/RX/3V3 (never connect the 3V3 pin). Per-device ports and logins are in `devices.md`.

Drive the port yourself with whatever serial tool your agent has: a serial MCP server (open / send-and-expect / wait-for / log / close), or `python -m serial.tools.miniterm`, `picocom`, or a short pyserial script. The steps below name the operation, not a specific tool.

- Before opening: `lsof /dev/cu.usbserial-* 2>/dev/null; ps -axo pid,command | grep '[s]creen'`. If the user's `screen` holds the port, ask them to quit it with Ctrl-A k y (typing `exit` logs out the device's root shell instead). Never touch a port held by another project's process.
- The user also logs with `screen -L`, which leaves `screenlog.0` in the unit folder. Read those before asking for a new capture. A log that is all binary noise was captured at the wrong baud.
- Stop autoboot: wait for `Autobooting in|Hit Esc key` and answer with two Esc bytes (`1b 1b`), with a timeout of about 90 s, then power-cycle (ask the user to).
- At a Linux shell, first `export TERM=dumb; stty cols 250` to stop line-wrap garbage. Wrap each command with a sentinel so you know it finished: `cmd; echo E7`, then wait for `E7` on its own line (or `login:`).
- Start logging to a file before the first power-on after a repair; the first boot is the one you can't repeat.
- Close the port when done, every time; a held port blocks the user's own terminal.

Pulling a file off a device with no network, over the UART: start logging, send `stty -echo; echo ==B64BEGIN==; xz -9c FILE | base64; echo ==B64END==; stty echo`, then strip the logger's timestamps and decode (`sed -E 's/\[20[0-9]{2}-..-..T[0-9:.]+\] //g' | tr -d '\r\n' | base64 -d | xz -dc`) and compare md5 on both ends. About 10 KB/s.

## U-Boot

Read-only commands are safe to run without asking: `version`, `bdinfo`, `printenv`, `pci`, `i2c bus`, `i2c dev N; i2c probe`, `i2c md <addr> 0.2 100`, `usb start`, `usb tree`, `usb storage`, `mmc info`, `sf probe`, `printsys`.

Ask before anything that writes: `saveenv`, `sf write/erase`, `mmc write`, `urescue`, `bootm` of a different image to flash.

- I2C mux isolation: probe one channel, then re-probe the parent bus (`i2c dev 2; i2c probe; i2c dev 0; i2c probe`). `Timed out waiting for bus` / `mux disconnect error` means that channel hangs the bus; a power cycle is needed to recover.
- On a board with a dying USB-attached eMMC, `usb reset` can wedge XHCI into a reset loop. Use a single `usb start`.
- Booting the alternate firmware bank from RAM tests the other image with no flash write (Realtek switches): `sf probe 0; sf read 0x81000000 <bank_offset> <size>; iminfo 0x81000000; bootm 0x81000000`.

## Boot-log triage

Compare against a known-good log for the same model before interpreting anything: a unit folder's earlier good boot, or the references listed in `devices.md`. Line up the same fields side by side (preload/EEPROM ID, DRAM size, PCIe links, network devices, storage) for the bad boot, the good boot, and after each change. Many alarming lines are present on healthy units; the device sections list the known-benign ones.

General reading:

- No output at all: the first-stage loader never ran (rails, DDR, SPI flash), or wrong baud/pins. DDR is initialised before the UART on Alpine, so dead DDR is silent.
- Loader prints but hardware inventory is wrong (half the RAM, no PCIe, no ethernet, ID 0000): straps or the I2C preload are being corrupted. Look for a damaged peripheral on a shared bus before suspecting the SoC.
- U-Boot fine, storage not found or controller timeouts: the boot storage device or its bridge.
- Kernel panic naming a driver's read function: that peripheral is missing or dead (e.g. an absent PHY).
- Kernel and rootfs fine, services failing: software state (cloned data, a full or corrupt partition). Factory reset before hardware theories.

## SSH on UniFi OS consoles (UDM Pro / SE)

- LAN side only: `root@192.168.1.1` (default password `ui` before setup; afterwards set under Settings → Control Plane → Console → SSH). The WAN port drops SSH unless a WAN→Gateway TCP/22 rule exists on the unit.
- The user installs a key once (`ssh-copy-id -i <pubkey> root@<ip>`); you then use `ssh -o BatchMode=yes`. Password SSH also trips PAM rate limits under repeated logins. Remove the key from `authorized_keys` at the end and confirm login is refused.
- First look:
  ```
  ubnt-device-info summary
  dmesg -T | grep -iE "mmc|error|fail|i/o|ext4|oom|usb|xhci"
  lsblk -b -o NAME,SIZE,TYPE,MODEL,VENDOR,TRAN ; mount | grep -E ' ro,|/boot|/data'
  systemctl --failed ; journalctl -p err -b --no-pager | tail -50
  smartctl -a /dev/sda ; sensors
  cat /sys/fs/pstore/console-ramoops-0 ; cat /var/log/reboot-time.log
  ```
- Boot storage shows up as `/dev/boot`, an eMMC behind a USB bridge, so eMMC wear registers (`life_time`, `pre_eol_info`) are not readable from Linux.
- Run long jobs as transient units so they survive an SSH drop: `systemd-run --unit=readtest --nice=19 -p IOSchedulingClass=idle sh -c "dd if=/dev/boot of=/dev/null bs=1M iflag=direct"`, then `journalctl -u readtest`.

## "Works, then misbehaves" faults

For faults like the front panel showing "unable to retrieve status" after hours:

1. Find what produces the message. The LCD daemon is `ulcmd`, log `/var/log/ulcmd.log`. Strings in the binary show its states: `grep -aoE '[[:print:]]{5,}' /usr/bin/ulcmd | grep -i <word>`.
2. Reproduce the state deliberately to learn its trigger (stopping `unifi-core` for 60 s gives `error.os`, the "unable to retrieve status" screen). That turns a vague symptom into "what makes unifi-core unreachable".
3. Check the usual causes in order: memory pressure (`journalctl -u earlyoom | grep "sending SIG"`; earlyoom, not the kernel OOM killer, does the killing, and it can leave `postgresql@14-main` down with dependents crash-looping), storage errors or read-only remounts, thermal, then load-dependent hardware (PoE budget under real load).
4. If it doesn't reproduce in the session, set up a soak with logging and state plainly which hypotheses remain untested.

## eMMC cloning (UDM Pro)

For a unit whose eMMC is dead, clone from a working unit of the same model. Identity (MAC, serial) lives in SPI/EEPROM, not on the eMMC, so the clone boots with the target's own identity; factory-reset it afterwards.

1. On the working unit: `ssh root@ip 'sfdisk -d /dev/boot' > partitions.txt`, then `ssh root@ip 'dd if=/dev/boot bs=4M 2>/dev/null' > udmpro-boot.img`. Ask where to put it; images are 15 GB and the internal disk is tight (earlier ones are on `/Volumes/Main/udm-pro-emmc/`).
2. Verify the read-only region by hash on both ends (boot + recovery + root, the first ~2145 MiB; the rest changes while running).
3. Program the donor chip in Xgpro on the T76: eMMC options dialog (not File→Open), single-file mode, User Area only, BOOT1/BOOT2/RPMB/ECSD unticked, verify on, 50 MHz HS. Check ECSD wear bytes (0x10B pre-EOL, 0x10C/0x10D life) on a used donor first.
4. Compare Xgpro's checksum (a plain 32-bit byte sum) with the image's.
5. Solder, capture the first boot on the UART, factory reset.

T76 in the UTM VM: keep the VM window frontmost for the whole write and verify, or it times out and needs a replug. Files over 4 GB don't cross the WebDAV share; serve them from the Mac (`python3 -m http.server` on 192.168.64.1) and fetch with `curl.exe` in the VM.

A dead eMMC on an SD-reader adapter shows as an MMC card with manufacturer ID 0x00 and 0 bytes (`system_profiler SPCardReaderDataType`): it answered CMD1 and never initialised.

## SPI flash and EEPROM

CH341A with a SOIC-8 clip, board unpowered. Read twice and compare hashes before trusting a dump; keep dumps in the unit folder.

```
flashrom -p ch341a_spi -c "<chip>" -r dump1.bin && flashrom -p ch341a_spi -c "<chip>" -r dump2.bin && shasum dump1.bin dump2.bin
```

1.8 V parts (MX25U...) need the 1.8 V adapter. I2C EEPROMs (AT24C64) use the CH341A in I2C mode (`ch341eeprom`, built in `~/dead-udm/ch341eeprom/`). Good dumps from one unit are a reference and a recovery source for the next of the same model; `devices.md` says where they are.

## LCM touchscreen (UDM Pro / SE front panel)

STM32F205, USB-CDC to the main board. USB IDs: `1f9b:157d` running, `0483:df11` in ST ROM DFU. On the Mac: `ioreg -p IOUSB -l -w0 | grep -E '"USB Product Name"|"idVendor"|"idProduct"'`.

| Symptom | Cause |
|---|---|
| Screen shows "touchscreen update failed"; log has `LCM FW hash mismatch` → `Custom DFU entry` ×6 → `Could not update LCM` | ulcmd can't put the MCU into DFU: the RESET/BOOT lines from the main board aren't reaching it |
| Black screen, no backlight, LCM log `tp i2c read error / FTS_REG_CHIP_ID` | Panel flex loose on the LCM board; reseat |

Telling firmware from hardware: temporarily bind-mount a matching hash over `/usr/share/firmware/udm-pro-lcm-fw.hash` so ulcmd skips the update, see whether the screen works, then unmount.

Manual flash from the Mac: bridge the "UB" pads (BOOT0) and plug the LCM's USB in, then
```
dfu-util -a 0 -s 0x08000000:1048576 -U lcm-backup.bin        # back up first
dfu-util -a 0 -s 0x08000000 -D udm-pro-lcm-fw.bin
dfu-util -a 0 -s 0x08000000:1048576 -U readback.bin && cmp   # verify
```
The firmware image is `/usr/share/firmware/udm-pro-lcm-fw.bin` on the device (also inside the UniFi OS squashfs). `udm-gd-lcm-fw.bin` is for different hardware. Protocol and RE notes: `~/unifi-touchscreens/protocol.md`.

## Switches

- Realtek-based (USW-48-PoE): login `ubnt`/`ubnt` after reset. `swctrl port show`, `swctrl poe show`, `swctrl env show`, `info`, `cat /proc/mtd`, `dmesg | grep -i poe`, `set-inform http://<controller>:8080/inform`.
- "No link on any port" at the bench: check the upstream switch first (BPDU guard error-disabled the port once). `rtk phymmd` failures in U-Boot are not evidence of dead PHYs.
- PoE `Chip Type 0xff / Error not supported chip type`: the PSE controller is unpowered (54 V absent or the PoE board detached), expected in that state.
- Broadcom-based (USW-Pro-48): `urescue` is TFTP recovery; holding reset over 5 s clears config.

## Stress and soak tests

Working scripts from the UDM SE repair are in `~/udm-pro-se-repair/`. Copy and adapt them into the unit folder; they have that unit's host, key path, and device names hardcoded.

| Script | Does | Adapt |
|---|---|---|
| `emmc_stress.sh` | Writes and sha256-verifies random data on `/data` with direct I/O, cleans up | Runs as is on UniFi OS consoles |
| `load_stress.py` | CPU burn, SSD read scan, RAM pattern test, temperature sampling | Sensor labels and `/dev/sda`. It uses `pkill` on the device; never run it on the Mac |
| `oom_test.py` | Applies memory pressure until the LCD state or `unifi-core` changes | Postgres and `unifi-directory` may need a restart afterwards |
| `monitor.sh` | Mac-side loop: SSH every 5 min, log mounts, failed units, earlyoom, LCD state, memory, temps, dmesg errors | Host, key path, the hardcoded `--since` epoch. Run under `caffeinate` or the Mac's sleep leaves gaps. Stop it when the soak ends |

Say what each test covered and what it did not (an eMMC and RAM pass says nothing about a PoE-load fault).
