"""SDMX helpers shared by sdmx_fetch.py and ecb_fetch.py. Standard library only.

Not a script. It knows:
- the keyless SDMX 2.1 REST services this skill uses (PROVIDERS);
- how to build data and structure URLs;
- how to turn SDMX-JSON (1.0, 2.0, and the older draft the ECB still sends) and
  SDMX-ML (2.1 and 3.0, generic and structure-specific) into tidy rows:
  one row per observation, dimension codes (+ labels when the format has them),
  TIME_PERIOD, OBS_VALUE, then attributes.
"""
import json
import urllib.parse
import xml.etree.ElementTree as ET

import _common as C

PROVIDERS = {
    "undata": {"label": "UNdata", "base": "https://data.un.org/ws/rest",
               "flows": "dataflow",
               "note": "UN Statistics Division; SDG, energy, national accounts, GHG flows; M49 area codes"},
    "unicef": {"label": "UNICEF Data Warehouse", "base": "https://sdmx.data.unicef.org/ws/public/sdmxapi/rest",
               "flows": "dataflow",
               "note": "child mortality, nutrition, immunisation, education, WASH, child protection; ISO3"},
    "ilo": {"label": "ILOSTAT", "base": "https://sdmx.ilo.org/rest",
            "flows": "dataflow",
            "note": "labour: unemployment, employment, wages, informality; ISO3"},
    "oecd": {"label": "OECD", "base": "https://sdmx.oecd.org/public/rest",
             "flows": "dataflow/all",
             "note": "OECD Data Explorer: prices, national accounts, labour, trade, education; ISO3"},
    "bis": {"label": "BIS", "base": "https://stats.bis.org/api/v1",
            "flows": "dataflow/BIS/all/latest",
            "note": "policy rates, credit, property prices, effective exchange rates; ISO2"},
    "ecb": {"label": "ECB", "base": "https://data-api.ecb.europa.eu/service",
            "flows": "dataflow/ECB",
            "note": "euro exchange rates, euro-area prices, interest rates, money; ISO2 and currency codes"},
}

ACCEPT_JSON = "application/vnd.sdmx.data+json"                     # all six answer this
ACCEPT_XML = "application/vnd.sdmx.genericdata+xml;version=2.1"     # all six answer this
ACCEPT_STRUCTURE = "application/vnd.sdmx.structure+xml;version=2.1"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Dimension ids that name the country or area, for the log's "entity" field.
AREA_DIMS = ("REF_AREA", "COUNTRY", "GEO", "AREA", "LOCATION", "REF_AREA_TYPE")


class SDMXError(Exception):
    pass


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# --------------------------------------------------------------------------- URLs

def resolve_base(provider=None, base=None):
    if base:
        return base.rstrip("/"), "SDMX " + C._host(base)
    if provider not in PROVIDERS:
        raise SDMXError("unknown provider %r; use one of %s or --base URL" % (provider, ", ".join(PROVIDERS)))
    p = PROVIDERS[provider]
    return p["base"], p["label"]


def split_flow(flow):
    """'AGENCY,ID,VERSION' / 'AGENCY,ID' / 'ID' -> (agency or 'all', id, version or 'latest')."""
    parts = [p.strip() for p in flow.split(",")]
    if len(parts) == 1:
        return "all", parts[0], "latest"
    if len(parts) == 2:
        return parts[0] or "all", parts[1], "latest"
    return parts[0] or "all", parts[1], parts[2] or "latest"


def data_url(base, flow, key="all", start=None, end=None, last=None, extra=None):
    path_key = urllib.parse.quote(key or "all", safe=".+*-_~")
    flow_ref = urllib.parse.quote(flow, safe=",.@-_~")
    params = [("startPeriod", start), ("endPeriod", end), ("lastNObservations", last)]
    params.extend(extra or [])
    return C.build_url("%s/data/%s/%s" % (base, flow_ref, path_key), params)


def structure_url(base, flow):
    agency, fid, version = split_flow(flow)
    return "%s/dataflow/%s/%s/%s?references=all" % (
        base, urllib.parse.quote(agency, safe=".-_"), urllib.parse.quote(fid, safe=".@-_"),
        urllib.parse.quote(version, safe=".-_"))


