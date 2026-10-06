# DBnomics worked examples

Every command was run on 2026-10-06 from the repository root with Python 3.9; the output is pasted as printed. Each example sets DBnomics against the provider's own API, because the difference is the main thing to know about DBnomics: one format everywhere, but each provider copied on DBnomics' schedule.

## 1. IMF World Economic Outlook through DBnomics, and through the IMF

A mask fetches three countries in one call:

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py "IMF/WEO:2025-04/NPL+IND+BGD.NGDP_RPCH.pcent_change" --start 2023 --end 2026
SERIES                                        PERIOD       VALUE
BGD.NGDP_RPCH.pcent_change                    2023         5.775
BGD.NGDP_RPCH.pcent_change                    2024         4.223
BGD.NGDP_RPCH.pcent_change                    2025         3.76
BGD.NGDP_RPCH.pcent_change                    2026         6.53
IND.NGDP_RPCH.pcent_change                    2023         9.191
IND.NGDP_RPCH.pcent_change                    2024         6.46
IND.NGDP_RPCH.pcent_change                    2025         6.198
IND.NGDP_RPCH.pcent_change                    2026         6.265
NPL.NGDP_RPCH.pcent_change                    2023         1.953
NPL.NGDP_RPCH.pcent_change                    2024         3.101
NPL.NGDP_RPCH.pcent_change                    2025         4.047
NPL.NGDP_RPCH.pcent_change                    2026         5.483

IMF/WEO:2025-04/BGD.NGDP_RPCH.pcent_change: 4 values 2023 to 2026 (latest available 2030; DBnomics indexed 2025-05-15)
   Bangladesh – Gross domestic product, constant prices (NGDP_RPCH) – Percent change
IMF/WEO:2025-04/IND.NGDP_RPCH.pcent_change: 4 values 2023 to 2026 (latest available 2030; DBnomics indexed 2025-05-15)
   India – Gross domestic product, constant prices (NGDP_RPCH) – Percent change
IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change: 4 values 2023 to 2026 (latest available 2030; DBnomics indexed 2025-05-15)
   Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change

12 rows from 3 series -> research/data/dbn_IMF_WEO-2025-04_NPL-IND-BGD.NGDP_RPCH.pcent_change_2023-2026.csv (logged in research/data_log.jsonl)
Cite as: (IMF World Economic Outlook by countries via DBnomics [IMF/WEO:2025-04], BGD.NGDP_RPCH.pcent_change, BGD, 2023:2026, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/BGD.NGDP_RPCH.pcent_change?observations=1)
Cite as: (IMF World Economic Outlook by countries via DBnomics [IMF/WEO:2025-04], IND.NGDP_RPCH.pcent_change, IND, 2023:2026, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/IND.NGDP_RPCH.pcent_change?observations=1)
Cite as: (IMF World Economic Outlook by countries via DBnomics [IMF/WEO:2025-04], NPL.NGDP_RPCH.pcent_change, NPL, 2023:2026, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change?observations=1)
```

The same countries from the IMF's own API (skill **imf-data**):

```
$ python3 skills/imf-data/scripts/imf_fetch.py IMF.RES,WEO NPL+IND+BGD.NGDP_RPCH.A --start 2023 --end 2026
IMF.RES,WEO  World Economic Outlook (WEO)  (version 9.0.0; IMF update date 2026-04-15)
COUNTRY   INDICATOR                       PERIOD     VALUE                 UNIT    DERIV
BGD       NGDP_RPCH                       2023       5.775112              PT
BGD       NGDP_RPCH                       2024       4.223259              PT
BGD       NGDP_RPCH                       2025       3.489907              PT
BGD       NGDP_RPCH                       2026       4.692694              PT
IND       NGDP_RPCH                       2023       7.210225              PT
IND       NGDP_RPCH                       2024       7.099269              PT
IND       NGDP_RPCH                       2025       7.618457              PT
IND       NGDP_RPCH                       2026       6.478172              PT
NPL       NGDP_RPCH                       2023       1.982548              PT
NPL       NGDP_RPCH                       2024       3.665374              PT
NPL       NGDP_RPCH                       2025       4.603769              PT
NPL       NGDP_RPCH                       2026       2.956156              PT

