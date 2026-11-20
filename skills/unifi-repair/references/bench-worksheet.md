# Bench worksheets (interactive test guides)

When a diagnosis needs more than three or four readings, build a worksheet page instead of a list in chat. The user works through it at the bench on a phone or laptop, types each reading, sees a verdict straight away, and pastes the "Copy readings" text back to you. Two earlier repairs used this loop and it worked both times.

Build one when the user asks for a guide, checklist, test plan, or interactive page/artifact, and offer one when you are about to write a long numbered list of measurements.

## Building one

1. Copy `assets/bench-worksheet.html` to the unit folder (e.g. `~/u6-repair/guide/cold-checks.html`). Put annotated photos beside it.
2. Replace the `SHEET` object between the `EDIT FROM HERE` / `EDIT TO HERE` markers. Leave the rest alone; it is a self-contained page with light/dark themes and a phone layout.
3. Check it, then deliver it. If your agent can publish a hosted page (an artifact, canvas, or similar), publish the HTML with its photos so it opens on a phone at the bench, and republish to the same address when readings change the plan. Otherwise give the user the file path, or serve the folder on the local network.
4. Record the page's path or URL in `NOTES.md`.

Shrink photos before publishing (max ~1100 px wide, JPEG quality ~82); a phone doesn't need the 4 MB original.

## SHEET fields

- `key`: localStorage key, unique per unit and job. Change it when items change so stale readings don't carry over.
- `eyebrow`, `title`, `lede`: device and board rev; the question the sheet answers; the state so far in two or three sentences.
- `off`: parts currently off the board.
- `phases[]`: `id`, `title`, `why`, optional `photos[]` (`src`, `alt`, `caption`), optional `powered: true`, and `items[]`.
- A phase with `powered: true` shows a "don't power up yet" block while any earlier item reads as a fault. Use it for every phase that applies power.

Item kinds:

| kind | Input | Judged by |
|---|---|---|
| `ohm` | resistance; accepts `OL`, `24.5k`, `1.2M` | `judge` |
| `v` | volts and diode mode; accepts `0.52`, `520mV`, `OL` | `judge` |
| `ma` | milliamps | `judge` |
| `pair` | marked value and measured value | built in: ok at 0.8-1.25x of marked |
| `choice` | buttons `[value, text, verdict]` | the chosen option's verdict |

Judge helpers (or write `v => "ok" | "warn" | "bad"` directly; `v` is `{n}` or `{ol: true}`):

- `atLeast(ok, warn)`: short hunting. Higher is better and OL passes.
- `atMost(ok, warn)`: continuity, sense resistors, winding resistance. OL is a fault.
- `between(lo, hi)`: rail voltages and forward diode drops.
- `openOk(warn)`: reverse diode, or anything that should read OL or keep climbing.

Each item needs `id`, `title`, `mode` (the meter setting, e.g. `"Ω ohms"`, `"▷| diode"`, `"V DC"`), `red` and `black` (exact probe points), `expect`, and `advice: {bad, warn}`.

## Writing good items

- **Probe points are exact and orientation-proof**: "U18 pin 3 (VIN)", "R214 end toward the 'D10' text", "ring 2 in the photo". Never left/right/near/far.
- **Item ids match the numbers on the annotated photo** in that phase.
- **`expect` says what normal looks like and where that number came from**: the twin rail's reading, the datasheet, the marking. If it is a guess, say so in the text and judge loosely.
- **Thresholds from the board, not a rule of thumb.** If a twin exists, the first phase measures the twin and later thresholds quote it.
- **`advice.bad` says what to do next**, not just that it failed: what to lift, what to measure, or "stop and send a photo".
- **Order by information per effort**: checks that split the hypothesis space first, non-destructive before destructive, unpowered before powered.
- Include an orientation proof early (a continuity check that confirms the user has the pin numbering right).
- Keep it to what the current question needs. A second worksheet for the next question is better than one page that tries to cover every branch.
- No steps that need equipment the user does not have (see SKILL.md).

## Checking before you publish

Earlier worksheets were published without ever being opened. Do both:

```bash
# syntax
node -e 'const s=require("fs").readFileSync(process.argv[1],"utf8").match(/<script>([\s\S]*)<\/script>/)[1]; new Function(s)' guide/cold-checks.html 2>&1 | grep -v "document is not defined"
```

Then open it (serve the folder on localhost, or any browser tool you have) and type one normal, one faulty, and one `OL` reading into a few items to confirm the verdicts and the powered-phase block behave as intended. A threshold that calls a known-bad reading "Normal" is the failure to look for.

## After the user pastes readings back

Update `NOTES.md` with the readings, state what they rule in and out, and either give the next action or republish the worksheet with the next phase. If a reading the user reports contradicts a threshold ("35Ω isn't healthy, the other rails are higher"), fix the threshold and republish.
