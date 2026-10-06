# How to use AVA in this project

If someone asks how to use AVA, which mode to pick, or how this project works, answer from this guide and point them to the section.

## What AVA is

AVA is the Institute's research assistant. It answers from a curated library of 4,000+ World Bank reports plus the documents added to this project, cites the document and the page for every claim, and says when the sources do not cover a question. It works in 60+ languages: ask in your language, and the citations stay in the original.

## The three ways to ask

| | Research, Fast | Research, Deep | Computer |
|---|---|---|---|
| What it does | One pass over the library and the project sources; a cited answer | Plans a multi-step search, reads more documents, checks the answer before replying | Runs code: analyses data files, builds tables and charts, converts documents, downloads and processes files |
| How long | Seconds | About one to two minutes | Several minutes (our test runs took about six) |
| Use it for | A fact, a definition, "what does the brief say about X" | Broad or comparative questions, "what does the evidence say about X across countries", anything you will cite | Numbers you need computed, a chart, a dataset, a long document to process, the research skills below |
| Watch for | It answers from fewer sources; ask Deep if the answer feels thin | Fast is the default: switch to Deep yourself before sending | It shows its plan and ticks steps off; outputs appear in the Outputs panel on the right |

Rule of thumb: start with Research Fast to orient, use Deep for anything you will put in a document, use Computer when the answer is a number, a file or a chart rather than a paragraph.

## Reading an answer

- Each claim carries a citation. Hover it to see the document, the page and the passage; click it to open the document at that page.
- "I don't know" or "the sources do not cover this" is a real answer. It means the library and the project's documents have nothing on it; try another phrasing, add a source, or take the question elsewhere.
- Ask a follow-up in the same thread; AVA keeps the context. Start a new thread for a new question.

## This project

- **Sources** (left panel) are the documents this project starts from. Add more with "Add sources": a PDF, a Word file, a link to a World Bank page or an Open Knowledge Repository item. Processing takes a minute; "About source processing" explains the status.
- **Threads** are conversations. Everyone in the project sees thread titles and outputs; names are not shown.
- **Outputs** (right panel) collect what you bookmark and what activities produce: documents, data tables, audio, video. Use the filter at the top.
- **Share** gives colleagues access as Editor or Viewer, or by link.

## Activities: turn an answer into something you can send

Activities make an output from an answer: Slide Deck, Briefing Doc, Mindmap, Audio Recap, Video Recap, Data Table Doc, Infographic, Charts, Implementation Strategy, Methodological Primer, Conceptual Overview, Technical Analysis, Blog Post, Study Guide, Flashcards, Quiz.

The habit that makes them work: do the research first, check the cited answer, then open the activity's settings ("Configure activity"), paste the answer with one line of instruction (who it is for, how long, which language), and generate. Tick "Save this as a reusable action" if you will do it again. Pasted citation markers can come out as empty brackets in slides; ask for citations in plain text, "(short title, p. N)", when you paste.

## Good questions get good answers

- One question per message, with the country or region and the period.
- Say who the answer is for: "for a director", "for a two-page note".
- Ask for the structure you want: key policy points; evidence points, cited; knowledge gaps; next steps.
- Ask "what do the sources not cover?" when the answer matters.
- Do not paste confidential or personal material. What goes into a shared project is visible to everyone it is shared with, and conversations may be reviewed by the AVA team to check and improve answer quality.

## After an event

If you attended a session, start with: "I attended [session] at [event]. I work on [role] in [country]. What from this session applies to my work, and what does not?" AVA answers from the session's documents and the library, separates what transfers from what does not, and ends with policy points, evidence points, gaps and next steps. Then turn it into a briefing note or six slides with an activity.

## Research beyond the library: the research skills

In Computer mode AVA can search public sources directly: World Bank Documents & Reports, Open Knowledge Repository and Projects; the World Bank indicators; the IMF's data API; DBnomics (IMF, OECD, ECB, Eurostat, ILO and more in one place); UN agencies (SDG database, UNESCO, UNICEF, UNHCR, WHO, ILO); and the academic indexes (OpenAlex, Crossref, Semantic Scholar, arXiv, NBER). The instructions and scripts live at https://github.com/chatilamoe/agora-skills. To use them, ask in Computer mode and say: "use the agora-skills research playbook"; the project instruction tells AVA where to download them. Results come back with the query, the source URL, the retrieval date, and page numbers for PDFs.

## If something fails

- An activity that is still generating shows in the Outputs panel; long ones (a deck) can take 15–20 minutes.
- A Computer run that stops: ask it to continue, or rerun with a narrower request.
- A source that will not process: check the format (PDF, DOCX, a public link), or paste the text.
- A cited page that looks wrong: click the citation and read the passage; if it does not support the claim, say so in the thread and do not use the claim.