12 rows, 3 series -> research/data/imf_WEO_NPL-IND-BGD.NGDP_RPCH.A_2023-2026.csv (logged in research/data_log.jsonl)
Latest actual data: BGD NGDP_RPCH FY2024/25; IND NGDP_RPCH FY2024/25; NPL NGDP_RPCH FY2024/25. Later periods are IMF staff estimates or projections.
Cite as: (IMF World Economic Outlook (WEO) [IMF.RES:WEO, updated 2026-04-15], NGDP_RPCH, <entity>, 2023:2026, retrieved 2026-10-06, https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL+IND+BGD.NGDP_RPCH.A?startPeriod=2023&endPeriod=2026)
```

Read: DBnomics has the April 2025 WEO (its newest IMF release, indexed 2025-05-15); the IMF serves the April 2026 WEO. For 2024, Nepal's growth is 3.101 in the first and 3.665 in the second; India's 6.46 and 7.10. Both are correct for their release. Cite the release you used, and use the IMF's API when the question is about the current outlook. DBnomics' WEO copy has no latest-actual year, so it does not show that 2026 is a projection.

## 2. World Bank WDI through DBnomics, and through the World Bank

Find the account-ownership series for Nepal inside WDI:

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py WB/WDI --dim country=NPL --q "account ownership" --max-codes 3
WB/WDI  World Development Indicators
396872 series; DBnomics indexed 2024-06-29
Dimensions, in series-code order: frequency, indicator, country
Filter: country=NPL; q="account ownership" -> 9 series
(code counts below apply the filters on the other dimensions)

[1] frequency    (1 codes with series of 1 in the codelist)
    A                      Annual                                                                                 9

[2] indicator    (9 codes with series of 1492 in the codelist)
    FX.OWN.TOTL.40.ZS      Account ownership at a financial institution or with a mobile-money-service prov       1
    FX.OWN.TOTL.60.ZS      Account ownership at a financial institution or with a mobile-money-service prov       1
    FX.OWN.TOTL.FE.ZS      Account ownership at a financial institution or with a mobile-money-service prov       1
    ... 6 more in research/catalog/dbn_codes_WB_WDI.csv

[3] country    (266 codes with series of 266 in the codelist)
    ABW                    Aruba                                                                                  9
    AFE                    Africa Eastern and Southern                                                            9
    AFG                    Afghanistan                                                                            9
    ... 263 more in research/catalog/dbn_codes_WB_WDI.csv

Series (9 match; showing 9):
  WB/WDI/A-FX.OWN.TOTL.40.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, poore
  WB/WDI/A-FX.OWN.TOTL.60.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, riche
  WB/WDI/A-FX.OWN.TOTL.FE.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, femal
  WB/WDI/A-FX.OWN.TOTL.MA.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, male 
  WB/WDI/A-FX.OWN.TOTL.OL.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, older
  WB/WDI/A-FX.OWN.TOTL.PL.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, prima
  WB/WDI/A-FX.OWN.TOTL.SO.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, secon
  WB/WDI/A-FX.OWN.TOTL.YG.ZS-NPL                               Annual – Account ownership at a financial institution or with a mobile-money-service provider, young
  WB/WDI/A-FX.OWN.TOTL.ZS-NPL                                  Annual – Account ownership at a financial institution or with a mobile-money-service provider (% of 

Series list: research/catalog/dbn_list_WB_WDI.csv
Next: python3 skills/dbnomics-macro/scripts/dbn_series.py WB/WDI/A-FX.OWN.TOTL.40.ZS-NPL --start YYYY
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py WB/WDI/A-FX.OWN.TOTL.ZS-NPL --start 2011
SERIES                                        PERIOD       VALUE
A-FX.OWN.TOTL.ZS-NPL                          2011         25.31
A-FX.OWN.TOTL.ZS-NPL                          2014         33.8
A-FX.OWN.TOTL.ZS-NPL                          2017         45.39
A-FX.OWN.TOTL.ZS-NPL                          2021         54.0

WB/WDI/A-FX.OWN.TOTL.ZS-NPL: 4 values 2011 to 2021 (latest available 2021; DBnomics indexed 2024-06-29)
   Annual – Account ownership at a financial institution or with a mobile-money-service provider (% of population ages 15+) – Nepal

4 rows from 1 series -> research/data/dbn_WB_WDI_A-FX.OWN.TOTL.ZS-NPL_2011.csv (logged in research/data_log.jsonl)
9 missing values (NA) left out
Cite as: (WB World Development Indicators via DBnomics [WB/WDI], A-FX.OWN.TOTL.ZS-NPL, NPL, 2011:2021, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/WB/WDI/A-FX.OWN.TOTL.ZS-NPL?observations=1)
```

The World Bank's own API (skill **worldbank-indicators**), for account ownership and for GDP growth:

```
$ cat native_doc.sh
curl -s "https://api.worldbank.org/v2/country/NPL/indicator/FX.OWN.TOTL.ZS?format=json&date=2011:2024" | python3 -c "import json,sys; print([(r['date'], r['value']) for r in json.load(sys.stdin)[1] if r['value'] is not None])"
curl -s "https://api.worldbank.org/v2/country/NPL/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2019:2025" | python3 -c "import json,sys; print([(r['date'], r['value']) for r in json.load(sys.stdin)[1] if r['value'] is not None])"
curl -s -H "Accept: application/vnd.sdmx.data+csv;version=1.0.0" "https://sdmx.oecd.org/public/rest/data/OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD,/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102?startPeriod=2025-Q4&dimensionAtObservation=AllDimensions" | python3 -c "import csv,sys; print([(r['TIME_PERIOD'], r['OBS_VALUE']) for r in csv.DictReader(sys.stdin)])"
```

```
$ bash native_doc.sh
[('2024', 59.9911157064883), ('2021', 54.0026922540655), ('2017', 45.3855766488135), ('2014', 33.8013508598438), ('2011', 25.3085584745673)]
[('2025', 4.43073194983359), ('2024', 3.67787459697703), ('2023', 1.98254843461849), ('2022', 5.6313145568451), ('2021', 4.838149614115), ('2020', -2.3696206292072), ('2019', 6.65705543110468)]
[('2026-Q1', '0.617206398'), ('2025-Q4', '0.051893243'), ('2026-Q2', '0.55048979')]
```

Read: DBnomics' WDI copy (indexed 2024-06-29) stops at the 2021 Findex round, 54.0 percent; the World Bank has the 2024 round, 59.99 percent. For GDP growth the copy ends at 2023, with 1.953 where the World Bank now has 1.983, and the World Bank adds 2024 (3.678) and 2025 (4.431). The third line of the script is example 3's OECD check.

