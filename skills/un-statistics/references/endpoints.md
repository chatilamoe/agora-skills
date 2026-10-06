# Endpoints: UN agencies and other official statistics, keyless

All tested on 2026-10-06 with the User-Agent `agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)`. Auth is none for every row. Example output lines are real, shortened; values are as published on that day.

| Agency (script) | What it holds | Base URL | Auth | Example call | Example output (2026-10-06) |
|---|---|---|---|---|---|
| UN SDG Global Database, UNSD (`sdg_fetch.py`) | All SDG indicators and series (about 250 indicators), countries and regions, with sex/age/location breakdowns and the custodian agency's source note. M49 area codes. | `https://unstats.un.org/SDGAPI/v1/sdg` | none | `/Series/Data?seriesCode=SI_POV_DAY1&areaCode=524&pageSize=500` | `SI_POV_DAY1, Nepal (524), 2022, value 2.4, PERCENT, source "Poverty and Inequality Portal, World Bank"` |
| UNdata SDMX, UNSD (`sdmx_fetch.py --provider undata`) | 15 dataflows: SDG harmonised global dataflow (DF_SDG_GLH), UNSD energy statistics and energy balances, greenhouse-gas inventories (UNFCCC; 43 Annex I countries, ISO3), national accounts main aggregates, MDG-era country data. (Its WDI mirror, DF_UNDATA_WDI, answered HTTP 500.) M49 area codes. | `https://data.un.org/ws/rest` (answers with a redirect to `/legacy/ws/rest`) | none | `/data/IAEG-SDGs,DF_SDG_GLH,1.26/A..SI_POV_DAY1.524...........?startPeriod=2010` | `SERIES=SI_POV_DAY1 REF_AREA=524 (Nepal) SEX=_T AGE=_T URBANISATION=_T 2022 2.4` |
| UNdata energy, UNSD (`sdmx_fetch.py --provider undata`) | UNSD Energy Statistics Database: production, trade and consumption by commodity and transaction, all countries. M49. | `https://data.un.org/ws/rest` | none | `/data/UNSD,DF_UNDATA_ENERGY,1.2/A.524.7000.01+12?startPeriod=2019` | `524 Nepal, 7000 Total Electricity, 01 Production, 2023, 13033.732 GWHR; 12 Final energy consumption, 2023, 10350.722 GWHR` |
| UNICEF Data Warehouse (`sdmx_fetch.py --provider unicef`) | 53 dataflows; GLOBAL_DATAFLOW has 800+ indicators: child mortality, nutrition, immunisation, education, WASH, child protection, child poverty. ISO3. | `https://sdmx.data.unicef.org/ws/public/sdmxapi/rest` | none | `/data/UNICEF,GLOBAL_DATAFLOW,1.0/NPL.CME_MRY0T4._T?startPeriod=2015` | `NPL, CME_MRY0T4 Under-five mortality rate, _T, 2024, 25.1172864419877, D_PER_1000_B` |
| ILOSTAT (`sdmx_fetch.py --provider ilo`) | 1,216 dataflows: unemployment, employment, labour force, wages, hours, informality, child labour; survey data and ILO modelled estimates (with projections). ISO3. | `https://sdmx.ilo.org/rest` | none | `/data/ILO,DF_UNE_2EAP_SEX_AGE_RT,1.0/NPL.A..SEX_T.AGE_YTHADULT_YGE15?startPeriod=2019&endPeriod=2024` | `NPL, UNE_2EAP_RT, SEX_T, 15+, 2024, 10.5` |
| OECD Data Explorer (`sdmx_fetch.py --provider oecd`) | About 1,550 dataflows: prices, national accounts, labour, education, health spending, trade, development aid (DAC). OECD members and partners. ISO3. | `https://sdmx.oecd.org/public/rest` | none | `/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/FRA.A.N.CPI.PA._T.N.GY?startPeriod=2019` | `FRA, CPI, growth rate over 1 year, 2024, 1.999049; 2025, 0.9437702` |
| BIS (`sdmx_fetch.py --provider bis`) | 29 dataflows: central bank policy rates, total credit, credit-to-GDP gaps, property prices, effective and US-dollar exchange rates, debt securities, banking statistics. ISO2. | `https://stats.bis.org/api/v1` | none | `/data/BIS,WS_CBPOL,1.0/M.US+GB?lastNObservations=3` | `GB 2026-08 3.75; US 2026-08 3.625` |
| ECB Data Portal (`ecb_fetch.py`, or `sdmx_fetch.py --provider ecb`) | 105 dataflows: euro reference exchange rates (EXR: 29 currencies in October 2026), HICP inflation (HICP; the older ICP flow stops at 2025-12), interest rates, money and credit. ISO2 and currency codes. | `https://data-api.ecb.europa.eu/service` | none | `/data/EXR/D.USD.EUR.SP00.A?lastNObservations=5&format=jsondata` | `USD per EUR, 2026-10-06, 1.1269` |
| UNESCO Institute for Statistics (`uis_fetch.py`) | About 5,060 indicators, mostly education: enrolment, completion, out-of-school, literacy, learning outcomes, teachers, spending; also science and culture. ISO3 and region ids such as `SDG: Southern Asia`. | `https://api.uis.unesco.org/api/public` | none | `/data/indicators?indicator=CR.1&geoUnit=NPL&footnotes=true` | `CR.1, NPL, 2021, 86.14209747314453, "Data sources: Nepal DHS 2022"` |
| WHO Global Health Observatory (`who_fetch.py`) | About 3,100 indicators: life expectancy, mortality, immunisation (WUENIC), nutrition, communicable diseases, health systems, risk factors. ISO3 and WHO regions (SEAR, AFR, ...). | `https://ghoapi.azureedge.net/api` | none | `/WHOSIS_000001?$filter=SpatialDim eq 'NPL' and Dim1 eq 'SEX_BTSX'` | `NPL, 2023, SEX_BTSX, 72.1, "72.1 [68.8-75.5]"` |
| UNHCR Refugee Statistics (`unhcr_fetch.py`) | Refugees, asylum-seekers, IDPs, stateless people, returns, by country of origin and of asylum, 1951-2025; demographics; asylum applications and decisions; solutions; IDMC; UNRWA; monthly nowcast. | `https://api.unhcr.org/population/v1` | none | `/population/?year=2024&coo=AFG&cf_type=ISO` | `2024, AFG: refugees 5766586, asylum_seekers 384732, idps 3199710` |
| Eurostat (`eurostat_fetch.py`) | EU statistics in JSON-stat: labour, HICP prices, national accounts, population, income and poverty (EU-SILC), regional data. EU, EFTA and candidate countries. ISO2 except EL (Greece) and UK. | `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data` | none | `/une_rt_a?geo=DE&geo=EL&age=Y15-74&unit=PC_ACT&sex=T&sinceTimePeriod=2019` | `EL Greece 2025 8.9; DE Germany 2020 3.6 status b (break in series); DOI 10.2908/UNE_RT_A` |
| Our World in Data (`owid_fetch.py`) | Data behind thousands of charts, compiled from UN agencies, the World Bank, academic projects; many long-run series. ISO3 plus OWID aggregates (OWID_WRL). | `https://ourworldindata.org/grapher/{slug}.csv` | none | `/gdp-per-capita-worldbank.csv?csvType=full` and `/gdp-per-capita-worldbank.metadata.json` | `Nepal,NPL,2025,5276.924,Asia`; citation `Eurostat, OECD, IMF, and World Bank (2026)` |
| UN Comtrade public preview (`comtrade_preview.py`) | Merchandise trade by reporter, partner and HS code. Preview limits: one period per call, at most 500 rows, about one call every 2 s. Comtrade's own country codes (India 699). | `https://comtradeapi.un.org/public/v1/preview/C/{A or M}/HS` | none (preview only) | `?reporterCode=524&period=2022&cmdCode=TOTAL&flowCode=M,X&partnerCode=0` | `NPL 2022 Import World TOTAL 13743903611.893; Export 1300469756.499` |

