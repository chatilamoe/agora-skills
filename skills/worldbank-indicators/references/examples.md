# Real runs

These were recorded on 2026-10-06 from the repository root with Python 3.9.6. The same commands, run with Python 3.14.3, printed the same output. Every command exited 0. The first `wdi_find.py` call, which downloads the indicator list, took 31 s; the others took 0 to 2 s, and the smoke test took 6 s. `[...]` marks output cut for length.

## Quick start

```
$ python3 skills/worldbank-indicators/scripts/wdi_find.py account ownership
downloading the full indicator list: 29544 indicators in 30 page(s)
  page 2/30
[...]
  page 30/30
cached 29544 indicators in research/cache/wb_indicators.json
34 of 29544 indicators match account ownership; showing 25
code                      source    in    name
FX.OWN.TOTL.ZS            2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider (% of populati~
FX.OWN.TOTL.MA.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, male (% of po~
FX.OWN.TOTL.FE.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, female (% of ~
FX.OWN.TOTL.40.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, poorest 40% (~
FX.OWN.TOTL.60.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, richest 60% (~
FX.OWN.TOTL.OL.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, older adults ~
FX.OWN.TOTL.YG.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, young adults ~
FX.OWN.TOTL.PL.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, primary educa~
FX.OWN.TOTL.SO.ZS         2 WDI     name  Account ownership at a financial institution or with a mobile-money-service provider, secondary edu~
TG.VAL.TOTL.GD.ZS         2 WDI     note  Merchandise trade (% of GDP)
BM.GSR.MRCH.CD            2 WDI     note  Goods imports (BoP, current US$)
[...]
in = where the words were found: name, or only the source note (often a weaker match)
next: wdi_fetch.py CODE --country NPL --mrnev 1   (add --source ID to read the code from that source)
```

The nine name matches are the useful ones. "account" and "ownership" also occur in the trade and balance-of-payments definitions, which is why those rows show `note`.

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py FX.OWN.TOTL.ZS --country NPL --date 2011:2024
FX.OWN.TOTL.ZS  Account ownership at a financial institution or with a mobile-money-service provider (% of population ages 15+)
  WDI (source 2, last updated 2026-07-13); 5 rows with values for NPL, 2011:2024; the API suggests 2 decimals
iso3  country                       year     value
NPL   Nepal                         2011     25.31
NPL   Nepal                         2014     33.80
NPL   Nepal                         2017     45.39
NPL   Nepal                         2021     54.00
NPL   Nepal                         2024     59.99