## 3. OECD quarterly GDP growth

Find the dataset:

```
$ python3 skills/dbnomics-macro/scripts/dbn_search.py quarterly real gdp growth --provider OECD --datasets 2 --series 3
DBnomics search "quarterly real gdp growth" in OECD: 17 datasets matched; showing 2

OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD  Quarterly real GDP growth - OECD countries  [1521 of 1521 series match; indexed 2026-06-16]
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/A.Y.ARG.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross domestic product
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/A.Y.ARG.S1.S1.B1GQ._Z._Z._Z.PC.L.GY.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross domestic product
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/A.Y.ARG.S1.S1.P51G._Z._T._Z.PC.L.G1.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross fixed capital fo
  ... 1521 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD --q "quarterly real gdp growth"

OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20  Quarterly real GDP growth - G20 countries  [711 of 711 series match; indexed 2026-06-16]
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20/A.Y.ARG.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross domestic product
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20/A.Y.ARG.S1.S1.B1GQ._Z._Z._Z.PC.L.GY.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross domestic product
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20/A.Y.ARG.S1.S1.P51G._Z._T._Z.PC.L.G1.T0102 Annual – Calendar and seasonally adjusted – Argentina – Total economy – Total economy – Gross fixed capital fo
  ... 711 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_G20 --q "quarterly real gdp growth"

Series IDs: research/catalog/dbn_search_quarterly-real-gdp-growth.csv. Next: python3 skills/dbnomics-macro/scripts/dbn_series.py <series id> --start YYYY
```

Narrow it to the United States, quarterly, GDP:

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD --dim REF_AREA=USA --dim FREQ=Q --dim TRANSACTION=B1GQ --max-codes 3
OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD  Quarterly real GDP growth - OECD countries
1521 series; DBnomics indexed 2026-06-16; provider updated 2026-06-15
Dimensions, in series-code order: FREQ, ADJUSTMENT, REF_AREA, SECTOR, COUNTERPART_SECTOR, TRANSACTION, INSTR_ASSET, ACTIVITY, EXPENDITURE, UNIT_MEASURE, PRICE_BASE, TRANSFORMATION, TABLE_IDENTIFIER
Filter: REF_AREA=USA; FREQ=Q; TRANSACTION=B1GQ -> 3 series
(code counts below apply the filters on the other dimensions)

[1] FREQ  Frequency of observation  (2 codes with series of 34 in the codelist)
    Q                      Quarterly                                                                              3
    A                      Annual                                                                                 2

[2] ADJUSTMENT  Adjustment  (1 codes with series of 17 in the codelist)
    Y                      Calendar and seasonally adjusted                                                       3

[3] REF_AREA  Reference area  (53 codes with series of 556 in the codelist)
    ARG                    Argentina                                                                              3
    AUS                    Australia                                                                              3
    AUT                    Austria                                                                                3
    ... 50 more in research/catalog/dbn_codes_OECD_DSD_NAMAIN1-DF_QNA_EXPENDITURE_GROWTH_OECD.csv

[4] SECTOR  Institutional sector  (1 codes with series of 213 in the codelist)
    S1                     Total economy                                                                          3

[5] COUNTERPART_SECTOR  Counterpart institutional sector  (1 codes with series of 213 in the codelist)
    S1                     Total economy                                                                          3

[6] TRANSACTION  Transaction  (5 codes with series of 308 in the codelist)
    P3                     Final consumption expenditure                                                          6
    B1GQ                   Gross domestic product                                                                 3
    P51G                   Gross fixed capital formation                                                          3
    ... 2 more in research/catalog/dbn_codes_OECD_DSD_NAMAIN1-DF_QNA_EXPENDITURE_GROWTH_OECD.csv

[7] INSTR_ASSET  Financial instruments and non-financial assets  (1 codes with series of 184 in the codelist)
    _Z                     Not applicable                                                                         3

[8] ACTIVITY  Economic activity  (1 codes with series of 958 in the codelist)
    _Z                     Not applicable                                                                         3

[9] EXPENDITURE  Expenditure  (1 codes with series of 500 in the codelist)
    _Z                     Not applicable                                                                         3

[10] UNIT_MEASURE  Unit of measure  (1 codes with series of 615 in the codelist)
    PC                     Percentage change                                                                      3

[11] PRICE_BASE  Price base  (1 codes with series of 14 in the codelist)
    L                      Chain linked volume                                                                    3

[12] TRANSFORMATION  Transformation  (3 codes with series of 59 in the codelist)
    G1                     Growth rate, period on period                                                          1
    GCM                    Cumulative growth rate since base period                                               1
    GY                     Growth rate, over 1 year                                                               1

[13] TABLE_IDENTIFIER  Table identifier  (1 codes with series of 80 in the codelist)
    T0102                  Table 0102 - GDP identity from the expenditure side                                    3

Series (3 match; showing 3):
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 Quarterly – Calendar and seasonally adjusted – United States – Total economy – Total economy – Gross
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.GCM.T0102 Quarterly – Calendar and seasonally adjusted – United States – Total economy – Total economy – Gross
  OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.GY.T0102 Quarterly – Calendar and seasonally adjusted – United States – Total economy – Total economy – Gross

