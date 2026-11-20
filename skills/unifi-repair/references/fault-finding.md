# Hardware fault-finding methods

Methods that worked on these boards, and the traps that cost time. Device-specific facts are in `devices.md`.

## Reading the first symptoms

| Symptom | What it means | What it doesn't mean |
|---|---|---|
| All fans at full speed from power-on | Nothing is controlling them: the SoC never ran its fan code (ADT7475-style controllers default to full) | Not a fan or thermal fault |
| SoC stays cold, no UART output | Power sequencing, a shorted rail, DDR, or boot flash. Check rails before firmware | Not an eMMC or OS fault (those print U-Boot first) |
| A regulator or PoE controller is hot | It is current-limiting into a short downstream | Rarely the chip itself; find the load first |
| Mixed/random port LEDs on a switch | LED shift chain never initialised: boot halted early | Not a map of damaged ports |
| PoE device dead after a storm, sibling units dead too | Ethernet surge: check TVS diodes, magnetics, PHY, PoE front end in that order | |
| "Insufficient PoE output" alert on the switch port | The PD drew over its class allowance: a short or a converter not regulating | Not a switch fault. Power-cycle the port in UniFi afterwards |

## Shorted rail

1. **Characterise it.** Ohms both ways and diode mode both ways across the rail's output cap. A hard short reads a few ohms and ~0.00 V in diode mode in both directions. Compare with a twin rail on the same board (same regulator marking elsewhere): a healthy rail's diode reading climbs as the cap charges one way and sits around 0.4-0.6 V the other.
2. **Which pads are on the rail?** A pad is on the shorted rail only if it reads 0-1 Ω to the reference pad. A pad that reads about the short's own resistance (6 Ω on a 6 Ω short) is reaching it through ground. The continuity beeper triggers below ~30 Ω, so it reports false hits on a low-resistance short; use ohms.
3. **Isolate by lifting, measuring after each removal.** Cheapest and most likely first: the output cap and bulk caps, then the inductor (separates regulator from load), then ferrites/0Ω links that split the rail into branches. When lifting a ferrite makes the main rail jump (6 Ω to 35 Ω), the short is on the branch beyond it; follow that branch.
4. **Don't call the remainder healthy by rule of thumb.** After a removal, compare what's left against the twin rail again.
5. **Two nets shorted to each other and to ground with every cap off** points inside the IC they both feed (SoC, switch chip). Check the decoupling caps under the IC on the other side before concluding that.

Voltage injection needs a current-limited supply. the user's supply has no working limit, so plan isolation by lifting. If injection comes up anyway, the low-risk form is 1.0 V or less (below anything's rating on a logic rail), checked on the meter before connecting, and millivolt-drop tracing: black probe on the injection pad, red on each rail pad, the most negative reading is nearest the short. Don't suggest it for PoE-side or primary-side nets.

In-circuit readings lie in predictable ways: a FET's drain-source "short" may be the transformer primary plus the sense resistor in parallel; a low reading across a cap is the whole rail. Before blaming a part, work out what else is across those two points, or lift one end.

## PoE powered-device front end (U6 and similar)

Typical chain: RJ45 magnetics centre taps → bridge/ideal-diode → TVS (SMAJ58A class) → PD controller with hot-swap switch (VEE→RTN) → bulk cap → flyback (primary FET, sense resistor, RCD clamp, transformer) → output rectifier → 12 V or 5 V.

Unpowered checks, in order:

1. Orientation proof: the PD controller's VEE pin beeps to the PoE negative / ground pour.
2. VIN-VEE: should not be a short. Some controllers have an internal ~25 kΩ signature resistor, so kΩ here can be normal; check the datasheet.
3. VEE-RTN (the internal hot-swap FET): a diode drop one way, OL the other.
4. VIN-RTN (the converter input): a short here is downstream of the controller. Suspects in order: primary FET, bulk cap and input MLCCs, TVS.
5. Each TVS, in circuit: any that reads near 0 Ω is shorted. They are often six identical parts; check them all.
6. Transformer: each winding has continuity, and no winding reads to any other. A burnt primary opens; carbonised insulation gives tens of ohms between primary and aux.
7. Primary FET off the board: body diode ~0.5 V, G-S and G-D open.
8. Sense resistor(s): the marked value. An open sense resistor removes the current limit.
9. RCD clamp diode, resistor, and caps; gate resistor; controller OUT pin to its return (not shorted).
10. Output rectifier and the output rail to ground.

If a replacement FET dies at first power-up, the cause is among items 6-10 or the substitute's pinout. Run all of them and record the results before fitting another.

First power for a PoE device is a real 802.3af/at port (the PSE classifies and current-limits). With the FET removed, the controller alone draws little; that is a reasonable intermediate step to check VCC and gate drive before fitting the FET.

## Isolated DC-DC in PoE switches (USW-48-PoE and similar)

- An active-clamp forward controller (UCC2897A) implies a P-channel clamp FET somewhere, often on the underside. Check the datasheet's typical application before listing parts.
- Never back-feed the secondary (the 12 V header) to "test the logic" with the converter's sync FETs fitted; it destroyed both.
- After a shorted primary FET, check the sync FETs, the sense resistors, and the gate-drive path before powering.
- Planned powered check when a current-limited source is available: primary FET removed, controller VDD and the empty gate pad observed. Without one, stay unpowered.

## Surge damage on an Ethernet port (UDM Pro WAN and similar)

Check the port's TVS array, the magnetics, and the PHY's core rail. A PHY that has failed internally can pull shared strap or MDIO lines and stop the SoC's boot preload entirely, so a damaged port PHY can look like a dead SoC or EEPROM. Removing the PHY and seeing the boot log return to normal is a clean test. A replacement PHY with one bad joint gives the same symptom as the dead one; reflow before re-theorising.

## Rework notes

- The user rates their hot-air BGA work as the weak spot; an earlier board was lost to torn eMMC pads. For BGA and bottom-terminated parts, give the preheat, temperature, and "don't lift until it floats" reminders, and suggest practising on the donor first.
- Underfilled parts are much harder to pull; say so when choosing a donor.
- After any replacement: re-measure the cold check that originally failed before power.

## First power-up after a repair

State the order explicitly: cold checks re-run and recorded → power with the minimum attached (no drives, no PoE loads, daughterboards as needed) → watch the first seconds for heat by touch → UART log captured from the first power-on → only then heatsinks, shields and case, unless a part needs its heatsink to run more than a few seconds (say which).
