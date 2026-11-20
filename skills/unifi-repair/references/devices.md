# Device notes

Model-level facts and where each unit's records live. Unit status changes; the unit folder's notes are the current truth, so read them and treat the summaries here as orientation. Add to this file when a repair establishes something reusable about a model.

Contents: where things are · UDM Pro · UDM Pro SE · U6 Pro · USW-48-PoE · USW-Pro-48-PoE · USW-EnterpriseXG-24 · marking decoder

## Where things are

| Folder | Unit(s) | Has |
|---|---|---|
| `~/dead-udm` | UDM Pro #1 (lost to torn eMMC pads) | Known-good dumps of all four flash chips, `ch341eeprom` build |
| `~/udm-pro-repairs` | UDM Pro eBay unit (113-723-10); `new1029/` = second unit (113-723-11) | Boot logs (bad, PHY-removed, good), annotated photos, LCM firmware v2.5.1 backup and v2.5.7 |
| `~/udm-pro-se-repair` | UDM Pro SE | Stress and monitor scripts, monitor log. Contains a private key (`udm_key`): never read or print it |
| `~/u6-repair` | U6 Pro boards 1-3 | Pinout photo; worksheet pages linked from its notes |
| `~/usw-48-poe-repair` | USW-48-PoE (non-Pro) | `NOTES.md`, photos, `digikey-bom.csv`, boot logs |
| `~/usw-48-repair` | USW-Pro-48-PoE | `docs/` reference set with [V]/[I]/[?] tags, blank `measurements.md` |
| `~/usw-enterprise-24` | USW-EnterpriseXG-24 | Marked-up photos, `guide/` worksheet |
| `~/unifi-touchscreens` | LCM coprocessor RE | `protocol.md`, firmware, probe scripts |

These folders are the original author's layout; on another machine, keep the same one-folder-per-unit convention and treat this table as an example. If your agent keeps per-project memory or searchable chat history, check it for a part number or reading before asking the user to repeat it.

## UDM Pro (UDM-Pro, board "alpine_v2_ubnt udm-pro")

- SoC Annapurna Alpine AL-324, 4 GB DDR4, eMMC Samsung KLMAG1JETD-B041 (16 GB, BGA-153) behind a USB bridge on an ASM1142 XHCI controller (PCIe 1b21:1142). Switch RTL8370MB. WAN PHY U51 AR8033-AL1A (AR8031/AR8035 share the package; AR8035 has no SGMII). Fan controller ADT7475.
- Flash: MX25U6435F 8 MB **1.8 V** by the CPU (al_boot, U-Boot, DTBs, env); AT24C64 EEPROM at I2C 0x57 (boot stage 3, device ID, keys); MX25L1608E underside (switch firmware); W25X05CL (board management). Good dumps: `~/dead-udm/dump-*.bin`.
- Boot chain: BootROM → SPI stage2 → EEPROM preload → U-Boot 2015.07 → kernel from eMMC.
- I2C bus 0: 0x28 PCA9575 GPIO expander (drives LCM RESET/BOOT), 0x57 EEPROM, 0x71 mux (a PCA9546A marked "PW546A": 4 channels; ADT7475 on channel 3).
- UART 115200. U-Boot prompt `UBNT_UDM_ALL>` or `ALPINE_UBNT_UDM_ALL>` depending on build; Esc Esc at "Autobooting".
- Known-good U-Boot log: `curl -sL https://gist.githubusercontent.com/rickmark/f84cc36a7ddf3dd9d76dd9c231855447/raw` (ends at autoboot; no userspace). Also blog.rickmark.me for the boot chain, ui.com/download for firmware, FCC ID SWX-UDMPRO for internal photos.
- Recovery: TFTP recovery mode at 192.168.1.20; eMMC clone procedure in `software-diagnostics.md`. Clone image: `/Volumes/Main/udm-pro-emmc/udmpro-boot.img`.

Boot-log signatures:

| Log | Meaning |
|---|---|
| `EEPROM Revision ID = 39`, `Device ID = a324`, `DRAM: 4 GiB`, PCIE_0 link to `1b21:1142`, `RTL8370B`, `2 USB Device(s) found` | Healthy board |
| `I2C Preload Disabled!`, Device ID `0000`, `DRAM: 2 GiB`, `PCIE_n no link`, `No ethernet found`, `Bootstraps / DT / Capabilities Mismatch!` | Straps/preload corrupted by something on a shared net. Was a surge-damaged AR8033 WAN PHY, then a bad joint on its replacement. Not the eMMC or EEPROM |
| `Could not attach to PHY`, then `SError ... al_mod_eth ... mdio_read` panic | WAN PHY absent |
| `2 USB Device(s) found` then `Bad device usb 0`; later `XHCI timeout on event type 33 ... BUG! resetting` in a loop | eMMC dead behind the USB bridge |
| `bad CRC, using default environment`, `SATA link 0-3 timeout`, `File not found select-image-1` | Benign |
| Fans 100%, LCD "booting" then "taking too long", no UART at all | SoC never started: DDR or SPI, not eMMC |

Common eBay failures are eMMC (fixable) and WAN surge damage (TVS D1671, magnetics T8, U51). After a clone or a previous owner's config: factory reset.

## UDM Pro SE

- Same family, adds PoE (BCM59121 PSE at I2C 5-0020, sysfs `/sys/bus/i2c/devices/5-0020/poe/`). eMMC is `/dev/boot` behind a Genesys 05e3:0749 bridge; the internal SSD is M.2 SATA.
- LCD "UNABLE TO RETRIEVE STATUS" = ulcmd state `error.os` = `unifi-core` unreachable for 60 s. Log chain: `ConsoleStatus stream failed` → `UCore timeout 60 sec` → `Set state: error.os`.
- Under memory pressure earlyoom kills `unifi`, `beam.smp`, and Postgres backends; `postgresql@14-main` can stay down afterwards.
- `persistent_ram: uncorrectable error in header` is likely benign.

## U6 Pro (PoE front end)

Two PCB generations with different PD controllers:

- **Later rev: MP8009** PD controller. Flyback transformer OEM-marked "EP13 604 2517L" (not a catalogue part; Bourns SM13117EL chosen as the architectural match, pending pad checks: primary 3-4, aux 1-2, paralleled secondaries). Sense resistor 0.1 Ω 1% 1206. Bulk cap CapXon 18 µF/63 V. Six identical bidirectional TVS marked "105J" around the front end (replace with SMAJ58CA class).
- **Earlier rev (©2022 "U6_PRO" silk): U18 = TI LM5072MH-80.** Pins: 1 RT, 2 SS, 3 VIN, 4 RCLASS, 5 ICL_FAUX, 6 DCCL, 7 VEE, 8 RTN, 9 OUT, 10 VCC, 11 nPGOOD, 12 CS, 13 RAUX, 14 FB, 15 COMP, 16 ARTN, pad = VEE. Pin 1 is by the U18 silk dot. UVLO on 38.5 V; VCC 7.7 V with a 15 mA limit; inrush limit 150 mA; internal ~24.5 kΩ signature resistor across VIN-VEE; 0.7 Ω hot-swap switch that limits at ~440 mA (why U18 runs hot into a downstream short).
  - Q4 primary FET (bottom): CYStek MTE050N15BRV8, marked "E050N 15BR", 150 V DFN5x6. Substitute used: Infineon BSC360N15NS3GATMA1.
  - D12 "RG" SMB input TVS [I]; C322 bulk (top) plus C340/C470 MLCCs; T2 "EP13 115 2239"; D7 10T100 Schottky; C325 560 µF/6.3 V output (so a ~5 V output [I]); clamp D10 "F1M", R214 51 Ω, C329/C330; sense R217/R219; opto U19.

Failures seen: flyback transformer primary burnt open with a carbon path into the aux winding; one of the six TVS shorted; primary FET shorted; an output-side MLCC shorted. Sibling units on the same cable run died in the same surge, so check all of them for the same parts.