Series list: research/catalog/dbn_list_OECD_DSD_NAMAIN1-DF_QNA_EXPENDITURE_GROWTH_OECD.csv
Next: python3 skills/dbnomics-macro/scripts/dbn_series.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 --start YYYY
```

`G1` is growth on the previous quarter, `GY` on the same quarter a year earlier:

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 --start 2025-Q1
SERIES                                        PERIOD       VALUE
Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102     2025-Q1      -0.162516404
Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102     2025-Q2      0.945999717
Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102     2025-Q3      1.076346213
Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102     2025-Q4      0.120344611
Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102     2026-Q1      0.402843412

OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102: 5 values 2025-Q1 to 2026-Q1 (latest available 2026-Q1; DBnomics indexed 2026-06-16)
   Quarterly – Calendar and seasonally adjusted – United States – Total economy – Total economy – Gross domestic product – Not applicable – Not applicable – Not applicable – Percentage change – Chain linked volume – Growth rate, period on period – Table 0102 - GDP identity from the expenditure side

5 rows from 1 series -> research/data/dbn_OECD_DSD_NAMAIN1-DF_QNA_EXPENDITURE_GROWTH_OECD_Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102_2025-Q1.csv (logged in research/data_log.jsonl)
Cite as: (OECD Quarterly real GDP growth - OECD countries via DBnomics [OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD], Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102, USA, 2025-Q1:2026-Q1, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102?observations=1)
```

The OECD's own API (`sdmx.oecd.org`, in skill **un-statistics**), third line of `native_doc.sh` above: `[('2026-Q1', '0.617206398'), ('2025-Q4', '0.051893243'), ('2026-Q2', '0.55048979')]`.

Read: DBnomics (indexed 2026-06-16) ends at 2026-Q1 with 0.403 percent. The OECD now has 2026-Q2, 0.550 percent, and has revised 2026-Q1 to 0.617 and 2025-Q4 to 0.052 (0.120 in the copy).

## 4. ECB: exchange rate and euro area inflation

The ECB is re-indexed every few days (2026-10-04), so DBnomics is current here:

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py ECB/EXR/D.USD.EUR.SP00.A --start 2026-09-28
SERIES                                        PERIOD       VALUE
D.USD.EUR.SP00.A                              2026-09-28   1.1378
D.USD.EUR.SP00.A                              2026-09-29   1.1355
D.USD.EUR.SP00.A                              2026-09-30   1.1355
D.USD.EUR.SP00.A                              2026-10-01   1.1298
D.USD.EUR.SP00.A                              2026-10-02   1.1225

ECB/EXR/D.USD.EUR.SP00.A: 5 values 2026-09-28 to 2026-10-02 (latest available 2026-10-02; DBnomics indexed 2026-10-04)
   Daily – US dollar – Euro – Spot – Average

5 rows from 1 series -> research/data/dbn_ECB_EXR_D.USD.EUR.SP00.A_2026-09-28.csv (logged in research/data_log.jsonl)
Cite as: (ECB Exchange Rates via DBnomics [ECB/EXR], D.USD.EUR.SP00.A, <entity>, 2026-09-28:2026-10-02, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/ECB/EXR/D.USD.EUR.SP00.A?observations=1)
```

Euro area HICP inflation. Find the series:

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py ECB/HICP --dim REF_AREA=U2 --dim ICP_ITEM=000000 --dim FREQ=M --max-codes 3
ECB/HICP  Indices of Consumer Prices
90170 series; DBnomics indexed 2026-10-04
Dimensions, in series-code order: FREQ, REF_AREA, ADJUSTMENT, ICP_ITEM, DATA_PROVIDER, ICP_SUFFIX
Filter: REF_AREA=U2; ICP_ITEM=000000; FREQ=M -> 5 series
(code counts below apply the filters on the other dimensions)

[1] FREQ  Frequency  (2 codes with series of 10 in the codelist)
    A                      Annual                                                                                 7
    M                      Monthly                                                                                5

[2] REF_AREA  Reference area  (32 codes with series of 906 in the codelist)
    DE                     Germany                                                                                7
    AT                     Austria                                                                                5
    BE                     Belgium                                                                                5
    ... 29 more in research/catalog/dbn_codes_ECB_HICP.csv

[3] ADJUSTMENT  Adjustment indicator  (2 codes with series of 10 in the codelist)
    N                      Neither seasonally nor working day adjusted                                            4
    Y                      Working day and seasonally adjusted                                                    1

[4] ICP_ITEM  Classification - ICP context  (479 codes with series of 532 in the codelist)
    FOOD00                 HICP - Food including alcohol and tobacco                                              6
    FOODPR                 HICP - Processed food including alcohol and tobacco                                    6
    FOODUN                 HICP - Unprocessed food                                                                6
    ... 476 more in research/catalog/dbn_codes_ECB_HICP.csv

[5] DATA_PROVIDER  Data provider  (2 codes with series of 1044 in the codelist)
    4D0                    Statistical Office of the European Commission (Eurostat)                               4
    4F0                    European Central Bank (ECB)                                                            1

[6] ICP_SUFFIX  Series variation - ICP context  (4 codes with series of 51 in the codelist)
    INX                    Index                                                                                  2
    ANR                    Annual rate of change                                                                  1
    CTR                    Annual rate of change at constant tax rates (HICP-CT)                                  1
    ... 1 more in research/catalog/dbn_codes_ECB_HICP.csv

Series (5 match; showing 5):
  ECB/HICP/M.U2.N.000000.4D0.ANR                               Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Neither
  ECB/HICP/M.U2.N.000000.4D0.CTR                               Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Neither
  ECB/HICP/M.U2.N.000000.4D0.CTX                               Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Neither
  ECB/HICP/M.U2.N.000000.4D0.INX                               Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Neither
  ECB/HICP/M.U2.Y.000000.4F0.INX                               Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Working

Series list: research/catalog/dbn_list_ECB_HICP.csv
Next: python3 skills/dbnomics-macro/scripts/dbn_series.py ECB/HICP/M.U2.N.000000.4D0.ANR --start YYYY
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py ECB/HICP/M.U2.N.000000.4D0.ANR --start 2026-01
SERIES                                        PERIOD       VALUE
M.U2.N.000000.4D0.ANR                         2026-01      1.7
M.U2.N.000000.4D0.ANR                         2026-02      1.9
M.U2.N.000000.4D0.ANR                         2026-03      2.6
M.U2.N.000000.4D0.ANR                         2026-04      3.0
M.U2.N.000000.4D0.ANR                         2026-05      3.2
M.U2.N.000000.4D0.ANR                         2026-06      2.8
M.U2.N.000000.4D0.ANR                         2026-07      2.9
M.U2.N.000000.4D0.ANR                         2026-08      3.2
M.U2.N.000000.4D0.ANR                         2026-09      3.8

ECB/HICP/M.U2.N.000000.4D0.ANR: 9 values 2026-01 to 2026-09 (latest available 2026-09; DBnomics indexed 2026-10-04)
   Monthly – Euro area (Member States and Institutions of the Euro Area) changing composition – Neither seasonally nor working day adjusted – HICP - Total – Statistical Office of the European Commission (Eurostat) – Annual rate of change

9 rows from 1 series -> research/data/dbn_ECB_HICP_M.U2.N.000000.4D0.ANR_2026-01.csv (logged in research/data_log.jsonl)
Cite as: (ECB Indices of Consumer Prices via DBnomics [ECB/HICP], M.U2.N.000000.4D0.ANR, U2, 2026-01:2026-09, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/ECB/HICP/M.U2.N.000000.4D0.ANR?observations=1)
```

