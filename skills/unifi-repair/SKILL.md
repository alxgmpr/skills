---
name: unifi-repair
description: Board-level repair and diagnostics for Ubiquiti UniFi hardware (UDM Pro / SE, U6 and other APs, USW switches, PoE front ends, LCM touchscreens). Use whenever the user is fixing, probing, or diagnosing a UniFi device at the bench or over a console - a dead or boot-looping unit, a hot chip, a shorted rail, a smoked FET, PoE faults, UART / U-Boot / SSH diagnostics, eMMC or SPI flash work, "unable to retrieve status" style software faults, identifying a part from its marking, or finding a replacement part. Also use when the user sends a board photo and asks where to measure, asks for a test guide / checklist / interactive page for bench testing, asks for a DigiKey part or BOM, or works in a device repair folder (u6-repair, udm-pro-repairs, usw-48-poe-repair, ...), even if they never say "UniFi" or "repair".
---

# UniFi repair

The user repairs UniFi gear, often bought dead or surge-damaged. They do the hands-on work (meter, hot air, programmer); you plan the measurements, read the results, drive the consoles, find parts, and keep the notes. The four things this skill adds over general knowledge are the bundled tools below and the working rules, which come from corrections he gave in earlier repairs.

## Tools in this skill

| Need | Use | Read first |
|---|---|---|
| Show where to probe on the photo | `scripts/annotate.py` (grid crop to find coordinates, then draw) | `references/photo-annotation.md` |
| A guided set of bench measurements with live pass/fail | `assets/bench-worksheet.html`, filled in and opened or published | `references/bench-worksheet.md` |
| Stock, price, specs, DigiKey part numbers, BOM | `scripts/dk.py` (DigiKey API) | `references/parts-sourcing.md` |
| UART / U-Boot / SSH / flash / eMMC / LCM work, log signatures | a serial console tool, ssh | `references/software-diagnostics.md` |
| Shorted rails, PoE front ends, FET substitution, first power-up | - | `references/fault-finding.md` |
| What is already known about a model or a specific unit | - | `references/devices.md` |

## Start of a session

1. Find the unit. Each physical unit has its own folder (`~/u6-repair`, `~/udm-pro-repairs/new1029`, ...). A new unit gets a new folder; don't merge it into another unit's notes, and name the unit explicitly whenever two are in play (which board the donor part is for, which one the log came from).
2. Read what exists before asking or guessing: the folder's `NOTES.md`, any notes or memory your agent keeps for the project, and the model's section in `references/devices.md`. If a fact might be in an earlier chat (a part number, a pinout, a measurement), search the old sessions before saying it's unknown.
3. Pin down the symptom and what has been measured so far. Photos and logs the user has saved are in the unit folder; copy photos pasted into chat there too, so the next session has them.

## Working rules

These are the corrections that came up more than once. Each has its reason, so apply the reasoning to cases that aren't listed.

- **Put it on the photo.** Any instruction that involves touching the board comes with a diagram drawn on the photo the user sent, not a text description. The user rotates the board while probing, so "left pad" or "far end" means nothing; name pads by the silkscreen next to them ("the end toward the 'F50' text") and say how to confirm with the meter when the photo can't settle it ("the pad that reads 0-1Ω to C123+ is the rail side").
- **Measurements decide.** When a reading contradicts the current theory, drop the theory. Don't keep building on one suspect (a lost resistor, a hot chip) after the numbers point elsewhere. A hot regulator or PoE controller is usually holding a short downstream: find the load before pulling the chip. A useful format is a table of measurements against hypotheses showing which reading separates them.
- **Mark what is verified.** Tag claims in notes and guides: **[V]** measured or read from a datasheet, **[I]** inferred (from layout, a marking, a typical design), **[?]** unknown. An inference stated as fact ("the P-channel clamp FET") costs the user time when it's wrong. Empty tinned pads are usually DNP, not missing parts.
- **Use the bench the user has.** Confirm the equipment once and record it in `NOTES.md`. The bench this skill grew up on: a multimeter, hot air and iron, a CH341A with 1.8 V adapter and SOIC clip, an XGecu T76 programmer (in a Windows VM), USB-UART adapters, a UniFi PoE switch, and a bench supply with no working current limit; no 48 V supply, and no scope or thermal camera unless stated. Plan unpowered checks first, and don't propose improvised current limiters (resistor patch cables, bulbs) to someone without a current-limited supply.
- **Finish the cold checks before power.** Every check listed as "before fitting" or "before power-up" gets a recorded result first. Before a substitute part goes on, map the footprint pads against the substitute's pinout. Skipping these burned two replacement FETs on one board.
- **Thresholds come from the board.** Take "normal" from a known-good twin (an identical rail, the same part elsewhere on the board, another unit) where one exists, and prefer the diode-mode signature over raw ohms. A generic "above 15Ω is fine" was wrong on a rail whose twin read hundreds.
- **Drive the tools yourself.** With a serial adapter attached, run the U-Boot or shell commands yourself through whatever serial tool you have and report results; don't hand the user commands to paste. Use the DigiKey API for stock and price; the website blocks bots and the credentials already exist. Don't type passwords for the user: The user runs `ssh-copy-id` once, you use the key, and the key comes off the device at the end.
- **Rule out the bench before the board.** "No link on any port" was the upstream switch's BPDU guard, not dead PHYs. WAN-side SSH is firewalled on consoles. Check the test setup when a symptom appears only at the bench.
- **Cost matters.** Donor boards and eBay pulls are normal. Offer the donor route alongside new parts, and say when a new part plus shipping and tariffs outweighs the unit.
- **Stay on long operations.** During a flash or programmer write, watch it to 100% and through verify. Don't background it or walk away on a timer; a T76 write fails if its VM loses focus.
- **Say when to close up.** State at which step heatsinks, shields, and the case go back on, and what must be tested before that.
- **The user will go off-plan.** They sometimes pull a part you advised leaving. Take the new result as data and re-plan from it.

## Notes

Keep `NOTES.md` in the unit folder current as you go, since the next session starts from it:

- Board identity (model, silkscreen rev, part number sticker, MAC if relevant).
- Parts table: position, marking, identified part, key specs, replacement, each with [V]/[I]/[?].
- Dated entries: symptom, readings, what was removed or fitted, what that ruled in or out, next step.
- Parts currently off the board, and where they are.

If your agent has persistent memory, use it only for things that outlast the unit: a preference, a model-level fact, where a reference lives. Unit status belongs in `NOTES.md`. When a repair teaches something reusable about a model or a method, add it to `references/devices.md` or the relevant reference here.

## Cleaning up

Close serial sessions you opened. Leave ports held by other processes alone; check with `lsof /dev/cu.usbserial-*` first. Remove SSH keys you had installed, revert bind-mounts and stopped services on the device, stop any monitor loops you started, and say what was left in place on purpose.