# --------------------------------------------------------------------------- errors

def error_text(text):
    """Pull the message out of an SDMX error body (XML, JSON or plain text)."""
    text = (text or "").strip()
    if text.startswith("{"):
        try:
            d = json.loads(text)
            errs = d.get("errors") or []
            msgs = [e.get("message") or e.get("detail") or "" for e in errs if isinstance(e, dict)]
            if not msgs and d.get("detail"):
                msgs = [d["detail"]]
            if msgs:
                return " ".join(m for m in msgs if m)
        except ValueError:
            pass
    if text.startswith("<"):
        try:
            root = ET.fromstring(text.encode("utf-8"))
            msgs = [t.text for t in root.iter() if local(t.tag) == "Text" and t.text]
            if msgs:
                return " ".join(msgs)
        except ET.ParseError:
            pass
    return C.snippet(text)


def is_no_data(status, text):
    """True when the server is saying 'the query is valid but matched nothing'."""
    t = (text or "").lower()
    return status == 404 and ("norecordsfound" in t or "no data" in t or "no series" in t
                              or "no results" in t or "noresultsfound" in t)


# --------------------------------------------------------------------------- data parsing

def parse_data(body):
    """bytes -> (rows, columns). Sniffs JSON vs XML from the first character."""
    text = body.decode("utf-8-sig", "replace").lstrip()
    if not text:
        return [], []          # the ECB answers HTTP 200 with an empty body when nothing matches
    if text.startswith("{"):
        return parse_json(json.loads(text))
    if text.startswith("<"):
        return parse_xml(text.encode("utf-8"))
    raise SDMXError("response is neither SDMX-JSON nor SDMX-ML: " + C.snippet(text, 200))


def _name(obj):
    if not isinstance(obj, dict):
        return ""
    if obj.get("name"):
        return obj["name"]
    names = obj.get("names") or {}
    return names.get("en") or next(iter(names.values()), "") if names else ""


def _attr_value(attr, index):
    if index is None or not isinstance(index, int):
        return ""
    values = attr.get("values") or []
    if 0 <= index < len(values):
        v = values[index]
        if isinstance(v, dict):
            for k in ("id", "value", "name"):
                if v.get(k) not in (None, ""):
                    return v[k]
            names = v.get("names") or {}
            return names.get("en") or next(iter(names.values()), "") if names else ""
        return v
    return ""


class _Cols:
    """Keeps column order: dimensions (+labels), TIME_PERIOD, OBS_VALUE, attributes."""

    def __init__(self):
        self.dims, self.time, self.attrs = [], [], []

    def add(self, bucket, name):
        target = getattr(self, bucket)
        if name not in self.dims and name not in self.time and name not in self.attrs:
            target.append(name)

    def ordered(self):
        return self.dims + self.time + ["OBS_VALUE"] + [a for a in self.attrs if a != "OBS_VALUE"]