## Search and structure calls the scripts also use

| Purpose | Call |
|---|---|
| SDG indicators and series | `https://unstats.un.org/SDGAPI/v1/sdg/Indicator/List` (Swagger: `https://unstats.un.org/SDGAPI/swagger/`) |
| SDG area codes | `https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/List` |
| SDMX dataflow list | `{base}/dataflow` (UNdata, UNICEF, ILO), `{base}/dataflow/all` (OECD), `{base}/dataflow/BIS/all/latest`, `{base}/dataflow/ECB` |
| SDMX dimension order and codes | `{base}/dataflow/all/{FLOW_ID}/latest?references=all` with `Accept: application/vnd.sdmx.structure+xml;version=2.1` |
| UIS indicators, regions, data version | `/definitions/indicators`, `/definitions/geounits`, `/versions/default` (OpenAPI: `/openapi/schema.json`) |
| WHO indicators, countries | `https://ghoapi.azureedge.net/api/Indicator`, `/DIMENSION/COUNTRY/DimensionValues` |
| Eurostat catalogue | `https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en` |
| Eurostat dimensions in use | `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/{code}/latest?references=descendants&detail=referencepartial` |
| OWID chart search | `https://ourworldindata.org/api/search?q=WORDS&type=charts&hitsPerPage=20` |
| Comtrade country codes | `https://comtradeapi.un.org/files/v1/app/reference/Reporters.json`, `.../partnerAreas.json` |

## SDMX formats that work everywhere

`Accept: application/vnd.sdmx.data+json` (no version) returns SDMX-JSON from all six SDMX services above; `application/vnd.sdmx.genericdata+xml;version=2.1` returns SDMX-ML from all six. Versioned JSON is not portable: `version=1.0.0` gives HTTP 406 at ILOSTAT, `version=1.0` gives 406 at UNICEF, `version=2.0.0` gives 406 at BIS. Plain `application/json` at UNdata returns data without the structure needed to decode it.

## Not keyless on 2026-10-06

| Source | What happened | Keyless route for the same numbers |
|---|---|---|
| FAOSTAT | `https://faostatservices.fao.org/api/v1/en/definitions/domain` → HTTP 401 "Missing Authorization Header"; the older `fenixservices.fao.org` host → HTTP 521 | FAO-custodian SDG series via `sdg_fetch.py` (undernourishment SN_ITK_DEFC, food insecurity); OWID food and agriculture charts |
| UNDP Human Development Report API | `https://hdrdata.org/api/...` → "Please provide API key" / "The API key is invalid" | OWID chart `human-development-index` (UNDP HDR 2025 edition on that day; check the metadata for the edition) |
| UN Comtrade full API | `https://comtradeapi.un.org/data/v1/get/...` → HTTP 401 "missing subscription key" (a free key exists; out of scope here) | the public preview row above |
| WTO Timeseries API | `https://api.wto.org/timeseries/v1/...` → HTTP 401 "missing subscription key" | merchandise values from the Comtrade preview; tariffs are not covered by this skill |
| BIS | reported earlier as 501/406 on some paths; `https://stats.bis.org/api/v1/data/...` works without a key (SDMX-JSON 2.0 requests get 406; plain JSON or XML works) | included above |
