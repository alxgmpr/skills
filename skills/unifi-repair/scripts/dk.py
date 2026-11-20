"""DigiKey Product Information API v4 lookups. Stdlib only.

  uv run python -I dk.py pn MPN [MPN ...]                 exact part: stock, price, DigiKey part numbers, specs
  uv run python -I dk.py search "MOSFET N-CH 150V 8-PowerTDFN" [--all] [--limit 50] [--params REGEX]
                                                          keyword search; in-stock, non-marketplace unless --all

Credentials: DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET from the environment or ~/.config/secrets.env
(a production app; a sandbox-only app gets 401 here). Mouser's key (MOUSER_SEARCH_API_KEY) lives in the same file.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.digikey.com"


def creds():
    env = dict(os.environ)
    try:
        for line in open(os.path.expanduser("~/.config/secrets.env")):
            line = line.strip().removeprefix("export ")
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip("\"'"))
    except OSError:
        pass
    try:
        return env["DIGIKEY_CLIENT_ID"], env["DIGIKEY_CLIENT_SECRET"]
    except KeyError:
        sys.exit("DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET not found in env or ~/.config/secrets.env")


def session():
    cid, sec = creds()
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(API + "/v1/oauth2/token", data=body), timeout=30))
    return {"X-DIGIKEY-Client-Id": cid, "Authorization": "Bearer " + tok["access_token"],
            "X-DIGIKEY-Locale-Site": "US", "X-DIGIKEY-Locale-Currency": "USD", "Content-Type": "application/json"}


def call(headers, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=30))


def keyword(headers, kw, limit=50, everything=False):
    body = {"Keywords": kw, "Limit": limit, "Offset": 0}
    if not everything:
        body["FilterOptionsRequest"] = {"SearchOptions": ["InStock"], "MarketPlaceFilter": "ExcludeMarketPlace"}
    return call(headers, "/products/v4/search/keyword", body)


def show(p, params_re):
    # Top-level QuantityAvailable comes back None when stock is 0, so print per-packaging stock too.
    print(f"== {p['ManufacturerProductNumber']} | {p['Manufacturer']['Name']} | "
          f"{p.get('ProductStatus', {}).get('Status')} | stock {p.get('QuantityAvailable') or 0}")
    print(f"   {p.get('Description', {}).get('ProductDescription', '')}")
    if p.get("DatasheetUrl"):
        print(f"   datasheet: {p['DatasheetUrl']}")
    for x in p.get("Parameters", []):
        if re.search(params_re, x["ParameterText"], re.I):
            print(f"   {x['ParameterText']}: {x['ValueText']}")
    for v in p.get("ProductVariations", []):
        price = next((s["UnitPrice"] for s in v.get("StandardPricing") or [] if s["BreakQuantity"] == 1), None)
        print(f"   DK# {v['DigiKeyProductNumber']:34s} {v['PackageType']['Name']:24s} "
              f"stock {v.get('QuantityAvailableforPackageType') or 0}  min {v.get('MinimumOrderQuantity')}  1pc ${price}")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("pn", "search"):
        sys.exit(__doc__)
    opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
    params_re = opt("--params", ".")
    skip = {"--all", "--limit", "--params", opt("--limit", None), opt("--params", None)}
    args = [a for a in argv[1:] if a not in skip]
    h = session()
    if argv[0] == "search":
        res = keyword(h, " ".join(args), int(opt("--limit", 50)), "--all" in argv)
        print(f"{res.get('ProductsCount')} matches, showing {len(res.get('Products', []))}")
        for p in res.get("Products", []):
            show(p, params_re)
        return
    for pn in args:
        try:
            if "/" in pn:                                  # productdetails 404s on part numbers containing "/"
                raise urllib.error.HTTPError(None, 404, "slash in part number", None, None)
            show(call(h, f"/products/v4/search/{urllib.parse.quote(pn)}/productdetails")["Product"], params_re)
        except urllib.error.HTTPError as e:
            hits = [p for p in keyword(h, pn, 50, True).get("Products", [])
                    if p["ManufacturerProductNumber"].upper().startswith(pn.upper().split("/")[0])]
            if not hits:
                print(f"== {pn}: not carried by DigiKey (HTTP {e.code})")
            for p in hits:
                show(p, params_re)


if __name__ == "__main__":
    main(sys.argv[1:])