def parse_json(doc):
    """SDMX-JSON 1.0 ({meta, data:{structure, dataSets}}), 2.0 ({meta, data:{structures, dataSets}})
    and the older draft ({header, structure, dataSets}) -> (rows, columns)."""
    if doc.get("errors") and not (doc.get("data") or doc.get("dataSets")):
        raise SDMXError(error_text(json.dumps(doc)))
    data = doc.get("data") if isinstance(doc.get("data"), dict) else doc
    structures = data.get("structures") or [data.get("structure") or doc.get("structure") or {}]
    datasets = data.get("dataSets") or doc.get("dataSets") or []
    rows, cols = [], _Cols()
    for ds in datasets:
        sidx = ds.get("structure", 0) if isinstance(ds.get("structure"), int) else 0
        st = structures[sidx] if sidx < len(structures) else structures[0]
        dims = st.get("dimensions") or {}
        attrs = st.get("attributes") or {}
        ds_dims = dims.get("dataSet") or []
        s_dims = sorted(dims.get("series") or [], key=lambda d: d.get("keyPosition", 0))
        o_dims = dims.get("observation") or []
        ds_attrs = attrs.get("dataSet") or attrs.get("dataset") or []   # BIS writes "dataset"
        s_attrs = attrs.get("series") or []
        o_attrs = attrs.get("observation") or []

        base = {}
        for d in ds_dims:
            vals = d.get("values") or []
            if vals:
                base[d["id"]] = vals[0].get("id")
                base[d["id"] + "_label"] = _name(vals[0])
                cols.add("dims", d["id"])
                cols.add("dims", d["id"] + "_label")
        for i, a in enumerate(ds_attrs):
            idx = (ds.get("attributes") or [None] * len(ds_attrs))
            val = _attr_value(a, idx[i] if i < len(idx) else None)
            if val not in ("", None):
                base[a["id"]] = val
                cols.add("attrs", a["id"])

        def put_dims(row, dim_list, key_parts, bucket):
            for d, part in zip(dim_list, key_parts):
                vals = d.get("values") or []
                try:
                    v = vals[int(part)]
                except (ValueError, IndexError):
                    v = {"id": part}
                vid = v.get("id") if v.get("id") is not None else v.get("value", part)
                row[d["id"]] = vid
                cols.add(bucket, d["id"])
                label = _name(v)
                if label and label != vid:
                    row[d["id"] + "_label"] = label
                    cols.add(bucket, d["id"] + "_label")

        def put_obs(row, values):
            row["OBS_VALUE"] = values[0] if values else None
            for a, idx in zip(o_attrs, values[1:] if values else []):
                val = _attr_value(a, idx)
                if val not in ("", None):
                    row[a["id"]] = val
                    cols.add("attrs", a["id"])

        if isinstance(ds.get("series"), dict):
            for skey, series in ds["series"].items():
                srow = dict(base)
                put_dims(srow, s_dims, skey.split(":") if skey else [], "dims")
                for a, idx in zip(s_attrs, series.get("attributes") or []):
                    val = _attr_value(a, idx)
                    if val not in ("", None):
                        srow[a["id"]] = val
                        cols.add("attrs", a["id"])
                for okey, values in (series.get("observations") or {}).items():
                    row = dict(srow)
                    put_dims(row, o_dims, okey.split(":"), "time")
                    put_obs(row, values)
                    rows.append(row)
        elif isinstance(ds.get("observations"), dict):
            # dimensionAtObservation=AllDimensions: every dimension is in the observation key
            all_dims = o_dims
            time_ids = {d["id"] for d in all_dims if d.get("role") == "time" or d["id"] == "TIME_PERIOD"}
            for okey, values in ds["observations"].items():
                row = dict(base)
                for d, part in zip(all_dims, okey.split(":")):
                    put_dims(row, [d], [part], "time" if d["id"] in time_ids else "dims")
                put_obs(row, values)
                rows.append(row)
    return _finish(rows, cols)


def _finish(rows, cols):
    columns = cols.ordered()
    if "TIME_PERIOD" in columns:
        rows.sort(key=lambda r: tuple(str(r.get(c, "")) for c in cols.dims) + (str(r.get("TIME_PERIOD", "")),))
    for r in rows:
        if r.get("OBS_VALUE") is None:
            r["OBS_VALUE"] = ""
    return rows, columns


_DS_SKIP = {"action", "structureRef", "dataScope", "setID", "publicationYear", "publicationPeriod",
            "reportingBeginDate", "reportingEndDate", "validFromDate", "validToDate", "type"}


