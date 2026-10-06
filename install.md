# Install (for an agent)

Nothing to install: download, unzip, read. Python 3.9 or later, standard library only.

## Shell

```bash
curl -L https://github.com/chatilamoe/agora-skills/archive/refs/heads/main.zip -o agora-skills.zip
unzip -q agora-skills.zip && cd agora-skills-main
cat index.json
```

## Python only (no curl or unzip)

```python
import urllib.request, zipfile, io, json
url = "https://github.com/chatilamoe/agora-skills/archive/refs/heads/main.zip"
req = urllib.request.Request(url, headers={"User-Agent": "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"})
zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).extractall(".")
print(json.load(open("agora-skills-main/index.json"))["skills"])
```

## Then

1. Read `skills/research-playbook/SKILL.md`.
2. Read the `SKILL.md` of each skill `index.json` suggests for the question.
3. Run the scripts with `--help` first; they write to `./research/`.
4. Before relying on an endpoint, check `STATUS.md` (updated weekly by the smoke tests).

## The instruction to paste into AVA (project or system instruction)

> For research tasks in Computer mode: download https://github.com/chatilamoe/agora-skills/archive/refs/heads/main.zip, unzip it, read `index.json` and `skills/research-playbook/SKILL.md`, then the SKILL.md of each skill you need. Run their scripts (Python standard library only). Cite as the playbook says, and say what was not found.
