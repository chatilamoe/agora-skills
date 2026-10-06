# IMF dataflows: what is where, with tested keys

Checked on 2026-10-06 against `https://api.imf.org/external/sdmx/2.1`. The API holds 223 dataflows: 104 current ones and 119 dated snapshots (ids ending in `_YYYY_MON_VINTAGE`, for example `IMF.STA,CPI_2026_MAY_VINTAGE`). `imf_dataflows.py` lists them all and writes `research/catalog/imf_dataflows.csv`; `imf_dimensions.py` gives any dataflow's key and codes.

Every key in the table below was fetched with `imf_fetch.py` on 2026-10-06; the last column is the latest value it returned. Values are in full units.

## Main dataflows

| Flow | What it holds | Key order | Tested key: latest value |
|---|---|---|---|
| `IMF.RES,WEO` | World Economic Outlook, latest release (April 2026, update date 2026-04-15): 210 countries and groups, 145 indicators, 1980 to 2031 with projections | `COUNTRY.INDICATOR.FREQUENCY` | `NPL.NGDP_RPCH.A`: 2026, 2.956 (projection) |
| `IMF.RES,WEO_2025_OCT_VINTAGE` | the October 2025 WEO, values rounded to 3 decimals | same | `NPL.NGDP_RPCH.A`: 2026, 5.162 |
| `IMF.STA,CPI` | consumer prices by COICOP 1999 item; monthly, quarterly, annual | `COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY` | `NPL.CPI._T.YOY_PCH_PA_PT.M`: 2026-M03, 3.62 (percent, year on year) |
| `IMF.STA,ER` | exchange rates | `COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY` | `NPL.XDC_USD.PA_RT.A`: 2025, 139.12 (rupees per US dollar, period average) |
| `IMF.STA,IL` | international liquidity: reserves | `COUNTRY.INDICATOR.UNIT.FREQUENCY` | `NPL.RXF11_REVS.USD.M`: 2025-M12, 19,978,623,094 (US dollars, reserves excluding gold) |
| `IMF.STA,MFS_IR` | interest rates | `COUNTRY.INDICATOR.FREQUENCY` | `NPL.MFS166_RT_PT_A_PT.M`: 2026-M07, 5.75 (monetary policy-related rate, percent) |
| `IMF.STA,MFS_MA` | monetary aggregates | `COUNTRY.INDICATOR.UNIT.FREQUENCY` | `NPL.BM_MAI.XDC.M`: 2026-M03, 8,374,721,733,309 (rupees, broad money) |
| `IMF.STA,ANEA` | annual national accounts | `COUNTRY.INDICATOR.PRICE_TYPE.TYPE_OF_TRANSFORMATION.FREQUENCY` | `NPL.B1GQ.V.XDC.A`: 2025, 5,924,810,000,000 (rupees, GDP at current prices) |
| `IMF.STA,QNEA` | quarterly national accounts | `COUNTRY.INDICATOR.PRICE_TYPE.S_ADJUSTMENT.TYPE_OF_TRANSFORMATION.FREQUENCY` | `IND.B1GQ.Q.SA.XDC.Q`: 2026-Q2, 85,126,612,600,000 (rupees, GDP at constant prices, seasonally adjusted) |
| `IMF.STA,BOP` | balance of payments (BPM6) | `COUNTRY.BOP_ACCOUNTING_ENTRY.INDICATOR.UNIT.FREQUENCY` | `NPL.NETCD_T.CAB.USD.A`: 2025, 4,855,136,910 (US dollars, current account balance) |
| `IMF.STA,IIP` | international investment position | same as BOP | `NPL.NETAL_P.NIIP.USD.A`: 2025, 9,045,498,124 (US dollars, net IIP) |
| `IMF.STA,IMTS` | goods trade by partner country | `COUNTRY.INDICATOR.COUNTERPART_COUNTRY.FREQUENCY` | `NPL.XG_FOB_USD.IND.A`: 2025, 2,033,824,874 (US dollars, Nepal's exports to India) |
| `IMF.STA,GFS_SOO` | government finance, statement of operations. Same structure: `GFS_BS`, `GFS_COFOG`, `GFS_SSUC`, `GFS_SOEF`, `GFS_SFCP` | `COUNTRY.SECTOR.GFS_GRP.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY` | `NPL.S13.G1.G1_T.POGDP_PT.A`: 2021, 28.38 (percent of GDP, general government revenue; 2022 to 2024 are empty placeholders) |
| `IMF.FAD,FM` | Fiscal Monitor: 18 country groups, 8 indicators, no single countries | `COUNTRY.INDICATOR.FREQUENCY` | `G001.GNLB_S13_POGDP_PT.A`: 2026, -5.41 (percent of GDP, world general government net lending) |
| `IMF.FAD,GDD` | Global Debt Database | `COUNTRY.INDICATOR.FREQUENCY` | `NPL.FL_S1311MIXED_POGDP_PT.A`: 2024, 47.87 (percent of GDP, central government debt) |
| `IMF.STA,FSIC` | financial soundness indicators | `COUNTRY.SECTOR.INDICATOR.FREQUENCY` | `NPL.S12CFSI.AQ12_CFSI_PT.Q`: 2026-Q1, 5.30 (percent, nonperforming loans to gross loans) |
| `IMF.STA,FAS` | Financial Access Survey | `COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY` | `NPL.FA19.NUM.A`: 2025, 5,263 (ATMs in the country) |
| `IMF.RES,PCPS` | primary commodity prices (`G001` = world) | `COUNTRY.INDICATOR.DATA_TRANSFORMATION.FREQUENCY` | `G001.POILBRE.USD.M`: 2026-M09, 102.02 (US dollars a barrel, Brent) |
| `IMF.APD,APDREO` | Asia and Pacific Regional Economic Outlook; also `IMF.AFR,AFRREO`, `IMF.MCD,MCDREO`, `IMF.WHD,WHDREO` | `COUNTRY.INDICATOR.FREQUENCY` | `imf_dimensions.py IMF.APD,APDREO --key NPL` found 6 Nepal series, 1961 to 2031 |

Other current dataflows include producer prices (`PPI`), labour (`LS`), effective exchange rates (`EER`), currency composition of reserves (`COFER`), direct and portfolio investment by counterpart (`DIP`, `PIP`), international trade in services (`IMF.RES,ITS`), climate and gender indicators, and the IMF's own accounts (`FA`).

## Where the old datasets went

The old API (`dataservices.imf.org`) used dataset codes and indicator codes that no longer work. DBnomics still carries a frozen copy of it (provider `IMF`, datasets `IFS`, `DOT`, `GFSR` and so on, indexed 2025-08-26), which is how the pairs below were checked.

| Old dataset | Now | How it was checked |
|---|---|---|
| `IFS` | split into `CPI`, `ER`, `IL`, `MFS_MA`, `MFS_IR`, `MFS_CBS`, `MFS_DC`, `MFS_ODC`, `MFS_OFC`, `MFS_FC`, `MFS_FMP`, `ANEA`, `QNEA`, `BOP`, `IIP`, `PPI`, `LS` (all `IMF.STA`) | series that were in IFS carry `IFS_FLAG=true`, defined as "used to identify and mark indicators that were part of the IFS data product" |
| `DOT` (Direction of Trade Statistics) | `IMF.STA,IMTS` | `IFS`, `DOT`, `DOTS` and `GFS` return HTTP 204 (no such dataflow) |
| `GFSR`, `GFSE`, `GFSMAB`, `GFSCOFOG`, `GFSIBS`, `GFSSSUC`, `GFSFALCS` | `IMF.STA,GFS_SOO`, `GFS_COFOG`, `GFS_BS`, `GFS_SSUC`, `GFS_SOEF`, `GFS_SFCP`; quarterly `IMF.STA,QGFS` | names of the new dataflows |
| `CDIS`, `CPIS` | `IMF.STA,DIP`, `IMF.STA,PIP` | their names say "formerly CDIS", "formerly CPIS" |
| `FSI` | `IMF.STA,FSIC`, `FSIBSIS`, `FSICDM` | names of the new dataflows |
| `BOP`, `CPI`, `PCPS`, `FM`, `FAS`, `COFER` | same ids, new structures (see the key orders above) | |

Old IFS indicator codes and their new keys, with Nepal values that match:

| Old IFS series (DBnomics `IMF/IFS/...`) | New key | Same value |
|---|---|---|
| `A.NP.ENDA_XDC_USD_RATE` (rupees per US dollar, period average) | `IMF.STA,ER` `NPL.XDC_USD.PA_RT.A` | 2024: 133.7266 in both |
| `M.NP.ENDE_XDC_USD_RATE` (rupees per US dollar, end of period) | `IMF.STA,ER` `NPL.XDC_USD.EOP_RT.M` | 2025-06: 137.74 in both |
| `M.NP.RAXG_USD` (total reserves excluding gold, US dollars, millions) | `IMF.STA,IL` `NPL.RXF11_REVS.USD.M` | 2024-07: 14,030.29 million and 14,030,289,869.83: the new API is in units, not millions |
| `M.NP.FPOLM_PA` (monetary policy-related interest rate) | `IMF.STA,MFS_IR` `NPL.MFS166_RT_PT_A_PT.M` | 2025-06: 6.5 in both |
| `M.NP.PCPI_IX` (consumer prices, all items, index) | `IMF.STA,CPI` `NPL.CPI._T.IX.M` | not comparable: the old copy has no Nepal values; the new key returns 2026-M03, 106.96442 |

Old keys used two-letter country codes (`NP`); the new API uses three-letter ISO codes (`NPL`) and its own codes for groups (`G001` world, `G110` advanced economies, `GX123` other advanced economies).

## Five worked examples

Each command was run on 2026-10-06 from the repository root with Python 3.9; the output is pasted as printed.

### 1. Nepal's real GDP growth (WEO)

Find the indicator among the WEO series that exist for Nepal:

```
$ python3 skills/imf-data/scripts/imf_dimensions.py IMF.RES,WEO --key NPL..A --dim INDICATOR --search "constant prices"
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0)
Key order: COUNTRY.INDICATOR.FREQUENCY
With data under key NPL..A: 33 series, 1980-01-01 to 2031-12-31 (only codes with data are listed; --all-codes for the full lists)

[2] INDICATOR  Indicator  (IMF.RES:CL_WEO_INDICATOR(2.0.3); 33 of 145 codes have data)
    NGDP_RPCH                Gross domestic product (GDP), Constant prices, Percent change
    NGDP_R                   Gross domestic product (GDP), Constant prices, Domestic currency
    NGDPRPC                  Gross domestic product (GDP), Constant prices, Per capita, Domestic currency
    NGDPRPPPPC               Gross domestic product (GDP), Constant prices, Per capita, purchasing power parity (PPP) internation

All codes: research/catalog/imf_codes_IMF.RES_WEO_NPL..A.csv
Next: python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO <key in the order above> --start YYYY
```

Fetch it, 2020 to 2027:

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO NPL.NGDP_RPCH.A --start 2020 --end 2027
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0; IMF update date 2026-04-15)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       NGDP_RPCH                       2020       -2.369621             PT
NPL       NGDP_RPCH                       2021       4.83815               PT
NPL       NGDP_RPCH                       2022       5.631315              PT
NPL       NGDP_RPCH                       2023       1.982548              PT
NPL       NGDP_RPCH                       2024       3.665374              PT
NPL       NGDP_RPCH                       2025       4.603769              PT
NPL       NGDP_RPCH                       2026       2.956156              PT
NPL       NGDP_RPCH                       2027       4.564108              PT