def parse_xml(body):
    """SDMX-ML GenericData or StructureSpecificData (2.1 or 3.0) -> (rows, columns)."""
    root = ET.fromstring(body)
    if local(root.tag) == "Error":
        raise SDMXError(" ".join(t.text for t in root.iter() if local(t.tag) == "Text" and t.text))
    rows, cols = [], _Cols()
    for ds in root.iter():
        if local(ds.tag) != "DataSet":
            continue
        base = {}
        for k, v in ds.attrib.items():
            if not k.startswith("{") and k not in _DS_SKIP and k.upper() == k:
                base[k] = v
                cols.add("attrs", k)
        for child in ds:
            kind = local(child.tag)
            if kind == "Attributes":           # generic format: dataset-level attributes
                for k, v in _values(child):
                    base[k] = v
                    cols.add("attrs", k)
            elif kind == "Series":
                if any(local(c.tag) == "SeriesKey" for c in child):
                    rows.extend(_generic_series(child, base, cols))
                else:
                    rows.extend(_ss_series(child, base, cols))
            elif kind == "Obs":
                if any(local(c.tag) in ("ObsKey", "ObsValue") for c in child):
                    rows.append(_generic_obs(child, dict(base), cols))
                else:
                    # flat structure-specific data: every dimension and attribute sits on <Obs>
                    row = dict(base)
                    for k, v in child.attrib.items():
                        if k.startswith("{"):
                            continue
                        row[k] = v
                        if k == "TIME_PERIOD":
                            cols.add("time", k)
                        elif k != "OBS_VALUE":
                            cols.add("dims", k)
                    rows.append(row)
    return _finish(rows, cols)


def _values(el):
    return [(v.attrib.get("id") or v.attrib.get("concept"), v.attrib.get("value")) for v in el
            if local(v.tag) == "Value"]


def _generic_series(series, base, cols):
    srow = dict(base)
    for part in series:
        kind = local(part.tag)
        if kind == "SeriesKey":
            for k, v in _values(part):
                srow[k] = v
                cols.add("dims", k)
        elif kind == "Attributes":
            for k, v in _values(part):
                srow[k] = v
                cols.add("attrs", k)
    out = []
    for obs in series:
        if local(obs.tag) == "Obs":
            out.append(_generic_obs(obs, dict(srow), cols))
    return out


def _generic_obs(obs, row, cols):
    for part in obs:
        kind = local(part.tag)
        if kind == "ObsDimension":
            dim = part.attrib.get("id") or "TIME_PERIOD"
            row[dim] = part.attrib.get("value")
            cols.add("time", dim)
        elif kind == "ObsKey":
            for k, v in _values(part):
                row[k] = v
                cols.add("time" if k == "TIME_PERIOD" else "dims", k)
        elif kind == "ObsValue":
            row["OBS_VALUE"] = part.attrib.get("value")
        elif kind == "Attributes":
            for k, v in _values(part):
                row[k] = v
                cols.add("attrs", k)
    return row


def _ss_series(series, base, cols):
    srow = dict(base)
    for k, v in series.attrib.items():
        if not k.startswith("{"):
            srow[k] = v
            cols.add("dims", k)
    out = []
    for obs in series:
        if local(obs.tag) != "Obs":
            continue
        row = dict(srow)
        for k, v in obs.attrib.items():
            if k.startswith("{"):
                continue
            row[k] = v
            if k == "TIME_PERIOD":
                cols.add("time", k)
            elif k != "OBS_VALUE":
                cols.add("attrs", k)
        out.append(row)
    return out


# --------------------------------------------------------------------------- structures

def _en_name(el):
    names = [c for c in el if local(c.tag) == "Name"]
    for n in names:
        if n.attrib.get(XML_LANG, "en").startswith("en"):
            return (n.text or "").strip()
    return (names[0].text or "").strip() if names else ""


def parse_dataflows(body):
    root = ET.fromstring(body)
    flows = []
    for el in root.iter():
        if local(el.tag) == "Dataflow" and el.attrib.get("id"):
            flows.append({"agency": el.attrib.get("agencyID", ""), "id": el.attrib["id"],
                          "version": el.attrib.get("version", ""), "name": _en_name(el)})
    return flows


