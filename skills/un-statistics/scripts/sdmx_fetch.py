#!/usr/bin/env python3
"""Fetch data from any keyless SDMX 2.1 REST service into a tidy CSV.

Built-in providers: undata (UN Statistics Division), unicef, ilo (ILOSTAT), oecd, bis, ecb.
Any other SDMX 2.1 REST endpoint works with --base URL.

Four things it does:
  --list-flows [--search WORDS]           which dataflows (datasets) a provider has
  --flow FLOW --dims                      the dimension order of a flow's key, with example codes
  --flow FLOW --codes DIM [--search W]    every code of one dimension
  --flow FLOW --key KEY [--start/--end/--last]   the data: CSV + one line in data_log.jsonl

A key is one code per dimension, in the order --dims prints, joined by dots.
Several codes: NPL+IND. All codes: leave the position empty (NPL..SEX_T).

Writes <out>/data/<provider>_<flow>_<key>.csv and appends one record to <out>/data_log.jsonl.
"""
import argparse

import _common as C
import _sdmx as X

EXAMPLES = """examples:
  python3 sdmx_fetch.py --provider unicef --list-flows --search mortality
  python3 sdmx_fetch.py --provider unicef --flow UNICEF,GLOBAL_DATAFLOW,1.0 --dims
  python3 sdmx_fetch.py --provider unicef --flow UNICEF,GLOBAL_DATAFLOW,1.0 --codes INDICATOR --search under-five
  python3 sdmx_fetch.py --provider unicef --flow UNICEF,GLOBAL_DATAFLOW,1.0 --key NPL.CME_MRY0T4._T --start 2015
  python3 sdmx_fetch.py --provider ilo --flow ILO,DF_UNE_2EAP_SEX_AGE_RT,1.0 --key NPL.A..SEX_T.AGE_YTHADULT_YGE15 --start 2015
  python3 sdmx_fetch.py --provider oecd --flow OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0 --key FRA.A.N.CPI.PA._T.N.GY --start 2019
  python3 sdmx_fetch.py --provider undata --flow IAEG-SDGs,DF_SDG_GLH,1.26 --key A..SI_POV_DAY1.524........... --start 2010
  python3 sdmx_fetch.py --provider bis --flow BIS,WS_CBPOL,1.0 --key M.US+NP --last 3

providers:
""" + "\n".join("  %-7s %s  (%s)" % (k, v["base"], v["note"]) for k, v in X.PROVIDERS.items())


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--provider", choices=sorted(X.PROVIDERS), help="a built-in provider")
    src.add_argument("--base", help="base URL of another SDMX 2.1 REST service, e.g. https://example.org/rest")
    ap.add_argument("--list-flows", action="store_true", help="list the provider's dataflows")
    ap.add_argument("--flow", help="dataflow: AGENCY,ID,VERSION (safest), AGENCY,ID or ID")
    ap.add_argument("--dims", action="store_true", help="show the flow's dimensions in key order")
    ap.add_argument("--codes", metavar="DIM", help="list the codes of one dimension of the flow")
    ap.add_argument("--search", nargs="+", metavar="WORD", help="filter --list-flows or --codes by words (all must match)")
    ap.add_argument("--key", help="series key, e.g. NPL.CME_MRY0T4._T ('all' = whole flow, can be huge)")
    ap.add_argument("--start", help="first period: 2015, 2015-01, 2015-Q1")
    ap.add_argument("--end", help="last period")
    ap.add_argument("--last", type=int, help="only the last N observations of each series")
    ap.add_argument("--format", choices=["json", "xml"], default="json",
                    help="ask for SDMX-JSON (default; includes labels) or SDMX-ML")
    ap.add_argument("--limit", type=int, default=100, help="rows shown in tables for lists (default 100)")
    C.add_common_args(ap)
    args = ap.parse_args()

    base, label = X.resolve_base(args.provider, args.base)
    search = " ".join(args.search) if args.search else None
    if args.list_flows:
        flows_path = X.PROVIDERS[args.provider]["flows"] if args.provider else "dataflow"
        X.cmd_list_flows(base, label, flows_path, search, args)
        return
    if not args.flow:
        ap.error("give --flow (find one with --list-flows --search WORDS)")
    if args.dims:
        X.cmd_dims(base, label, args.flow, args)
        return
    if args.codes:
        X.cmd_codes(base, label, args.flow, args.codes, search, args)
        return
    if not args.key:
        ap.error("give --key (run --dims to see the dimension order; --key all fetches the whole flow)")
    X.cmd_data(base, label, args.provider or "sdmx", args.flow, args.key, args)


if __name__ == "__main__":
    try:
        C.run(main)
    except X.SDMXError as err:
        C.die(str(err))