The older ECB dataset still answers but stopped in December 2025:

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py ECB/ICP/M.U2.N.000000.4.ANR --start 2025-10
SERIES                                        PERIOD       VALUE
M.U2.N.000000.4.ANR                           2025-10      2.1
M.U2.N.000000.4.ANR                           2025-11      2.1
M.U2.N.000000.4.ANR                           2025-12      1.9

ECB/ICP/M.U2.N.000000.4.ANR: 3 values 2025-10 to 2025-12 (latest available 2025-12; DBnomics indexed 2026-10-04)
   Monthly – Euro area (changing composition) – Neither seasonally nor working day adjusted – HICP - Overall index – Eurostat – Annual rate of change

3 rows from 1 series -> research/data/dbn_ECB_ICP_M.U2.N.000000.4.ANR_2025-10.csv (logged in research/data_log.jsonl)
Cite as: (ECB Indices of Consumer prices via DBnomics [ECB/ICP], M.U2.N.000000.4.ANR, U2, 2025-10:2025-12, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/ECB/ICP/M.U2.N.000000.4.ANR?observations=1)
```

Read: euro area annual inflation was 3.8 percent in September 2026 (`ECB/HICP/M.U2.N.000000.4D0.ANR`). The series many scripts still use, `ECB/ICP/M.U2.N.000000.4.ANR`, ends at 2025-12: same concept, older dataset. When a series stops early, look for a newer dataset from the same provider before saying "no data".

## 5. One call across providers

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL --start 2019
SERIES                                        PERIOD       VALUE
NPL.NGDP_RPCH.pcent_change                    2019         6.657
NPL.NGDP_RPCH.pcent_change                    2020         -2.37
NPL.NGDP_RPCH.pcent_change                    2021         4.838
NPL.NGDP_RPCH.pcent_change                    2022         5.631
NPL.NGDP_RPCH.pcent_change                    2023         1.953
NPL.NGDP_RPCH.pcent_change                    2024         3.101
NPL.NGDP_RPCH.pcent_change                    2025         4.047
NPL.NGDP_RPCH.pcent_change                    2026         5.483
NPL.NGDP_RPCH.pcent_change                    2027         5.039
NPL.NGDP_RPCH.pcent_change                    2028         5.002
NPL.NGDP_RPCH.pcent_change                    2029         5.0
NPL.NGDP_RPCH.pcent_change                    2030         4.999
A-NY.GDP.MKTP.KD.ZG-NPL                       2019         6.65705543110468
A-NY.GDP.MKTP.KD.ZG-NPL                       2020         -2.3696206292072
A-NY.GDP.MKTP.KD.ZG-NPL                       2021         4.838149614115
A-NY.GDP.MKTP.KD.ZG-NPL                       2022         5.63131455871746
A-NY.GDP.MKTP.KD.ZG-NPL                       2023         1.95254463264347

IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change: 12 values 2019 to 2030 (latest available 2030; DBnomics indexed 2025-05-15)
   Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change
WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL: 5 values 2019 to 2023 (latest available 2023; DBnomics indexed 2024-06-29)
   Annual – GDP growth (annual %) – Nepal

17 rows from 2 series -> research/data/dbn_2series_5ff5bd2d_2019.csv (logged in research/data_log.jsonl)
Cite as: (IMF World Economic Outlook by countries via DBnomics [IMF/WEO:2025-04], NPL.NGDP_RPCH.pcent_change, NPL, 2019:2030, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change?observations=1)
Cite as: (WB World Development Indicators via DBnomics [WB/WDI], A-NY.GDP.MKTP.KD.ZG-NPL, NPL, 2019:2023, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL?observations=1)
```