wrote research/data/wdi_FX.OWN.TOTL.ZS_NPL_2011-2024.csv (5 rows); appended 1 line to research/data_log.jsonl
```

The CSV, and the line added to `research/data_log.jsonl`. The nine empty years between surveys were dropped.

```
country,iso3,indicator,year,value
Nepal,NPL,FX.OWN.TOTL.ZS,2011,25.3085584745673
Nepal,NPL,FX.OWN.TOTL.ZS,2014,33.8013508598438
Nepal,NPL,FX.OWN.TOTL.ZS,2017,45.3855766488135
Nepal,NPL,FX.OWN.TOTL.ZS,2021,54.0026922540655
Nepal,NPL,FX.OWN.TOTL.ZS,2024,59.9911157064883
```
```json
{"source": "worldbank-indicators", "dataset": "WDI", "indicator": "FX.OWN.TOTL.ZS", "entity": "NPL", "period": "2011:2024", "url": "https://api.worldbank.org/v2/country/NPL/indicator/FX.OWN.TOTL.ZS?format=json&per_page=1000&date=2011:2024", "accessed": "2026-10-06", "rows": 5, "file": "research/data/wdi_FX.OWN.TOTL.ZS_NPL_2011-2024.csv"}
```

```
$ python3 skills/worldbank-indicators/scripts/wdi_countries.py --region SAS
6 economies (region=SAS)
iso3  iso2  name                                region                          income               lending
BGD   BD    Bangladesh                          South Asia                      Lower middle income  IDA
BTN   BT    Bhutan                              South Asia                      Lower middle income  IDA
IND   IN    India                               South Asia                      Lower middle income  IBRD
LKA   LK    Sri Lanka                           South Asia                      Upper middle income  IDA
MDV   MV    Maldives                            South Asia                      Upper middle income  IDA
NPL   NP    Nepal                               South Asia                      Lower middle income  IDA
wrote research/data/wb_countries_region_sas.csv (6 rows); appended 1 line to research/data_log.jsonl
```

## wdi_find.py

```
$ python3 skills/worldbank-indicators/scripts/wdi_find.py "gdp per capita" --name-only --limit 8
37 of 29544 indicators match "gdp per capita"; showing 8
code                      source    in    name
NY.GDP.PCAP.CD            2 WDI     name  GDP per capita (current US$)
NY.GDP.PCAP.CN            2 WDI     name  GDP per capita (current LCU)
NY.GDP.PCAP.KN            2 WDI     name  GDP per capita (constant LCU)
NY.GDP.PCAP.KD.ZG         2 WDI     name  GDP per capita growth (annual %)
NY.GDP.PCAP.KD            2 WDI     name  GDP per capita (constant 2015 US$)
NY.GDP.PCAP.PP.CD         2 WDI     name  GDP per capita, PPP (current international $)
NY.GDP.PCAP.PP.KD         2 WDI     name  GDP per capita, PPP (constant 2021 international $)
SE.XPD.PRIM.PC.ZS         2 WDI     name  Government expenditure per student, primary (% of GDP per capita)
next: wdi_fetch.py CODE --country NPL --mrnev 1   (add --source ID to read the code from that source)
```

```
$ python3 skills/worldbank-indicators/scripts/wdi_find.py account female --source 28 --name-only --limit 5
downloading source 28: 3313 indicators in 4 page(s)
  page 2/4
  page 3/4
  page 4/4
cached 3313 indicators in research/cache/wb_indicators_source_28.json
3 of 3313 indicators match account female; showing 3
code                      source    in    name
account.t.d.1             28 FDX    name  Account, female (% age 15+)
mobileaccount.t.d.1       28 FDX    name  Mobile money account, female (% age 15+)
fin17a.17a1.d.1           28 FDX    name  Saved at a financial institution or using a mobile money account, female (% age 15+)
next: wdi_fetch.py CODE --country NPL --mrnev 1   (add --source ID to read the code from that source)
```

```
$ python3 skills/worldbank-indicators/scripts/wdi_find.py --list-sources
71 sources; pass the id to wdi_find.py --source or wdi_fetch.py --source
id   code  updated     name
1    DBS   2021-08-18  Doing Business
2    WDI   2026-07-13  World Development Indicators
3    WGI   2026-09-25  Worldwide Governance Indicators
[...]
14   GDS   2026-07-22  Gender Statistics
15   GEM   2026-09-08  Global Economic Monitor
[...]
28   FDX   2025-10-06  Global Findex database
[...]
93   FPA   2026-07-21  FPN Datahub Archive
```

```
$ python3 skills/worldbank-indicators/scripts/wdi_find.py --list-topics
21 topics; filter with wdi_find.py --topic NAME
id   name
1    Agriculture & Rural Development
2    Aid Effectiveness
3    Economy & Growth
[...]
7    Financial Sector
[...]
21   Trade
```

## wdi_fetch.py

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py NY.GDP.PCAP.CD --country "NPL;IND;BGD" --mrv 3
NY.GDP.PCAP.CD  GDP per capita (current US$)
  WDI (source 2, last updated 2026-07-13); 9 rows with values for NPL;IND;BGD, 2023:2025; the API suggests 1 decimal
iso3  country                       year     value
BGD   Bangladesh                    2023     2,551.02
BGD   Bangladesh                    2024     2,593.42
BGD   Bangladesh                    2025     2,597.34
IND   India                         2023     2,434.45
IND   India                         2024     2,591.99
IND   India                         2025     2,702.48
NPL   Nepal                         2023     1,382.38
NPL   Nepal                         2024     1,460.28
NPL   Nepal                         2025     1,535.88

wrote research/data/wdi_NY.GDP.PCAP.CD_NPL-IND-BGD_mrv3.csv (9 rows); appended 1 line to research/data_log.jsonl
```