def parse_structure(body, flow_id=None):
    """Dataflow with references=all -> {name, dimensions[], constraint{}, constraint_type}.

    references=all can bring sibling dataflows that share codelists (BIS does this), so the
    dataflow, its data structure and its content constraints are matched on flow_id."""
    root = ET.fromstring(body)
    codelists = {}
    for cl in root.iter():
        if local(cl.tag) != "Codelist":
            continue
        codes = {}
        for code in cl:
            if local(code.tag) == "Code" and code.attrib.get("id") is not None:
                codes[code.attrib["id"]] = _en_name(code)
        key = (cl.attrib.get("agencyID"), cl.attrib.get("id"), cl.attrib.get("version"))
        codelists[key] = codes
        codelists.setdefault(cl.attrib.get("id"), codes)
    flows = [el for el in root.iter() if local(el.tag) == "Dataflow" and el.attrib.get("id")]
    fid = (flow_id or "").upper()
    flow = next((f for f in flows if f.attrib["id"].upper() == fid), flows[0] if flows else None)
    name, dsd_id = "", None
    if flow is not None:
        name = _en_name(flow)
        for r in flow.iter():
            if local(r.tag) == "Ref" and (r.attrib.get("class") == "DataStructure"
                                           or r.attrib.get("package") == "datastructure"):
                dsd_id = r.attrib.get("id")
                break
    dsds = [el for el in root.iter() if local(el.tag) == "DataStructure" and el.attrib.get("id")]
    dsd = next((d for d in dsds if d.attrib["id"] == dsd_id), dsds[0] if dsds else None)
    dims = []
    for dl in (dsd.iter() if dsd is not None else []):
        if local(dl.tag) != "DimensionList":
            continue
        for d in dl:
            kind = local(d.tag)
            if kind not in ("Dimension", "TimeDimension"):
                continue
            ref = None
            for r in d.iter():
                if local(r.tag) == "Ref" and (r.attrib.get("class") == "Codelist"
                                               or r.attrib.get("package") == "codelist"):
                    ref = (r.attrib.get("agencyID"), r.attrib.get("id"), r.attrib.get("version"))
                    break
            codes = {}
            if ref:
                codes = codelists.get(ref) or codelists.get(ref[1]) or {}
            dims.append({"position": int(d.attrib.get("position") or len(dims) + 1), "id": d.attrib.get("id"),
                         "time": kind == "TimeDimension", "codelist": ref[1] if ref else "", "codes": codes})
        break
    dims.sort(key=lambda x: x["position"])

    def attached(cc):
        if not flow_id:
            return True
        targets = set()
        for ca in cc.iter():
            if local(ca.tag) != "ConstraintAttachment":
                continue
            for x in ca.iter():
                if local(x.tag) == "Ref" and x.attrib.get("id"):
                    targets.add(x.attrib["id"])
                elif x.text and "=" in x.text:            # URN form: ...Dataflow=AGENCY:ID(VERSION)
                    targets.add(x.text.strip().split(":")[-1].split("(")[0])
        upper = {t.upper() for t in targets}
        return not targets or fid in upper or (dsd_id.upper() in upper if dsd_id else False)

    constraint, ctype = {}, ""
    for wanted in ("Actual", "Allowed"):
        for cc in root.iter():
            if local(cc.tag) != "ContentConstraint" or cc.attrib.get("type", "Actual") != wanted:
                continue
            if not attached(cc):
                continue
            for kv in cc.iter():
                if local(kv.tag) == "KeyValue":
                    vals = [v.text for v in kv if local(v.tag) == "Value" and v.text is not None]
                    if vals:
                        constraint.setdefault(kv.attrib.get("id"), set()).update(vals)
        if constraint:
            ctype = wanted
            break
    return {"name": name, "dimensions": dims, "constraint": constraint, "constraint_type": ctype}


def key_template(dims):
    return ".".join(d["id"] for d in dims if not d["time"])


search_match = C.matches   # every word of the query appears in the text, ignoring case


# --------------------------------------------------------------------------- commands
# Shared by sdmx_fetch.py and ecb_fetch.py. Each prints a table (or JSON with --json).

def _hint(err):
    text = (err.body or "") + " " + str(err)
    low = text.lower()
    if "key values" in low or "expecting" in low:
        return "\nHint: the key has the wrong number of parts; run with --dims to see the dimension order."
    if ("could not find dataflow" in low or "not available for dissemination" in low
            or ("dataflow" in low and err.status == 404)):
        return "\nHint: unknown dataflow; run with --list-flows --search WORDS."
    if "ora-" in low:
        return "\nHint: ILOSTAT answers HTTP 500 when a code in the key does not exist; check codes with --dims."
    if "semantic" in low or err.status in (400, 422):
        return "\nHint: check the key and the period format (2020, 2020-01, 2020-Q1); run with --dims."
    return ""