Read: one CSV with an IMF and a World Bank series, and one `data_log.jsonl` line listing both datasets and both series codes. The two copies agree to three decimals from 2019 to 2023, both with 1.953 for 2023, where the World Bank's current data say 1.983 (example 2): a copy is only as recent as its last indexing.

## Finding a series when the words do not match

Search matches whole words. `gdp` matches "GDP" in "Percent of GDP", so old IMF GFS tables come first and WEO growth does not appear:

```
$ python3 skills/dbnomics-macro/scripts/dbn_search.py nepal gdp --datasets 2 --series 4
DBnomics search "nepal gdp": 116 datasets matched; showing 2 (34 older releases or duplicates hidden; --all-releases shows them)

IMF/GFSIBS  Government Finance Statistics (GFS), Integrated Balance Sheet (Stock Positions and Flows ~  [1776 of 689088 series match; indexed 2025-08-31]
  IMF/GFSIBS/A.NP.S13.XDC_R_B1GQ.G31.N113N.W0_S1             Annual – Nepal – General government – Percent of GDP – Investment in nonfinancial assets – Machinery & equipme
  IMF/GFSIBS/A.NP.S13.XDC_R_B1GQ.G31.N114N.W0_S1             Annual – Nepal – General government – Percent of GDP – Investment in nonfinancial assets – Weapons systems – T
  IMF/GFSIBS/A.NP.S13.XDC_R_B1GQ.G31.N11KN.W0_S1             Annual – Nepal – General government – Percent of GDP – Investment in nonfinancial assets – Buildings & structu
  IMF/GFSIBS/A.NP.S13.XDC_R_B1GQ.G31.N11N.W0_S1              Annual – Nepal – General government – Percent of GDP – Investment in nonfinancial assets – Fixed assets – Tota
  ... 1776 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/GFSIBS --q "nepal gdp"

IMF/GFSR  Government Finance Statistics (GFS), Revenue  [672 of 262080 series match; indexed 2025-08-31]
  IMF/GFSR/A.NP.S13.XDC_R_B1GQ.1A_S1_G13                     Annual – Nepal – General government – Percent of GDP – Grants revenue from int orgs
  IMF/GFSR/A.NP.S13.XDC_R_B1GQ.1A_S1_G13C                    Annual – Nepal – General government – Percent of GDP – Grants revenue from int orgs: current
  IMF/GFSR/A.NP.S13.XDC_R_B1GQ.1A_S1_G13K                    Annual – Nepal – General government – Percent of GDP – Grants revenue from int orgs: capital
  IMF/GFSR/A.NP.S13.XDC_R_B1GQ.W00_S1W_G1442                 Annual – Nepal – General government – Percent of GDP – Revenue from other transfers: capital
  ... 672 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/GFSR --q "nepal gdp"

Series IDs: research/catalog/dbn_search_nepal-gdp.csv. Next: python3 skills/dbnomics-macro/scripts/dbn_series.py <series id> --start YYYY
```

Once you know the dataset, search inside it with the words the provider uses:

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/WEO:2025-04 --q "nepal gross domestic product constant prices" --max-codes 2
IMF/WEO:2025-04  World Economic Outlook by countries
8624 series; DBnomics indexed 2025-05-15; source https://www.imf.org/en/Publications/WEO/weo-database/2025/april
Dimensions, in series-code order: weo-country, weo-subject, unit
Filter: q="nepal gross domestic product constant prices" -> 4 series
(code counts below apply the filters on the other dimensions)

[1] weo-country  WEO Country  (1 codes with series of 196 in the codelist)
    NPL                    Nepal                                                                                  4

[2] weo-subject  WEO Subject  (4 codes with series of 44 in the codelist)
    NGDPRPC                Gross domestic product per capita, constant prices                                     1
    NGDPRPPPPC             Gross domestic product per capita, constant prices                                     1
    ... 2 more in research/catalog/dbn_codes_IMF_WEO-2025-04.csv

[3] unit  Unit  (3 codes with series of 12 in the codelist)
    national_currency      National currency                                                                      2
    pcent_change           Percent change                                                                         1
    ... 1 more in research/catalog/dbn_codes_IMF_WEO-2025-04.csv

Series (4 match; showing 4):
  IMF/WEO:2025-04/NPL.NGDPRPC.national_currency                Nepal – Gross domestic product per capita, constant prices (NGDPRPC) – National currency
  IMF/WEO:2025-04/NPL.NGDPRPPPPC.purchasing_power_parity_2021_international_dollar Nepal – Gross domestic product per capita, constant prices (NGDPRPPPPC) – Purchasing power parity; 2
  IMF/WEO:2025-04/NPL.NGDP_R.national_currency                 Nepal – Gross domestic product, constant prices (NGDP_R) – National currency
  IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change                   Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change