Two codes in one call, with aggregates. The API gives `LMC` (Lower middle income) no ISO3 code; the script fills it in.

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py "FX.OWN.TOTL.FE.ZS;FX.OWN.TOTL.MA.ZS" --country "NPL;SAS;WLD;LMC" --mrnev 1
FX.OWN.TOTL.FE.ZS  Account ownership at a financial institution or with a mobile-money-service provider, female (% of population ages 15+)
  WDI (source 2, last updated 2026-07-13); 4 rows with values for NPL;SAS;WLD;LMC, 2024; the API suggests 2 decimals
iso3  country                       year     value
LMC   Lower middle income           2024     67.59
NPL   Nepal                         2024     59.78
SAS   South Asia                    2024     75.06
WLD   World                         2024     76.63

FX.OWN.TOTL.MA.ZS  Account ownership at a financial institution or with a mobile-money-service provider, male (% of population ages 15+)
  WDI (source 2, last updated 2026-07-13); 4 rows with values for NPL;SAS;WLD;LMC, 2024; the API suggests 2 decimals
iso3  country                       year     value
LMC   Lower middle income           2024     73.20
NPL   Nepal                         2024     60.23
SAS   South Asia                    2024     80.05
WLD   World                         2024     80.86

wrote research/data/wdi_FX.OWN.TOTL.FE.ZS_NPL-SAS-WLD-LMC_mrnev1.csv (4 rows); appended 1 line to research/data_log.jsonl
wrote research/data/wdi_FX.OWN.TOTL.MA.ZS_NPL-SAS-WLD-LMC_mrnev1.csv (4 rows); appended 1 line to research/data_log.jsonl
```

The same series from the Global Findex database itself. The 2024 value matches the WDI female series above (59.78):

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py account.t.d.1 --source 28 --country NPL --date 2011:2024
account.t.d.1  Account, women (% age 15+)
  Global Findex database (source 28, last updated 2025-10-06); 5 rows with values for NPL, 2011:2024; the API suggests 1 decimal
iso3  country                       year     value
NPL   Nepal                         2011     21.22
NPL   Nepal                         2014     31.27
NPL   Nepal                         2017     41.60
NPL   Nepal                         2021     49.90
NPL   Nepal                         2024     59.78

wrote research/data/wdi_account.t.d.1_NPL_2011-2024_src28.csv (5 rows); appended 1 line to research/data_log.jsonl
```
```json
{"source": "worldbank-indicators", "dataset": "Global Findex database", "indicator": "account.t.d.1", "entity": "NPL", "period": "2011:2024", "url": "https://api.worldbank.org/v2/country/NPL/indicator/account.t.d.1?format=json&per_page=1000&date=2011:2024&source=28", "accessed": "2026-10-06", "rows": 5, "file": "research/data/wdi_account.t.d.1_NPL_2011-2024_src28.csv"}
```

Cross-checking a number quoted in a document. The Bank's 2019 Findex note on the Maldives says 80 percent of adults had an account (see worldbank-documents, `references/examples.md`):

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py FX.OWN.TOTL.ZS --country MDV --date 2017
FX.OWN.TOTL.ZS  Account ownership at a financial institution or with a mobile-money-service provider (% of population ages 15+)
  WDI (source 2, last updated 2026-07-13); 1 row with values for MDV, 2017; the API suggests 2 decimals
iso3  country                       year     value
MDV   Maldives                      2017     79.55