def cmd_list_flows(base, label, flows_path, search, args):
    url = "%s/%s" % (base, flows_path)
    body, _ = C.fetch(url, accept=ACCEPT_STRUCTURE)
    flows = parse_dataflows(body)
    if search:
        flows = [f for f in flows if search_match(f["id"] + " " + f["name"], search)]
    if args.json:
        C.print_json({"provider": label, "url": url, "count": len(flows), "dataflows": flows})
        return
    print("%s dataflows%s: %d" % (label, (" matching %r" % search) if search else "", len(flows)))
    C.print_table(flows, ["agency", "id", "version", "name"], limit=args.limit, width=90,
                  more="use --search, --limit N or --json to see more")
    if flows:
        f = flows[0]
        print("\nNext: --flow %s,%s,%s --dims" % (f["agency"], f["id"], f["version"]))


def load_structure(base, flow):
    url = structure_url(base, flow)
    body, _ = C.fetch(url, accept=ACCEPT_STRUCTURE)
    st = parse_structure(body, split_flow(flow)[1])
    st["url"] = url
    if not st["dimensions"]:
        raise SDMXError("no data structure found for %r at %s" % (flow, url))
    return st


def cmd_dims(base, label, flow, args, examples=6):
    st = load_structure(base, flow)
    dims = [d for d in st["dimensions"] if not d["time"]]
    rows = []
    for d in dims:
        codes = d["codes"]
        with_data = st["constraint"].get(d["id"])
        pool = [c for c in codes if c in with_data] if with_data else list(codes)
        if with_data and not pool:
            pool = sorted(with_data)
        rows.append({"position": d["position"], "dimension": d["id"], "codelist": d["codelist"],
                     "codes": len(codes), "in_use": len(with_data) if with_data else "",
                     "examples": ", ".join("%s=%s" % (c, codes.get(c, "")) for c in pool[:examples])})
    template = key_template(st["dimensions"])
    if args.json:
        C.print_json({"provider": label, "flow": flow, "name": st["name"], "key_template": template,
                      "constraint": st["constraint_type"], "url": st["url"], "dimensions": rows})
        return
    print("%s %s: %s" % (label, flow, st["name"]))
    print("Key order: %s" % template)
    print("Write one code per position, separated by dots; join several codes with +; "
          "leave a position empty for all codes.")
    if st["constraint_type"] == "Actual":
        print("'in_use' counts codes the provider lists as having data (its 'actual' content constraint). "
              "Lists can be incomplete: a code not listed may still have data, so try it.")
    elif st["constraint_type"]:
        print("'in_use' counts codes the flow allows (an 'allowed' content constraint; not proof of data).")
    print()
    C.print_table(rows, ["position", "dimension", "codelist", "codes", "in_use", "examples"],
                  limit=100, width=110)
    print("\nList all codes of one dimension: --flow %s --codes DIMENSION [--search WORDS]" % flow)


def cmd_codes(base, label, flow, dim_id, search, args):
    st = load_structure(base, flow)
    match = [d for d in st["dimensions"] if d["id"].upper() == dim_id.upper()]
    if not match:
        raise SDMXError("%s has no dimension %r; dimensions: %s" % (flow, dim_id, key_template(st["dimensions"])))
    d = match[0]
    with_data = st["constraint"].get(d["id"])
    flag = "listed_with_data" if st["constraint_type"] == "Actual" else "allowed"
    rows = [{"code": c, "name": n, flag: ("yes" if c in with_data else "no") if with_data else ""}
            for c, n in d["codes"].items()]
    if search:
        rows = [r for r in rows if search_match(r["code"] + " " + r["name"], search)]
    if with_data:
        rows.sort(key=lambda r: r[flag] != "yes")     # codes in use first, codelist order kept
    if args.json:
        C.print_json({"provider": label, "flow": flow, "dimension": d["id"], "position": d["position"],
                      "codelist": d["codelist"], "count": len(rows), "codes": rows})
        return
    print("%s %s, dimension %s (position %d, codelist %s): %d codes%s" % (
        label, flow, d["id"], d["position"], d["codelist"], len(rows),
        (" matching %r" % search) if search else ""))
    C.print_table(rows, ["code", "name", flag] if with_data else ["code", "name"], limit=args.limit, width=90,
                  more="use --search, --limit N or --json to see more")


