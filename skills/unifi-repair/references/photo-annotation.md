# Annotating board photos

The goal is a picture the user can probe from without reading a paragraph: rings on the exact pads, a short label per mark, numbered in the order to measure.

`scripts/annotate.py` has two modes. All coordinates are original-photo pixels.

## 1. Find coordinates with a grid crop

Estimating coordinates by eye from the full photo is what put marks on the wrong part in earlier sessions: the image viewer shows a downscaled copy, so eyeballed numbers are in the wrong frame, and at full-board zoom an 0402 is a few pixels wide. The grid crop fixes both, because its labels are printed in original pixels.

```bash
uv run scripts/annotate.py grid photo.jpg /tmp/.../grid.png                     # whole photo, coarse
uv run scripts/annotate.py grid photo.jpg /tmp/.../grid.png 1400 600 1900 1000  # region, upscaled
uv run scripts/annotate.py grid photo.jpg /tmp/.../grid.png 1560 700 1760 860 --step 20   # pin level
```

Read the PNG, then read coordinates off the yellow labels. Work down: whole photo to find the region, a region crop to find the part, a fine crop (step 10-20) when marking individual pins or 0402 pads. The same crops are how to read part markings and silkscreen; read designators from the crop, not from the full photo. Write grid crops to the scratchpad, not the unit folder.

## 2. Draw

Write a spec, render, look at the result.

```json
{
  "title": "TOP SIDE - primary FET",
  "crop": [1100, 400, 2016, 1200],
  "marks": [
    {"box": [1590, 730, 1720, 840], "label": "1  Q17 pads: G-S, D-S", "color": "red"},
    {"at": [1655, 700], "r": 28, "label": "2  D120 diode test", "color": "cyan"},
    {"at": [1612, 742], "r": 14, "color": "green"},
    {"at": [1700, 742], "r": 14, "color": "red", "label": "A / B", "label_at": [1740, 640]}
  ],
  "notes": ["green = pad A, red = pad B", "A = end toward the 'Q17' silkscreen"]
}
```

```bash
uv run scripts/annotate.py draw photo.jpg spec.json ~/unit-folder/annotated/q17-cold-checks.jpg
```

Labels are placed automatically beside each mark and kept off other marks and labels; the leader runs from the label's edge to the mark's edge. Set `label_at` when the automatic spot covers something that matters. `crop` and `zoom` trim the output; coordinates stay in original pixels either way.

Then Read the output and check, every time:

- Each ring or box sits on the intended pad or part. If a mark is off, cut a finer grid crop there; don't nudge by guesswork.
- No label covers the silkscreen or the neighbouring parts the user needs for orientation.
- The number of marks matches the number of steps in the text or worksheet.

Save finished images in the unit folder (`annotated/` or `photos/`) with a name that says what they show, and show them to the user inline if your agent can display images; otherwise give the path.

## Conventions

- **Title** in the top-left says which side of the board and what the image is for ("BOTTOM SIDE - F50 pads").
- **Numbers** in labels match the step numbers in the instructions or worksheet item ids. One number per mark (two marks for one step become 1a / 1b), and every numbered step in the reply states the expected reading, so a mark never leads to "see below".
- **Colors** carry meaning, and the notes block says what they mean when it isn't obvious:
  red = suspect / fault / pad B, yellow = measure here, cyan = reference or injection point, magenta = remove this, green = pad A / known-good reference, white = ground or instruction, grey = already cleared.
- **Two-pad parts**: ring the pads green (A) and red (B), and anchor A to silkscreen in a note. The user will have the board upside down or rotated.
- **IC pins**: mark only the pins being probed. State where pin 1 is and which way the numbering runs, and give a continuity check that proves the orientation ("pin 7 beeps to the ground pour").
- **Hedge on the image** when the photo can't settle it: "F51?", "VERIFY by continuity". Then say in the text how to resolve it with the meter.
- **One job per image.** A tight crop with four marks beats a whole-board photo with twelve. For a sequence across both sides, make one image per side.
- A whole-board overview is fine for "where on the board is this", but pair it with crops for the actual probing.

## Things that went wrong before

- A box labelled as cap C686 was actually ferrite F50: the designator was read from the nearest silkscreen in a dense cluster. In dense areas, designators often sit beside a different part than they name; follow the silkscreen outline or count along the row, and hedge if unsure.
- Labels placed over the ring they described, and labels with no leader far from their mark.
- Pin-1 placed by eye. Use a fine grid crop on the package corner and look for the dot or notch.
- If the photo is too blurry or angled to place a pad-level mark, ask for a closer, square-on shot of that area instead of guessing.
