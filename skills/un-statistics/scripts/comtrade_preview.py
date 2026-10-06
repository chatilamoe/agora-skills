#!/usr/bin/env python3
"""Fetch merchandise trade values from UN Comtrade's keyless public preview API.

UN Comtrade's full API needs a (free) subscription key, which this repo does not use. Its
public preview endpoint needs none but has limits: one period per call, at most 500 rows,
and roughly one call every two seconds (HTTP 429 otherwise; the script waits and retries).
That is enough for a country's total exports and imports, its trade with one partner, or
its trade by HS chapter in one year.

  --reporter NPL --year 2022                          total exports and imports with the world
  --reporter NPL --year 2022 --partner IND            with one partner
  --reporter NPL --year 2022 --partner all --flow X   by partner (up to 500 rows)
  --reporter NPL --year 2022 --cmd AG2 --flow X       by HS 2-digit chapter
  --reporter NPL --year 2022 --cmd 27,84              specific HS codes

Countries: ISO3 codes are converted to Comtrade's own reporter/partner codes, which are not
always M49 (India is 699, the USA 842, France 251, Switzerland 757). Values are in current US
dollars as reported (imports usually CIF, exports FOB). A year with no rows usually means the
country has not reported it yet: try the year before.

Writes <out>/data/comtrade_<reporter>_<year>_<flow>_<cmd>_<partner>.csv and appends one record
to <out>/data_log.jsonl.
"""
import argparse

import _common as C

API = "https://comtradeapi.un.org/public/v1/preview/C"
REF = "https://comtradeapi.un.org/files/v1/app/reference"
MAX_ROWS = 500

EXAMPLES = """examples:
  python3 comtrade_preview.py --reporter NPL --year 2022
  python3 comtrade_preview.py --reporter NPL --year 2022 --partner IND
  python3 comtrade_preview.py --reporter NPL --year 2022 --cmd AG2 --flow X
  python3 comtrade_preview.py --reporter IND --year 2023 --partner all --flow X
"""


def code_for(token, kind):
    """ISO3/ISO2/M49/name -> Comtrade reporter or partner code (current, non-expired entry)."""
    t = token.strip()
    if t.isdigit():
        return int(t), t
    iso3 = C.to_iso3(t).upper()
    if kind == "reporter":
        url, code_key, iso_key, name_key = REF + "/Reporters.json", "reporterCode", "reporterCodeIsoAlpha3", "text"
    else:
        url, code_key, iso_key, name_key = REF + "/partnerAreas.json", "PartnerCode", "PartnerCodeIsoAlpha3", "text"
    entries = C.fetch_json(url).get("results") or []
    current = [e for e in entries if (e.get(iso_key) or "").upper() == iso3 and not e.get("entryExpiredDate")]
    if not current:
        current = [e for e in entries if (e.get(name_key) or "").casefold() == t.casefold()]
    if not current:
        raise C.FetchError("no Comtrade %s code for %r; give the numeric code instead (see %s)" % (kind, t, url))
    return int(current[0][code_key]), iso3


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reporter", required=True, help="reporting country: ISO3 (NPL) or Comtrade code (524)")
    ap.add_argument("--year", required=True, help="one year (2022) or, with --freq M, one month (202203)")
    ap.add_argument("--freq", default="A", choices=["A", "M"], help="A annual (default) or M monthly")
    ap.add_argument("--flow", default="M,X", help="M imports, X exports, or M,X (default)")
    ap.add_argument("--partner", default="World", help="World (default), all (one row per partner), or ISO3")
    ap.add_argument("--cmd", default="TOTAL", help="TOTAL (default), AG2 (all HS chapters), or HS codes: 27,84")
    C.add_common_args(ap)
    args = ap.parse_args()

    rep_code, rep_iso = code_for(args.reporter, "reporter")
    params = [("reporterCode", rep_code), ("period", args.year), ("flowCode", args.flow.upper().replace(" ", "")),
              ("cmdCode", args.cmd.replace(" ", "")), ("includeDesc", "true")]
    partner = args.partner.strip()
    if partner.casefold() == "world":
        params.append(("partnerCode", 0))
        partner_label = "World"
    elif partner.casefold() == "all":
        partner_label = "all"
    else:
        pcode, piso = code_for(partner, "partner")
        params.append(("partnerCode", pcode))
        partner_label = piso
    url = C.build_url("%s/%s/HS" % (API, args.freq), params)
    data = C.fetch_json(url)
    if data.get("error"):
        raise C.FetchError("Comtrade: %s" % data["error"], None, str(data), url)
    keep = ["period", "reporterCode", "reporterISO", "reporterDesc", "flowCode", "flowDesc", "partnerCode",
            "partnerISO", "partnerDesc", "cmdCode", "cmdDesc", "aggrLevel", "isLeaf", "primaryValue", "fobvalue",
            "cifvalue", "netWgt", "qty", "qtyUnitAbbr", "customsCode", "motCode", "partner2Code",
            "isReported", "isAggregate"]
    rows = [{k: r.get(k) for k in keep} for r in data.get("data") or []]
    rows.sort(key=lambda r: (str(r["flowCode"]), str(r["partnerDesc"]), str(r["cmdCode"])))
    stem = "comtrade_%s_%s_%s_%s_%s" % (rep_iso, args.year, args.flow.replace(",", ""), args.cmd.replace(",", "-"),
                                        partner_label)
    path = C.write_csv(rows, keep, args.out, stem) if rows else None
    log = C.log_data(args.out, "UN Comtrade (public preview API, HS, %s)" % ("annual" if args.freq == "A" else "monthly"),
                     "flow=%s;cmd=%s;partner=%s" % (args.flow, args.cmd, partner_label), rep_iso, str(args.year),
                     url, len(rows), path)
    C.report(args, rows, keep, ["period", "flowDesc", "partnerDesc", "cmdCode", "cmdDesc", "primaryValue"], log)
    if not args.json:
        if len(rows) >= MAX_ROWS:
            print("The preview returns at most %d rows: this result may be cut off. Narrow --cmd or --partner." % MAX_ROWS)
        if not rows:
            print("No rows: the reporter may not have reported %s yet; try an earlier year." % args.year)
        else:
            print("Values: current US dollars as reported (primaryValue; imports usually CIF, exports FOB).")


if __name__ == "__main__":
    C.run(main)
