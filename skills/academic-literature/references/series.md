# Finding working-paper series and evaluations through keyless APIs

Counts are from filter-only calls on 6 October 2026 (works published from 2023 on).

| Series | OpenAlex | Crossref | Other |
|---|---|---|---|
| World Bank Policy Research Working Papers | `openalex.py --series wb-prwp` = `doi_starts_with:10.1596/1813-9450` (1,171 since 2023) | `crossref.py --series wb-prwp` (prefix 10.1596, DOI checked; deposited as type `book`) | PDFs: `worldbank-documents` skill (Documents & Reports, OKR) |
| All World Bank DOIs | `--series worldbank` = `doi_starts_with:10.1596` (5,602) | `--publisher worldbank` | |
| IMF Working Papers | `--series imf-wp` = source S4210171147 "IMF Working Paper" (987) | `--series imf-wp` (prefix 10.5089, `type:journal-article`, container "IMF Working Papers") | all IMF DOIs: `--series imf` / `--publisher imf` (4,897) |
| NBER Working Papers | `--series nber-wp` = `doi_starts_with:10.3386/w` (4,875) | `--series nber-wp` (prefix 10.3386, type `report`) | `nber_search.py`; PDF at `nber.org/system/files/working_papers/wN/wN.pdf` |
| CEPR Discussion Papers | `--series cepr-dp`: RePEc copies (source S4306401271) by CEPR-affiliated authors (I4210140326), kept only if a location links to cepr.org (1,205 before that check) | none: CEPR DPs have no Crossref DOIs | many also sit on SSRN (`--series ssrn`) |
| 3ie impact evaluations, systematic reviews, working papers | `--series 3ie` = `doi_starts_with:10.23846` (100) | `--publisher 3ie` | institution preset `3ie` (I4210121424) |
| J-PAL evaluations | no series: J-PAL's evaluation pages are web summaries; the papers appear in journals and NBER. Use `--institution jpal` (I4210113636) with a query | | `--institution ipa` (I1313272365) for Innovations for Poverty Action |
| World Bank journals | `--series wber` (181), `--series wbro` (33) | `--publisher worldbank` does not cover them (Oxford University Press DOIs) | |
| Development journals | `--series jde` (724), `--series jdeff` (89) | | |

## Grey literature from the Bank, the Fund and the UN system

`openalex.py "QUERY" --grey` = type `report` and at least one author at the World Bank (I1334329717, I55633929), IMF (I1310145890), UN (I1286959531), UNDP (I107145371), UNICEF (I112289208), FAO (I1320745970), ILO (I1285985921), WHO (I4210105654), UNU-WIDER (I32309878), UNCTAD (I4405271075), OECD (I1288051870), IDB (I184564680), ADB (I4210129130), AfDB (I1330402449), EBRD (I35841627), BIS (I52989892), WTO (I1285402005) or IFPRI (I150314799). Matching uses `authorships.institutions.lineage`, so regional offices count.

Two gaps to know:
- IMF Working Papers are typed `article`, so `--grey` misses them; add a separate `--series imf-wp` search.
- PRWPs by authors without a Bank affiliation are missed; use `--series wb-prwp`.

Crossref publisher prefixes: OECD 10.1787, IDB 10.18235, ADB 10.22617, UNU-WIDER 10.35188, IFPRI 10.2499, ILO 10.54394, UN Publications 10.18356 (checked with `api.crossref.org/prefixes/{prefix}`).

## RePEc/IDEAS and SSRN

Neither has a usable keyless search API. IDEAS offers no public search API, and SSRN offers none and blocks scripts. OpenAlex indexes both:
- RePEc as a repository source, "RePEc: Research Papers in Economics" (S4306401271, about 1.3 million works): `openalex.py "QUERY" --series repec`. Each work's `locations` list the RePEc copies (IDEAS or EconPapers pages, series PDFs).
- SSRN as "SSRN Electronic Journal" (S4210172589), with DOIs `10.2139/ssrn.N`: `openalex.py "QUERY" --series ssrn`, or `crossref.py --publisher ssrn`.

A working paper's later journal version often has its own DOI, and OpenAlex may merge the two. Cite the version you read.
