#!/usr/bin/env python3
"""Fetch European Central Bank data (ECB Data Portal, keyless SDMX API) into a tidy CSV.

Two shortcuts cover the common questions; --flow/--key reaches any ECB series.
  --fx USD,JPY [--freq D|M|Q|A]    euro reference exchange rates: units of each currency per 1 euro
                                   (series EXR/<freq>.<CUR>.EUR.SP00.A)
  --hicp U2,DE,FR [--measure ANR|INX] [--item 000000]
                                   euro-area and member HICP inflation, monthly, from the HICP flow
                                   (series HICP/M.<area>.N.<item>.4D0.<measure>); U2 = euro area
  --flow EXR --key D.USD.EUR.SP00.A  any flow and key (see --list-flows, --flow X --dims)

Periods: --last N (latest N observations per series) or --start/--end (2026-01-02, 2026-01, 2026-Q1, 2026).
Writes <out>/data/ecb_<flow>_<key>.csv and appends one record to <out>/data_log.jsonl.
The ECB publishes reference rates for about 30 currencies only (no NPR, BDT, ...): for others
use the BIS flow WS_XRU through sdmx_fetch.py.
"""
import argparse
import sys

import _common as C
import _sdmx as X

EXAMPLES = """examples:
  python3 ecb_fetch.py --fx USD --last 5
  python3 ecb_fetch.py --fx USD,JPY,INR --freq M --start 2025-01 --end 2025-12
  python3 ecb_fetch.py --hicp U2,DE,FR --last 3
  python3 ecb_fetch.py --flow EXR --key D.GBP.EUR.SP00.A --start 2026-09-01
  python3 ecb_fetch.py --list-flows --search interest rate
  python3 ecb_fetch.py --flow HICP --dims
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fx", help="currencies against the euro, e.g. USD or USD,JPY,INR")
    ap.add_argument("--freq", default="D", choices=["D", "M", "Q", "A"],
                    help="for --fx: D daily (default), M monthly average, Q, A")
    ap.add_argument("--hicp", help="HICP areas, e.g. U2 (euro area) or U2,DE,FR (ISO2 codes)")
    ap.add_argument("--measure", default="ANR",
                    help="for --hicp: ANR annual rate of change (default), INX index, MAR 12-month average rate")
    ap.add_argument("--item", default="000000", help="for --hicp: ICP_ITEM code, 000000 = all items (default)")
    ap.add_argument("--list-flows", action="store_true", help="list ECB dataflows")
    ap.add_argument("--flow", help="ECB dataflow id, e.g. EXR, HICP, FM, MIR, BSI")
    ap.add_argument("--key", help="series key for --flow, e.g. D.USD.EUR.SP00.A")
    ap.add_argument("--dims", action="store_true", help="show the dimensions of --flow in key order")
    ap.add_argument("--codes", metavar="DIM", help="list the codes of one dimension of --flow")
    ap.add_argument("--search", nargs="+", metavar="WORD", help="filter --list-flows or --codes")
    ap.add_argument("--start", help="first period: 2026-01-02, 2026-01, 2026-Q1 or 2026")
    ap.add_argument("--end", help="last period")
    ap.add_argument("--last", type=int, help="latest N observations of each series")
    ap.add_argument("--format", choices=["json", "xml"], default="json", help="SDMX-JSON (default) or SDMX-ML")
    ap.add_argument("--limit", type=int, default=100, help="rows shown for lists (default 100)")
    C.add_common_args(ap)
    args = ap.parse_args()

    base, label = X.resolve_base("ecb")
    search = " ".join(args.search) if args.search else None
    if args.list_flows:
        X.cmd_list_flows(base, label, X.PROVIDERS["ecb"]["flows"], search, args)
        return
    if args.fx:
        curs = [c.upper() for c in C.split_values([args.fx])]
        flow, key = "EXR", "%s.%s.EUR.SP00.A" % (args.freq, "+".join(curs))
    elif args.hicp:
        areas = [a.upper() for a in C.split_values([args.hicp])]
        flow, key = "HICP", "M.%s.N.%s.4D0.%s" % ("+".join(areas), args.item, args.measure.upper())
    elif args.flow:
        flow, key = args.flow, args.key
        if args.dims:
            X.cmd_dims(base, label, flow, args)
            return
        if args.codes:
            X.cmd_codes(base, label, flow, args.codes, search, args)
            return
        if not key:
            ap.error("give --key with --flow (run --flow %s --dims to see the dimension order)" % flow)
    else:
        ap.error("give --fx, --hicp, --flow or --list-flows")
    if not (args.last or args.start or args.end):
        args.last = 10
        print("No period given: showing the last 10 observations per series (--last 10).", file=sys.stderr)
    X.cmd_data(base, label, "ecb", flow, key, args, entity_dims=("REF_AREA", "CURRENCY"))


if __name__ == "__main__":
    try:
        C.run(main)
    except X.SDMXError as err:
        C.die(str(err))