Substitute rule learned here: check the pad map against the substitute's pinout and run the full cold-check list (clamp, gate drive, sense path, transformer, output) before first power. Two replacement FETs burned when those were skipped.

## USW-48-PoE (non-Pro; Realtek RTL8393, MIPS, 16 MB SPI NOR)

The Pro's notes do not apply to this model.

- 54 V PSU → isolated 54 V→12 V active-clamp forward converter: controller U5081 UCC2897A; primary FET Q17 (CYStech MTE65N20H8, marked "E65/N20", 200 V); secondary sync FETs Q13/Q14 (Wayon WMB198N15HG, marked "B198N15H", 150 V); P-channel clamp FET Q8 on the underside (CYStech MTE1K0P25, "E1K0 P25"); sense R6453/R6455 0.15 Ω each.
- Replacements chosen: Q17 ISC300N20NM6ATMA1, Q13/Q14 BSC160N15NS5ATMA1, Q8 FQD7P20TM.
- UART `/dev/cu.usbserial-0001`-style adapter, 115200; login `ubnt`/`ubnt`. U-Boot prompt `uboot>`, Esc at "Hit Esc key".
- Expected with 54 V absent or the PoE board detached: `PoE ... Chip Type 0xff / Error not supported chip type`. Likely benign: `port 48-51 patch ready fail 0`.

## USW-Pro-48-PoE (Broadcom)

Reference set in `~/usw-48-repair/docs/` (hardware overview, power architecture, PoE subsystem, boot and flash, measurements log). Console 115200 8N1 3.3 V; a second header carries the PoE MCU link at 19200. PSE chips BCM59111/59121. `mtdparts=spi1.0:1920k(u-boot),64k(u-boot-env),64k(shmoo),31168k(kernel0),31232k(kernel1),1024k(cfg),64k(EEPROM)`.

## USW-EnterpriseXG-24 (board 11-03112-06)

- Main SoC U14 (Broadcom switch SoC), DDR4 U9/U12 (Samsung K4A8G16WC-BCTD), SPI flash MX66L51235F on the underside.
- Buck U16 (SOT-23-6 "6DW", L17, C123 100 µF polymer) and its twin U21 (L18, C144). The U16 rail feeds U14 through ferrites (F1 top side, F50 underside), not just RAM.
- Unit history: U16 rail shorted at 6 Ω; isolated by lifting down to a branch behind F1 that stays shorted with all its caps off and is linked to the main rail by something other than F1. Most likely inside U14 [I]; decoupling under U14 not ruled out. No UART or software work was possible.
- Twin-rail reference readings: diode mode climbing one way, ~0.476 V the other.

## Marking decoder

| Marking | Part |
|---|---|
| PW546A | TI PCA9546A I2C mux |
| E050N 15BR | CYStek MTE050N15BR (150 V N-FET) |
| E65 / N20 | CYStech MTE65N20H8 (200 V N-FET) |
| E1K0 P25 | CYStech MTE1K0P25 (250 V P-FET) |
| B198N15H | Wayon WMB198N15HG (150 V N-FET) |
| 10T100 | 10 A 100 V Schottky |
| F1M | 1 A 1000 V fast diode (RS1M class) |
| 105J (black SMA) | bidirectional TVS on the PoE input, SMAJ58CA class [I] |
| RG (SMB) | 58 V-class TVS [I] |
| 4R7 | 4.7 µH inductor |
| 510 / 4R7 / 100 on a resistor | 51 Ω / 4.7 Ω / 10 Ω |
| SEC ... B041 KLMAG1JETD | Samsung 16 GB eMMC |
| Toshiba eMMC suffix G5 / G6 / G7 | 4 / 8 / 16 GB |
| 6DW (SOT-23-6) | Buck regulator, not identified [?] |
| YE04 / YF04E | TXB0104 / TXS0104E level shifter [I] |