wrote research/data/wdi_FX.OWN.TOTL.ZS_MDV_2017.csv (1 row); appended 1 line to research/data_log.jsonl
```

A monthly series (Global Economic Monitor, source 15). NPL has no monthly values in this range, so only India's rows come back:

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py CPTOTSAXN --source 15 --country "IND;NPL" --date 2025M01:2025M03
CPTOTSAXN  CPI Price, seas. adj.,,,
  Global Economic Monitor (source 15, last updated 2026-09-08); 3 rows with values for IND;NPL, 2025M01:2025M03; the API suggests 0 decimals
iso3  country                       year     value
IND   India                         2025M01  236.16
IND   India                         2025M02  236.16
IND   India                         2025M03  236.97

wrote research/data/wdi_CPTOTSAXN_IND-NPL_2025M01-2025M03_src15.csv (3 rows); appended 1 line to research/data_log.jsonl
```

An unknown code (exit 1):

```
$ python3 skills/worldbank-indicators/scripts/wdi_fetch.py NOT.A.CODE --country NPL --mrv 1
error: NOT.A.CODE: API error: Invalid value: The provided parameter value is not valid (check the code with wdi_find.py and the countries with wdi_countries.py)
```

## wdi_countries.py

```
$ python3 skills/worldbank-indicators/scripts/wdi_countries.py nepal
1 economy (name=nepal)
iso3  iso2  name                                region                          income               lending
NPL   NP    Nepal                               South Asia                      Lower middle income  IDA
wrote research/data/wb_countries_name_nepal.csv (1 row); appended 1 line to research/data_log.jsonl
```

```
$ python3 skills/worldbank-indicators/scripts/wdi_countries.py --aggregates
79 aggregates (aggregates)
iso3  iso2  name                                region                          income               lending
AFE   ZH    Africa Eastern and Southern         Aggregates                      Aggregates           Aggregates
AFR   A9    Africa                              Aggregates                      Aggregates           Aggregates
[...]
HIC   XD    High income                         Aggregates                      Aggregates           Aggregates
[...]
LMC   XN    Lower middle income                 Aggregates                      Aggregates           Aggregates
[...]
SAS   8S    South Asia                          Aggregates                      Aggregates           Aggregates
[...]
WLD   1W    World                               Aggregates                      Aggregates           Aggregates
XZN   A5    Sub-Saharan Africa excluding Sout~  Aggregates                      Aggregates           Aggregates
wrote research/data/wb_countries_aggregates.csv (79 rows); appended 1 line to research/data_log.jsonl
```

## Smoke test

```
$ python3 skills/worldbank-indicators/tests/smoke.py
OK    indicator list   api.worldbank.org/v2/indicator  (29544 indicators)
OK    indicator meta   /v2/indicator/{code}  (FX.OWN.TOTL.ZS = Account ownership at a financial institution or wi...)
OK    data             /v2/country/{iso3}/indicator/{code}?mrnev=1  (NPL 2024 = 60.0)
OK    data, source     /v2/country/{a;b}/indicator/{code}?source=28  (source 28: IND 2024, NPL 2024)
OK    countries        /v2/country  (296 economies and aggregates)
OK    sources          /v2/sources  (71 sources)
OK    source list      /v2/sources/{id}/indicators  (3313 indicators in source 28 (Global Findex))
OK    topics           /v2/topic  (21 topics)
```

## Files after the quick start and the runs above

```
research/cache/wb_countries.json
research/cache/wb_indicators.json                 (15 MB)
research/cache/wb_indicators_source_28.json
research/cache/wb_sources.json
research/data/wb_countries_aggregates.csv
research/data/wb_countries_name_nepal.csv
research/data/wb_countries_region_sas.csv
research/data/wdi_FX.OWN.TOTL.FE.ZS_NPL-SAS-WLD-LMC_mrnev1.csv
research/data/wdi_FX.OWN.TOTL.MA.ZS_NPL-SAS-WLD-LMC_mrnev1.csv
research/data/wdi_FX.OWN.TOTL.ZS_MDV_2017.csv
research/data/wdi_FX.OWN.TOTL.ZS_NPL_2011-2024.csv
research/data/wdi_CPTOTSAXN_IND-NPL_2025M01-2025M03_src15.csv
research/data/wdi_NY.GDP.PCAP.CD_NPL-IND-BGD_mrv3.csv
research/data/wdi_account.t.d.1_NPL_2011-2024_src28.csv
research/data_log.jsonl
```