def _table_view(rows, columns):
    """Columns that vary across rows (plus TIME_PERIOD, OBS_VALUE) and a line for the constant ones."""
    tidx = columns.index("TIME_PERIOD") if "TIME_PERIOD" in columns else columns.index("OBS_VALUE")
    dims = [c for c in columns[:tidx] if not c.endswith("_label")]
    varying = [c for c in dims if len({str(r.get(c, "")) for r in rows}) > 1]
    if not varying:
        varying = [c for c in dims if c in AREA_DIMS][:1]
    view = []
    for c in varying:
        view.append(c)
        if c + "_label" in columns:
            view.append(c + "_label")
    view += [c for c in ("TIME_PERIOD", "OBS_VALUE") if c in columns]
    for extra in ("UNIT_MEASURE", "OBS_STATUS"):
        if extra in columns and len({str(r.get(extra, "")) for r in rows}) > 1:
            view.append(extra)
    constant = []
    for c in dims:
        if c in varying:
            continue
        v = rows[0].get(c, "")
        lab = rows[0].get(c + "_label", "")
        constant.append("%s=%s%s" % (c, v, (" (%s)" % lab) if lab and lab != v else ""))
    for extra in ("UNIT_MEASURE", "UNIT_MULT"):
        if extra in columns and extra not in view and extra not in dims and rows[0].get(extra) not in (None, ""):
            constant.append("%s=%s" % (extra, rows[0].get(extra)))
    return view, constant


def cmd_data(base, label, provider, flow, key, args, file_prefix=None, entity_dims=AREA_DIMS):
    start, end, last = args.start, args.end, args.last
    url = data_url(base, flow, key, start=start, end=end, last=last)
    fmt = getattr(args, "format", "json")
    accept = ACCEPT_JSON if fmt == "json" else ACCEPT_XML
    rows, columns, note = [], [], ""
    try:
        try:
            body, _ = C.fetch(url, accept=accept)
            rows, columns = parse_data(body)
        except (ValueError, SDMXError, ET.ParseError):
            if fmt != "json":
                raise
            body, _ = C.fetch(url, accept=ACCEPT_XML)        # JSON unusable: try SDMX-ML once
            rows, columns = parse_data(body)
            note = "JSON answer was unusable; parsed SDMX-ML instead."
    except C.FetchError as err:
        if is_no_data(err.status, err.body):
            rows, columns, note = [], [], "The service says no data matches this key and period."
        elif err.status == 406 and fmt == "json":
            body, _ = C.fetch(url, accept=ACCEPT_XML)
            rows, columns = parse_data(body)
            note = "JSON not offered for this query; parsed SDMX-ML instead."
        else:
            raise C.FetchError("%s%s" % (err, _hint(err)), err.status, err.body, err.url)
    if not rows and not note:
        note = "The service returned no observations for this key and period."
    agency, fid, version = split_flow(flow)
    stem_parts = [file_prefix or provider or "sdmx", fid, key, C.period_tag(start, end, last)]
    stem_parts = [p for p in stem_parts if p]
    path = C.write_csv(rows, columns, args.out, "_".join(stem_parts)) if rows else None
    entity = ""
    for d in entity_dims:
        if rows and d in columns:
            entity = C.joined(r.get(d) for r in rows)
            break
    requested = "%s:%s" % (start or "", end or "") if (start or end) else ""
    log = C.log_data(args.out, "%s %s" % (label, flow), key, entity,
                     C.period_of((r.get("TIME_PERIOD") for r in rows), requested), url, len(rows), path)
    if args.json:
        C.report(args, rows, columns, [], log, extra={"note": note} if note else None)
        return
    if rows:
        view, constant = _table_view(rows, columns)
        if constant:
            print("Same in every row: " + "; ".join(constant))
            print()
        C.report(args, rows, columns, view, log)
    else:
        C.report(args, rows, columns, [], log)
    if note:
        print("Note: " + note)