8 rows, 1 series -> research/data/imf_WEO_NPL.NGDP_RPCH.A_2020-2027.csv (logged in research/data_log.jsonl)
Latest actual data: NPL NGDP_RPCH FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) [IMF.RES:WEO, updated 2026-04-15], NGDP_RPCH, NPL, 2020:2027, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL.NGDP_RPCH.A?startPeriod=2020&endPeriod=2027)
```

Read: 3.7 percent in 2024 and 4.6 percent in 2025 are actual data (FY2024/25 is filed as 2025); 3.0 percent in 2026 and 4.6 percent in 2027 are IMF staff projections from the April 2026 WEO.

### 2. Nepal's inflation: WEO annual and the monthly CPI

The WEO has annual average inflation, with projections:

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO NPL.PCPIPCH.A --start 2022 --end 2027
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0; IMF update date 2026-04-15)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       PCPIPCH                         2022       6.371161              PT
NPL       PCPIPCH                         2023       7.729683              PT
NPL       PCPIPCH                         2024       5.422712              PT
NPL       PCPIPCH                         2025       4.057243              PT
NPL       PCPIPCH                         2026       3.143759              PT
NPL       PCPIPCH                         2027       5.029498              PT

6 rows, 1 series -> research/data/imf_WEO_NPL.PCPIPCH.A_2022-2027.csv (logged in research/data_log.jsonl)
Latest actual data: NPL PCPIPCH FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) [IMF.RES:WEO, updated 2026-04-15], PCPIPCH, NPL, 2022:2027, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL.PCPIPCH.A?startPeriod=2022&endPeriod=2027)
```

