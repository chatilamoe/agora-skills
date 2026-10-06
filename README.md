# agora-skills

Research skills for AI agents: how to find and cite academic and grey literature and official statistics through public, keyless APIs (World Bank, IMF, UN agencies, OECD, academic indexes).

Each skill is a folder with a `SKILL.md` (what it is for, when to use it, how to call the API, how to cite what comes back) and `scripts/` in Python standard library only, so they run in any sandbox without installing packages or keys.

Built by the World Bank Group Institute for Economic Development for AVA's Computer mode and for any agent that reads the SKILL.md format (Claude Code, Codex and others).

## Skills

| Skill | What it covers |
|---|---|
| `skills/research-playbook` | The method: which source for which question, the evidence log, how to cite, when to say "not found". Read first. |
| `skills/worldbank-documents` | World Bank Documents & Reports, Open Knowledge Repository, Projects & Operations; PDF download |
| `skills/worldbank-indicators` | World Bank indicators API (WDI and other sources): find an indicator, fetch tidy series |
| `skills/imf-data` | The IMF's SDMX 2.1 API (WEO, IFS, FM, BOP and more); where IMF publications live |
| `skills/dbnomics-macro` | DBnomics: 47,000 datasets from IMF, World Bank, OECD, ECB, Eurostat, ILO and others in one API |
| `skills/un-statistics` | UN SDG database, UNdata, UNESCO UIS, UNICEF, UNHCR, WHO, ILO, OECD, Eurostat, ECB, Our World in Data |
| `skills/academic-literature` | OpenAlex, Crossref, Semantic Scholar, arXiv, CORE, NBER; open-access PDFs; working-paper series |
| `skills/pdf-to-cited-text` | PDF to per-page text; find the page for a quote; verify claims |

`index.json` lists them for machines. `STATUS.md` shows which endpoints answered in the last weekly test.

## Install

Two lines, see [install.md](install.md): download the zip, read `index.json`, start with the playbook.

## For AVA users

[ava/how-to-use-ava.md](ava/how-to-use-ava.md) is the guide to AVA itself (Research Fast and Deep, Computer, projects, activities), written to be uploaded into an AVA project so AVA can answer "how do I use this?".

## Conventions

[CONVENTIONS.md](CONVENTIONS.md): layout, script rules, the `sources.jsonl` and `data_log.jsonl` records, citation formats, the weekly smoke tests.

## License

MIT. Contact: decaihub@worldbank.org.