Series list: research/catalog/dbn_list_IMF_WEO-2025-04.csv
Next: python3 skills/dbnomics-macro/scripts/dbn_series.py IMF/WEO:2025-04/NPL.NGDPRPC.national_currency --start YYYY
```

## Output of the commands in SKILL.md

Quick start:

```
$ python3 skills/dbnomics-macro/scripts/dbn_search.py nepal inflation --datasets 3
DBnomics search "nepal inflation": 42 datasets matched; showing 3 (33 older releases or duplicates hidden; --all-releases shows them)

DESTATIS/99911BJ013  International indicators, Gross domestic product (GDP), current prices, GDP per capita, c~  [7 of 1358 series match; indexed 2026-06-27]
  DESTATIS/99911BJ013/ST458.INT600                           Nepal – Gross domestic product (GDP), current prices
  DESTATIS/99911BJ013/ST458.INT601                           Nepal – GDP per capita, current prices
  DESTATIS/99911BJ013/ST458.INT602                           Nepal – GDP, constant prices (annual change)
  DESTATIS/99911BJ013/ST458.INT603                           Nepal – Inflation (annual change of CPI)
  DESTATIS/99911BJ013/ST458.INT604                           Nepal – Gross value added: Agriculture (share of GDP)
  ... 7 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py DESTATIS/99911BJ013 --q "nepal inflation"

IMF/WEO:2025-04  World Economic Outlook by countries  [4 of 8624 series match; indexed 2025-05-15]
  IMF/WEO:2025-04/NPL.PCPI.idx                               Nepal – Inflation, average consumer prices (PCPI) – Index
  IMF/WEO:2025-04/NPL.PCPIE.idx                              Nepal – Inflation, end of period consumer prices (PCPIE) – Index
  IMF/WEO:2025-04/NPL.PCPIEPCH.pcent_change                  Nepal – Inflation, end of period consumer prices (PCPIEPCH) – Percent change
  IMF/WEO:2025-04/NPL.PCPIPCH.pcent_change                   Nepal – Inflation, average consumer prices (PCPIPCH) – Percent change

WB/WDI  World Development Indicators  [3 of 396872 series match; indexed 2024-06-29]
  WB/WDI/A-FP.CPI.TOTL.ZG-NPL                                Annual – Inflation, consumer prices (annual %) – Nepal
  WB/WDI/A-NY.GDP.DEFL.KD.ZG-NPL                             Annual – Inflation, GDP deflator (annual %) – Nepal
  WB/WDI/A-NY.GDP.DEFL.KD.ZG.AD-NPL                          Annual – Inflation, GDP deflator: linked series (annual %) – Nepal

Series IDs: research/catalog/dbn_search_nepal-inflation.csv. Next: python3 skills/dbnomics-macro/scripts/dbn_series.py <series id> --start YYYY
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/WEO:2025-04 --dim weo-country=NPL --dim weo-subject=NGDP_RPCH,PCPIPCH --max-codes 3
IMF/WEO:2025-04  World Economic Outlook by countries
8624 series; DBnomics indexed 2025-05-15; source https://www.imf.org/en/Publications/WEO/weo-database/2025/april
Dimensions, in series-code order: weo-country, weo-subject, unit
Filter: weo-country=NPL; weo-subject=NGDP_RPCH+PCPIPCH -> 2 series
(code counts below apply the filters on the other dimensions)

[1] weo-country  WEO Country  (196 codes with series of 196 in the codelist)
    ABW                    Aruba                                                                                  2
    AFG                    Afghanistan                                                                            2
    AGO                    Angola                                                                                 2
    ... 193 more in research/catalog/dbn_codes_IMF_WEO-2025-04.csv

[2] weo-subject  WEO Subject  (44 codes with series of 44 in the codelist)
    BCA                    Current account balance                                                                1
    BCA_NGDPD              Current account balance                                                                1
    GGR                    General government revenue                                                             1
    ... 41 more in research/catalog/dbn_codes_IMF_WEO-2025-04.csv

[3] unit  Unit  (1 codes with series of 12 in the codelist)
    pcent_change           Percent change                                                                         2

Series (2 match; showing 2):
  IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change                   Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change
  IMF/WEO:2025-04/NPL.PCPIPCH.pcent_change                     Nepal – Inflation, average consumer prices (PCPIPCH) – Percent change

Series list: research/catalog/dbn_list_IMF_WEO-2025-04.csv
Next: python3 skills/dbnomics-macro/scripts/dbn_series.py IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change --start YYYY
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change --start 2015
SERIES                                        PERIOD       VALUE
NPL.NGDP_RPCH.pcent_change                    2015         3.976
NPL.NGDP_RPCH.pcent_change                    2016         0.433
NPL.NGDP_RPCH.pcent_change                    2017         8.977
NPL.NGDP_RPCH.pcent_change                    2018         7.622
NPL.NGDP_RPCH.pcent_change                    2019         6.657
NPL.NGDP_RPCH.pcent_change                    2020         -2.37
NPL.NGDP_RPCH.pcent_change                    2021         4.838
NPL.NGDP_RPCH.pcent_change                    2022         5.631
NPL.NGDP_RPCH.pcent_change                    2023         1.953
NPL.NGDP_RPCH.pcent_change                    2024         3.101
NPL.NGDP_RPCH.pcent_change                    2025         4.047
NPL.NGDP_RPCH.pcent_change                    2026         5.483
NPL.NGDP_RPCH.pcent_change                    2027         5.039
NPL.NGDP_RPCH.pcent_change                    2028         5.002
NPL.NGDP_RPCH.pcent_change                    2029         5.0
NPL.NGDP_RPCH.pcent_change                    2030         4.999

IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change: 16 values 2015 to 2030 (latest available 2030; DBnomics indexed 2025-05-15)
   Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change

16 rows from 1 series -> research/data/dbn_IMF_WEO-2025-04_NPL.NGDP_RPCH.pcent_change_2015.csv (logged in research/data_log.jsonl)
Cite as: (IMF World Economic Outlook by countries via DBnomics [IMF/WEO:2025-04], NPL.NGDP_RPCH.pcent_change, NPL, 2015:2030, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change?observations=1)
```

Script examples:

```
$ python3 skills/dbnomics-macro/scripts/dbn_search.py euro area hicp --provider ECB --datasets 2 --series 2
DBnomics search "euro area hicp" in ECB: 108 datasets matched; showing 2

ECB/SPF  Survey of Professional Forecasters  [130739 of 506002 series match; indexed 2026-10-04]
  ECB/SPF/A.U2.HICP.F0_0T0_4.P12M.Q.001                      Annual – Euro area (changing composition) – Harmonised ICP – from 0.0 to 0.4 – Target period ends 12 months af
  ECB/SPF/A.U2.HICP.F0_0T0_4.P12M.Q.002                      Annual – Euro area (changing composition) – Harmonised ICP – from 0.0 to 0.4 – Target period ends 12 months af
  ... 130739 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py ECB/SPF --q "euro area hicp"

ECB/HICP  Indices of Consumer Prices  [3424 of 90170 series match; indexed 2026-10-04]
  ECB/HICP/A.AT.N.000000.4D0.10W                             Annual – Austria – Neither seasonally nor working day adjusted – HICP - Total – Statistical Office of the Euro
  ECB/HICP/A.AT.N.000000.4D0.I9W                             Annual – Austria – Neither seasonally nor working day adjusted – HICP - Total – Statistical Office of the Euro
  ... 3424 match in this dataset: python3 skills/dbnomics-macro/scripts/dbn_dataset.py ECB/HICP --q "euro area hicp"

Series IDs: research/catalog/dbn_search_euro-area-hicp.csv. Next: python3 skills/dbnomics-macro/scripts/dbn_series.py <series id> --start YYYY
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF --q "economic outlook 2025"
IMF  International Monetary Fund  (provider last indexed 2025-09-04; terms: http://datahelp.imf.org/tos)
DATASET                                         NAME
WEOAGG:2025-04                                  World Economic Outlook by country groups (2025-04 release)
WEO:2025-04                                     World Economic Outlook by countries (2025-04 release)

2 of 106 datasets. Full list: research/catalog/dbn_datasets_IMF.csv. Next: python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/<DATASET>
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py ECB/EXR/D.USD.EUR.SP00.A --start 2026-10-01 --json

2 rows from 1 series -> research/data/dbn_ECB_EXR_D.USD.EUR.SP00.A_2026-10-01.csv (logged in research/data_log.jsonl)
Cite as: (ECB Exchange Rates via DBnomics [ECB/EXR], D.USD.EUR.SP00.A, <entity>, 2026-10-01:2026-10-02, retrieved 2026-10-06, https://api.db.nomics.world/v22/series/ECB/EXR/D.USD.EUR.SP00.A?observations=1)
{
 "url": "https://api.db.nomics.world/v22/series/ECB/EXR/D.USD.EUR.SP00.A?observations=1&metadata=0&limit=1000",
 "file": "research/data/dbn_ECB_EXR_D.USD.EUR.SP00.A_2026-10-01.csv",
 "series": [
  {
   "id": "ECB/EXR/D.USD.EUR.SP00.A",
   "provider": "ECB",
   "dataset": "EXR",
   "series_code": "D.USD.EUR.SP00.A",
   "dataset_name": "Exchange Rates",
   "series_name": "Daily – US dollar – Euro – Spot – Average",
   "frequency": "daily",
   "entity": "",
   "indexed_at": "2026-10-04",
   "observations": 2,
   "first": "2026-10-01",
   "last": "2026-10-02",
   "last_available": "2026-10-02"
  }
 ],
 "rows": [
  {
   "provider": "ECB",
   "dataset": "EXR",
   "series_code": "D.USD.EUR.SP00.A",
   "series_name": "Daily – US dollar – Euro – Spot – Average",
   "frequency": "daily",
   "period": "2026-10-01",
   "value": 1.1298
  },
  {
   "provider": "ECB",
   "dataset": "EXR",
   "series_code": "D.USD.EUR.SP00.A",
   "series_name": "Daily – US dollar – Euro – Spot – Average",
   "frequency": "daily",
   "period": "2026-10-02",
   "value": 1.1225
  }
 ]
}
```

Two errors, as the scripts report them:

```
$ python3 skills/dbnomics-macro/scripts/dbn_dataset.py IMF/WEO:2025-04 --dim country=NPL
error: this dataset has no dimension 'country'; it has: weo-country, weo-subject, unit
```

```
$ python3 skills/dbnomics-macro/scripts/dbn_series.py IMF/WEO:2025-04/NPL.NOPE.x
error: HTTP 404: Series 'IMF/WEO:2025-04/NPL.NOPE.x' not found (https://api.db.nomics.world/v22/series/IMF/WEO:2025-04/NPL.NOPE.x?observations=1&metadata=0&limit=1000)
```