The monthly consumer price index (the former IFS series) is in `IMF.STA,CPI`. Its key has five positions; `TYPE_OF_TRANSFORMATION` says what the number is:

```
$ python3 skills/imf-data/scripts/imf_dimensions.py IMF.STA,CPI --key NPL.... --dim TYPE_OF_TRANSFORMATION
IMF.STA,CPI  Consumer Price Index (CPI)  (version 5.0.0)
Key order: COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY
With data under key NPL....: 150 series, 1900-01-01 to 2026-03-31 (only codes with data are listed; --all-codes for the full lists)

[4] TYPE_OF_TRANSFORMATION  Type of Transformation  (IMF.STA:CL_CPI_TYPE_OF_TRANSFORMATION(5.0.0); 8 of 8 codes have data)
    IX                       Index
    POP_PCH_PA_PT            Period average, Period-over-period percent change
    YOY_PCH_PA_PT            Period average, Year-over-year (YOY) percent change
    WGT                      Weight
    WGT_PT                   Weight, Percent
    SRP_IX                   Standard reference period (2010=100), Index
    SRP_POP_PCH_PA_PT        Standard reference period (2010=100), Period average, Period-over-period percent change
    SRP_YOY_PCH_PA_PT        Standard reference period (2010=100), Period average, Year-over-year (YOY) percent change

All codes: research/catalog/imf_codes_IMF.STA_CPI_NPL.....csv
Next: python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,CPI <key in the order above> --start YYYY
```

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,CPI NPL.CPI._T.YOY_PCH_PA_PT.M --start 2025-10
IMF.STA,CPI  Consumer Price Index (CPI)  (version 5.0.0; IMF update date 2026-10-06)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       CPI._T.YOY_PCH_PA_PT            2025-M10   1.469304172594495             O
NPL       CPI._T.YOY_PCH_PA_PT            2025-M11   1.105567962264172             O
NPL       CPI._T.YOY_PCH_PA_PT            2025-M12   1.632020117831157             O
NPL       CPI._T.YOY_PCH_PA_PT            2026-M01   2.419317071252905             O
NPL       CPI._T.YOY_PCH_PA_PT            2026-M02   3.246110105248933             O
NPL       CPI._T.YOY_PCH_PA_PT            2026-M03   3.618740794481108             O

