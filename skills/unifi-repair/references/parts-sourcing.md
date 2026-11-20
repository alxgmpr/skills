# Identifying and sourcing parts

## Identify the part

1. Read the marking from a grid crop (`references/photo-annotation.md`), not the full photo. Common misreads: I/1, O/0/G, S/5, M/N, 3/8. If two readings give different voltage classes, ask for a sharper photo before picking a substitute; a 150 V FET was once read as 100 V.
2. Search the marking. Makers drop the family prefix on the package, so search the marking without quotes and with the package: `E050N15BR MOSFET DFN5x6` found CYStek **MT**E050N15BR. SMD code lists and alldatasheet help for SOT-23 codes; some (e.g. "6DW" SOT-23-6 buck) won't be found, and then the twin on the board is the reference.
3. Get the datasheet as a PDF and read the numbers from it:
   - TI: `curl -sL -A "Mozilla/5.0" -o part.pdf https://www.ti.com/lit/ds/symlink/<part>.pdf`
   - `scripts/dk.py pn <MPN>` prints a datasheet URL for anything DigiKey carries.
   - `pdftotext -layout part.pdf - | grep -E 'BVDSS|RDS|Qg|VGS'` for a quick spec pull; Read the PDF pages for pinout drawings.
4. Tag the identification [V] (marking matches a datasheet marking table), [I] (inferred from circuit position), or [?].

Marking notes collected so far are in `references/devices.md`.

## DigiKey API

Use `scripts/dk.py`. Don't open digikey.com in a browser; it serves a bot wall, and an "unverified stock" answer isn't useful to the user.

```bash
uv run python -I scripts/dk.py pn BSC360N15NS3GATMA1 ISC300N20NM6ATMA1
uv run python -I scripts/dk.py pn LM5072MH-80/NOPB --params 'Package'
uv run python -I scripts/dk.py search "MOSFET N-CH 150V 8-PowerTDFN" --params 'Vdss|Rds|Gate Charge|Vgs|Package'
uv run python -I scripts/dk.py search "TVS 58V SMA bidirectional" --limit 20
```

- Credentials: `DIGIKEY_CLIENT_ID` / `DIGIKEY_CLIENT_SECRET` in `~/.config/secrets.env` (production app, client-credentials OAuth). Never print them. `MOUSER_SEARCH_API_KEY` is in the same file for a second source.
- `search` returns in-stock, non-marketplace parts by default; `--all` lifts that.
- Under the hood: `POST /v1/oauth2/token`, then `GET /products/v4/search/{mpn}/productdetails` or `POST /products/v4/search/keyword` with headers `X-DIGIKEY-Client-Id`, `Authorization: Bearer`, `X-DIGIKEY-Locale-Site: US`, `X-DIGIKEY-Locale-Currency: USD`. Extend the script if you need another endpoint.

Things the API does that will mislead you:

- `Active` status says nothing about stock. Read the per-packaging stock lines.
- Order the Cut Tape (`CT-ND`) number. Tape & Reel has reel minimums; a `2156-...` number is a marketplace/Rochester listing with a high minimum.
- DigiKey part numbers can't be derived from the MPN (`448-...`, `296-35300-1-ND`). Take them from the output.
- Keyword search is fuzzy. Search several package spellings (8-PowerTDFN, PowerVDFN, PowerPAK SO-8, DFN5x6, TDSON-8) and filter on the printed parameters.
- Parts DigiKey doesn't carry (CYStek, Wayon, Voohu) report "not carried"; that is when you pick a substitute.
- Recheck stock right before the user orders.

## Choosing a substitute

State the criteria, then show the candidates against them. For a FET:

- Vds at least the original's. Don't drop a class.
- RDS(on) specified at or below the gate drive actually available (an LM5072 drives ~7.7 V, so a part characterised only at 10 V is a risk).
- Gate charge within what the controller's VCC can supply at the switching frequency.
- Same footprint **and pinout**. "Standard 5x6" is an assumption until the pad map is checked: before fitting, the user identifies gate, source, and drain pads on the bare footprint with the meter and you compare against the substitute's datasheet drawing. Explain package-name equivalence up front (PG-TDSON-8 = SuperSO8 = PowerPAK SO-8 = DFN5x6 footprint) so the user does not have to ask.
- When the user says "best fit, highest quality", prefer a major manufacturer (Infineon, TI, onsemi, Vishay) in the identical package.

For transformers and magnetics, match winding arrangement and pin assignment first, then inductance and current; a part with the right voltage and half the current rating is not a substitute. OEM-custom magnetics usually mean a donor board.

## BOM for ordering

When the user asks for a BOM, write `digikey-bom.csv` in the unit folder (uploads at digikey.com/BOM):

```csv
Digi-Key Part Number,Manufacturer Part Number,Manufacturer,Quantity,Customer Reference,Description
448-ISC300N20NM6ATMA1CT-ND,ISC300N20NM6ATMA1,Infineon Technologies,2,Q17,"200V 27mOhm @15V, Qg 21nC, PG-TDSON-8 (5x6); replaces CYStech MTE65N20H8 (1 + 1 spare)"
```

Quantity is what's needed plus a spare for anything that can die on first power-up. The description carries the key specs, what it replaces, and the spare count. Every line is a real in-stock CT part number from the API, with the stock and unit price repeated in your reply.

## Donor route

Often cheaper than new, and the only route for custom magnetics, eMMC, and Ubiquiti-specific parts. When the user is shopping donors:

- eMMC: any JEDEC 153-ball 11.5x13 mm part of at least the original capacity fits (169-ball too; 100-ball doesn't). Reject eMCP (KMQ/KMF/KMR/H9TQ, 162/221-ball). Chromebook boards carry discrete, usually non-underfilled eMMC. A larger chip needs `sgdisk -e` after restoring the image.
- Read markings from listing photos with `sips -s format png in.webp --out full.png`, then a grid crop.
- An identical dead unit (same surge event, different fault) is the best donor and also the best known-good reference.