6 rows, 1 series -> research/data/imf_CPI_NPL.CPI._T.YOY_PCH_PA_PT.M_2025-10.csv (logged in research/data_log.jsonl)
Cite as: (IMF Consumer Price Index (CPI) [IMF.STA:CPI, updated 2026-10-06], CPI._T.YOY_PCH_PA_PT, NPL, 2025-M10:2026-M03, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/NPL.CPI._T.YOY_PCH_PA_PT.M?startPeriod=2025-10)
```

Read: the WEO puts 2025 average inflation at 4.1 percent; the CPI dataflow has the monthly year-on-year rate, 3.6 percent in March 2026, its latest month. The two measure different things (annual average against a monthly rate) and come from different releases (2026-04-15 and 2026-10-06), so quote each with its own citation.

### 3. Nepal's current account: percent of GDP (WEO) and US dollars (BOP)

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO NPL.BCA_NGDPD.A --start 2021 --end 2027
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0; IMF update date 2026-04-15)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       BCA_NGDPD                       2021       -7.701229             PT
NPL       BCA_NGDPD                       2022       -12.564009            PT
NPL       BCA_NGDPD                       2023       -0.878823             PT
NPL       BCA_NGDPD                       2024       3.874013              PT
NPL       BCA_NGDPD                       2025       6.708096              PT
NPL       BCA_NGDPD                       2026       6.906818              PT
NPL       BCA_NGDPD                       2027       2.02218               PT

7 rows, 1 series -> research/data/imf_WEO_NPL.BCA_NGDPD.A_2021-2027.csv (logged in research/data_log.jsonl)
Latest actual data: NPL BCA_NGDPD FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) [IMF.RES:WEO, updated 2026-04-15], BCA_NGDPD, NPL, 2021:2027, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL.BCA_NGDPD.A?startPeriod=2021&endPeriod=2027)
```

The balance of payments dataflow has the dollar amounts. Find the indicator:

```
$ python3 skills/imf-data/scripts/imf_dimensions.py IMF.STA,BOP --key NPL...USD.A --dim INDICATOR --search "current account"
IMF.STA,BOP  Balance of Payments (BOP)  (version 21.0.0)
Key order: COUNTRY.BOP_ACCOUNTING_ENTRY.INDICATOR.UNIT.FREQUENCY
With data under key NPL...USD.A: 767 series, 1976-01-01 to 2025-12-31 (only codes with data are listed; --all-codes for the full lists)

[3] INDICATOR  Indicator  (IMF.STA:CL_BOP_INDICATOR(10.0.0); 400 of 979 codes have data)
    CABXEF                   Current account balance excluding exceptional financing
    TCDCA                    Total current account credit/revenue
    TDBCA                    Total current account debit/expenditure
    CAB                      Current account balance (credit less debit)
    TCAKA                    Total current and capital account balances (credit less debit)
    TCAKAFA                  Total current, capital (credit less debit) and financial account balances (assets less liabilities)
    CKAB                     Current and capital account balance (credit less debit)

All codes: research/catalog/imf_codes_IMF.STA_BOP_NPL...USD.A.csv
Next: python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,BOP <key in the order above> --start YYYY
```

`CAB` with accounting entry `NETCD_T` (net, credit less debit):

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,BOP NPL.NETCD_T.CAB.USD.A --start 2021
IMF.STA,BOP  Balance of Payments (BOP)  (version 21.0.0; IMF update date 2026-10-05)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       NETCD_T.CAB.USD                 2021       -5362970002.436417    USD     O
NPL       NETCD_T.CAB.USD                 2022       -2374991141.98961     USD     O
NPL       NETCD_T.CAB.USD                 2023       1005873573.595837     USD     O
NPL       NETCD_T.CAB.USD                 2024       1674893574.704456     USD     O
NPL       NETCD_T.CAB.USD                 2025       4855136909.90263      USD     O

5 rows, 1 series -> research/data/imf_BOP_NPL.NETCD_T.CAB.USD.A_2021.csv (logged in research/data_log.jsonl)
Cite as: (IMF Balance of Payments (BOP) [IMF.STA:BOP, updated 2026-10-05], NETCD_T.CAB.USD, NPL, 2021:2025, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.STA,BOP/NPL.NETCD_T.CAB.USD.A?startPeriod=2021)
```

Read: the current account turned from a deficit of 12.6 percent of GDP in 2022 to a surplus of 6.7 percent in 2025 (WEO). The BOP dataflow puts the 2025 surplus at 4,855,136,910 US dollars, that is 4.86 billion: values are in full units even though the series' `SCALE` attribute is 6 (millions). Do not set the two side by side without checking periods: the WEO's Nepal series are fiscal years filed under calendar years (latest actual FY2024/25).

### 4. Several countries at once: South Asia's growth

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO NPL+IND+BGD+PAK+LKA.NGDP_RPCH.A --start 2024 --end 2026
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0; IMF update date 2026-04-15)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
BGD       NGDP_RPCH                       2024       4.223259              PT
BGD       NGDP_RPCH                       2025       3.489907              PT
BGD       NGDP_RPCH                       2026       4.692694              PT
IND       NGDP_RPCH                       2024       7.099269              PT
IND       NGDP_RPCH                       2025       7.618457              PT
IND       NGDP_RPCH                       2026       6.478172              PT
LKA       NGDP_RPCH                       2024       5.008733              PT
NPL       NGDP_RPCH                       2024       3.665374              PT
NPL       NGDP_RPCH                       2025       4.603769              PT
NPL       NGDP_RPCH                       2026       2.956156              PT
PAK       NGDP_RPCH                       2024       2.633962              PT
PAK       NGDP_RPCH                       2025       3.093464              PT
PAK       NGDP_RPCH                       2026       3.602952              PT

13 rows, 5 series -> research/data/imf_WEO_NPL-IND-BGD-PAK-LKA.NGDP_RPCH.A_2024-2026.csv (logged in research/data_log.jsonl)
Latest actual data: BGD NGDP_RPCH FY2024/25; IND NGDP_RPCH FY2024/25; LKA NGDP_RPCH 2024; NPL NGDP_RPCH FY2024/25; PAK NGDP_RPCH FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) [IMF.RES:WEO, updated 2026-04-15], NGDP_RPCH, <entity>, 2024:2026, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL+IND+BGD+PAK+LKA.NGDP_RPCH.A?startPeriod=2024&endPeriod=2026)
```

Read: one call, one CSV, one log line with `entity` `BGD;IND;LKA;NPL;PAK`. Sri Lanka stops at 2024: the April 2026 WEO publishes no 2025 or 2026 value for it, so say "not published", not zero. Bhutan (`BTN`), Maldives (`MDV`) and Afghanistan (`AFG`) are also WEO country codes.

### 5. Exchange rate: a former IFS series

```
$ python3 skills/imf-data/scripts/imf_dimensions.py IMF.STA,ER --key NPL...
IMF.STA,ER  Exchange Rates (ER)  (version 4.0.1)
Key order: COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY
With data under key NPL...: 48 series, 1952-01-01 to 2026-07-31 (only codes with data are listed; --all-codes for the full lists)

[1] COUNTRY  Country  (IMF.STA:CL_ER_COUNTRY_PUB(3.0.0); 1 of 348 codes have data)
    NPL                      Nepal

[2] INDICATOR  Indicator  (IMF.STA:CL_ER_INDICATOR_PUB(1.0.0); 8 of 10 codes have data)
    ECU_XDC                  ECU per domestic currency
    EUR_XDC                  Euros per domestic currency
    XDC_ECU                  Domestic currency per ECU
    XDC_EUR                  Domestic currency per Euro
    XDC_XDR                  Domestic currency per SDR
    XDC_USD                  Domestic currency per US Dollar
    XDR_XDC                  SDR per domestic currency
    USD_XDC                  US Dollar per domestic currency

[3] TYPE_OF_TRANSFORMATION  Type of Transformation  (IMF.STA:CL_ER_TYPE_OF_TRANSFORMATION(1.0.2); 2 of 2 codes have data)
    EOP_RT                   End-of-period (EoP)
    PA_RT                    Period average

[4] FREQUENCY  Frequency  (IMF:CL_FREQ(1.2.0); 3 of 34 codes have data)
    A                        Annual
    M                        Monthly
    Q                        Quarterly

All codes: research/catalog/imf_codes_IMF.STA_ER_NPL....csv
Next: python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,ER <key in the order above> --start YYYY
```

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.STA,ER NPL.XDC_USD.PA_RT.A --start 2021
IMF.STA,ER  Exchange Rates (ER)  (version 4.0.1; IMF update date 2026-10-06)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       XDC_USD.PA_RT                   2021       118.1340816049469             R
NPL       XDC_USD.PA_RT                   2022       125.1994577926091             R
NPL       XDC_USD.PA_RT                   2023       132.115460088756              R
NPL       XDC_USD.PA_RT                   2024       133.7266443154431             R
NPL       XDC_USD.PA_RT                   2025       139.1154375926956             R

5 rows, 1 series -> research/data/imf_ER_NPL.XDC_USD.PA_RT.A_2021.csv (logged in research/data_log.jsonl)
Cite as: (IMF Exchange Rates (ER) [IMF.STA:ER, updated 2026-10-06], XDC_USD.PA_RT, NPL, 2021:2025, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.STA,ER/NPL.XDC_USD.PA_RT.A?startPeriod=2021)
```

Read: the rupee averaged 139.12 per US dollar in 2025, against 118.13 in 2021. `XDC_USD` is domestic currency per US dollar; `USD_XDC` is the inverse. `PA_RT` is the period average and `EOP_RT` the end of period.

## Bonus: the same number in two WEO releases

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO_2025_OCT_VINTAGE NPL.NGDP_RPCH.A --start 2024 --end 2026
IMF.RES,WEO_2025_OCT_VINTAGE  World Economic Outlook (WEO) 2025 October  (version 1.0.0; IMF update date 2025-11-19)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
NPL       NGDP_RPCH                       2024       3.665                 PT
NPL       NGDP_RPCH                       2025       4.315                 PT
NPL       NGDP_RPCH                       2026       5.162                 PT

3 rows, 1 series -> research/data/imf_WEO_2025_OCT_VINTAGE_NPL.NGDP_RPCH.A_2024-2026.csv (logged in research/data_log.jsonl)
Latest actual data: NPL NGDP_RPCH FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) 2025 October [IMF.RES:WEO_2025_OCT_VINTAGE, updated 2025-11-19], NGDP_RPCH, NPL, 2024:2026, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO_2025_OCT_VINTAGE/NPL.NGDP_RPCH.A?startPeriod=2024&endPeriod=2026)
```

The October 2025 WEO projected 5.162 percent growth for Nepal in 2026; the April 2026 WEO projects 2.956 (example 1). Cite the release you used, by its update date.
