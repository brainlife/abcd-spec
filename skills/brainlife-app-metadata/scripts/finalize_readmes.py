"""Assemble agent-written READMEs (with <!-- BLOCK -->, <!-- BRAINLIFE-CITATIONS -->, <!-- FUNDING -->
placeholders), add CITATION.cff, and publish them to our App repos via a PR that is merged.

    python finalize_readmes.py build                 # writes readmes_final/<owner>__<name>.md and .cff
    python finalize_readmes.py publish [--only owner/repo ...] [--limit N]
Only README.md and CITATION.cff may change; anything else stops the PR from being merged.
"""
import base64, json, pathlib, re, subprocess, sys, time

M = pathlib.Path(__file__).parent
SKILL = pathlib.Path.home() / "git/brainlife/abcd-spec/skills/brainlife-app-metadata"
sys.path.insert(0, str(pathlib.Path.home() / "git/brainlife/abcd-spec/tools"))
import readme  # noqa: E402

FUNDING = (SKILL / "funding.md").read_text().strip()
BL_CITES = (SKILL / "brainlife-citations.md").read_text().strip()
TOOLS = json.loads((SKILL / "tool-citations.json").read_text())
TOOL_KEYS = {"freesurfer": ["freesurfer", "recon-all"], "fsl": ["fsl"], "mrtrix": ["mrtrix"], "dipy": ["dipy"],
             "ants": ["ants"], "afni": ["afni"], "mne": ["mne"], "nilearn": ["nilearn"],
             "connectome workbench": ["workbench", "wb_command"], "fmriprep": ["fmriprep"], "qsiprep": ["qsiprep"],
             "mriqc": ["mriqc"], "tractseg": ["tractseg"], "amico": ["amico"], "noddi": ["noddi"],
             "trekker": ["trekker"], "life": ["life", "encode"], "synthstrip": ["synthstrip"],
             "contrack": ["contrack"], "wma_tools": ["wma_tools", "wma-tools"], "pyafq": ["pyafq"]}
FINAL = M / "readmes_final"
LOG = M / "readme_redesign_log.jsonl"
BRANCH = "readme-redesign"


def work_items():
    items = []
    for i in range(6):
        items += json.load(open(M / f"readme_work_{i}.json"))
    return items


def manifest(path):
    return json.loads(pathlib.Path(path).read_text())


def header_badges(doi):
    tag = doi.split("/", 1)[1] if doi else ""
    parts = ['  <a href="https://github.com/brainlife/abcd-spec"><img src="https://img.shields.io/badge/ABCD_Spec-v1.1-green.svg" alt="ABCD Spec v1.1"></a>']
    if doi:
        parts.append(f'  <a href="https://doi.org/{doi}"><img src="https://img.shields.io/badge/Brainlife-{tag.replace("-", "--")}-blue.svg" alt="Run on brainlife.io"></a>')
    parts.append('  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="MIT license"></a>')
    return '<p align="center">\n' + "\n".join(parts) + "\n</p>"


def tool_citations(item, text):
    blob = " ".join(json.dumps({k: m.get(k) for k in ("software", "runtime", "summary", "description")})
                    for m in (manifest(a["manifest"]) for a in item["apps"] if not a["deprecated"]
                              and pathlib.Path(a["manifest"]).exists())).lower()
    out = []
    for tool, keys in TOOL_KEYS.items():
        doi = TOOLS[tool]["doi"]
        if doi.lower() in text.lower():
            continue
        if tool == "life":
            hit = re.search(r"\blife\b", blob) and ("linear fascicle" in blob or "encode" in blob)
        else:
            hit = any(re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", blob) for k in keys)
        if hit:
            out.append(f"- {TOOLS[tool]['text']} [doi:{doi}](https://doi.org/{doi})")
    return out


def cff(item, primary, text):
    names = []
    m = re.search(r"^## Authors\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if m:
        for line in m.group(1).splitlines():
            line = re.sub(r"\(.*?\)|\*\*.*?\*\*|<.*?>", "", line).strip(" -*")
            for name in [n.strip() for n in re.split(r",| and ", line) if n.strip()]:
                if re.fullmatch(r"[A-Z][\w'.-]+(?: [A-Z][\w'.-]+){1,3}", name):
                    names.append(name)
    authors = []
    for n in dict.fromkeys(names):
        given, family = n.rsplit(" ", 1)
        authors.append(f'  - given-names: "{given}"\n    family-names: "{family}"')
    authors.append('  - name: "brainlife.io"')
    lines = ["cff-version: 1.2.0", "message: \"If you use this App, please cite it as below, together with the "
             "software it uses (see the README).\"", "type: software", f'title: "{primary["name"]}"',
             "authors:", *authors, f'repository-code: "https://github.com/{item["repo"]}"', "license: MIT"]
    if primary.get("doi"):
        lines.insert(4, f'doi: "{primary["doi"]}"')
        lines.append(f'url: "https://doi.org/{primary["doi"]}"')
    lines += ["references:", '  - type: article', '    title: "brainlife.io: a decentralized and open-source cloud '
              'platform to support neuroscience research"', '    doi: "10.1038/s41592-024-02237-2"',
              '    journal: "Nature Methods"', '    year: 2024', '    authors:', '      - family-names: "Hayashi"',
              '        given-names: "Soichi"', '      - name: "and others"']
    return "\n".join(lines) + "\n"


ICONS = [("at a glance", "🧠"), ("versions", "🏷️"), ("running", "🚀"), ("usage", "🚀"), ("how to run", "🚀"),
         ("on brainlife", "☁️"), ("locally", "💻"), ("sample data", "🧪"), ("outputs", "📦"), ("output", "📦"),
         ("troubleshooting", "🩺"), ("known issues", "🩺"), ("notes", "📝"), ("citing", "📚"), ("citation", "📚"),
         ("references", "📚"), ("authors", "👥"), ("contributors", "👥"), ("funding", "💰"), ("acknowledg", "💰"),
         ("license", "⚖️"), ("method", "🔬"), ("how it works", "🔬"), ("inputs", "📥"), ("parameters", "⚙️")]
CITE_TIP = ("> [!TIP]\n> If you use this App in your work, please cite the App, the software it builds on and "
            "brainlife.io (below). GitHub's **Cite this repository** button gives the App citation in APA and BibTeX.")


def dedupe_citations(text):
    """Keep the first bullet for each DOI in the Citing section."""
    m = re.search(r"^## [^\n]*Cit[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return text
    seen, out = set(), []
    for line in m.group(1).splitlines(keepends=True):
        d = re.search(r"doi\.org/(10\.[^)\s]+)", line) if line.lstrip().startswith("- ") else None
        key = d.group(1).lower().rstrip(".") if d else None
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(line)
    return text[:m.start(1)] + "".join(out) + text[m.end(1):]


def visual(text):
    def icon(m):
        hashes, title = m.group(1), m.group(2).strip()
        if not title or not title[0].isalpha():
            return m.group(0)  # already has an icon
        low = title.lower()
        for key, ic in ICONS:
            if low.startswith(key) or (len(hashes) == 2 and key in low):
                return f"{hashes} {ic} {title}"
        return m.group(0)
    text = re.sub(r"^(#{2,3}) (.+)$", icon, text, flags=re.M)
    m = re.search(r"^## 📚 [^\n]*\n", text, re.M)
    if m and "[!TIP]" not in text:
        rest = re.sub(r"^\s*(If you use this App[^\n]*\n)", "", text[m.end():].lstrip("\n"), count=1)
        text = text[:m.end()] + "\n" + CITE_TIP + "\n\n" + rest
    return text


def build_one(item, src):
    text = src.read_text()
    for ph in ("<!-- BLOCK -->", "<!-- BRAINLIFE-CITATIONS -->", "<!-- FUNDING -->"):
        if text.count(ph) != 1:
            raise ValueError(f"placeholder {ph} appears {text.count(ph)} times")
    primary = next(a for a in item["apps"] if a["id"] == item["primary_app"])
    pm = manifest(primary["manifest"])
    text = re.sub(r'<p align="center">\s*\n(?:\s*<a [^\n]*img\.shields\.io[^\n]*\n)+\s*</p>',
                  lambda _: header_badges(primary.get("doi")), text, count=1)
    text = text.replace("<!-- BLOCK -->", readme.render(pm, references=False).rstrip("\n"))
    app_cite = f"- {primary['name']}. brainlife.io App." + (
        f" [doi:{primary['doi']}](https://doi.org/{primary['doi']})" if primary.get("doi") else "")
    app_refs = [f"- {c.get('text', '').strip()} [doi:{c['doi']}](https://doi.org/{c['doi']})".replace("  ", " ")
                if c.get("doi") else f"- {c.get('text', '').strip()}" for c in pm.get("citations", [])
                if c.get("text") or c.get("doi")]
    cites = "\n".join([app_cite, *app_refs, *tool_citations(item, text), BL_CITES])
    text = text.replace("<!-- BRAINLIFE-CITATIONS -->", cites).replace("<!-- FUNDING -->", FUNDING)
    text = re.sub(r"\(?<?\b(?:franpest|pestilli|franco\.pestilli|fpestilli)@[A-Za-z0-9.]+\b>?\)?",
                  "([@francopestilli](https://github.com/francopestilli))", text)
    text = visual(dedupe_citations(text))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, cff(item, primary, text)


def build():
    FINAL.mkdir(exist_ok=True)
    items = work_items()
    items.append({"repo": "brainlife/app-freesurfer", "default_branch": "master",
                  "primary_app": "62fa925519b13f0a0edd5c7c",
                  "apps": [{"id": "62fa925519b13f0a0edd5c7c", "name": "Freesurfer 7.3.2", "deprecated": False,
                            "doi": "10.25663/brainlife.app.664",
                            "manifest": str(pathlib.Path.home() / "git/brainlife/abcd-spec/catalog/apps/62fa925519b13f0a0edd5c7c.json")}]})
    ok, bad = 0, []
    for item in items:
        key = item["repo"].replace("/", "__")
        src = SKILL / "readme-exemplar.md" if item["repo"] == "brainlife/app-freesurfer" else M / "readmes_new" / f"{key}.md"
        if not src.exists():
            continue
        try:
            text, c = build_one(item, src)
        except Exception as e:
            bad.append((item["repo"], str(e))); continue
        (FINAL / f"{key}.md").write_text(text)
        (FINAL / f"{key}.cff").write_text(c)
        ok += 1
    print("built", ok, "failed", len(bad))
    for b in bad:
        print("  ", *b)


def gh(*args, stdin=None):
    r = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


def put_file(repo, path, content, message):
    sha = None
    try:
        sha = gh("api", f"repos/{repo}/contents/{path}?ref={BRANCH}", "--jq", ".sha")
    except RuntimeError:
        pass
    body = {"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": BRANCH,
            "committer": {"name": "Franco Pestilli", "email": "pestilli@utexas.edu"}}
    if sha:
        body["sha"] = sha
    gh("api", "-X", "PUT", f"repos/{repo}/contents/{path}", "--input", "-", stdin=json.dumps(body))


def publish_one(repo, key):
    info = json.loads(gh("api", f"repos/{repo}"))
    repo, base = info["full_name"], info["default_branch"]
    head = gh("api", f"repos/{repo}/git/ref/heads/{base}", "--jq", ".object.sha")
    try:
        gh("api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{BRANCH}")
    except RuntimeError:
        pass
    gh("api", "-X", "POST", f"repos/{repo}/git/refs", "-f", f"ref=refs/heads/{BRANCH}", "-f", f"sha={head}")
    put_file(repo, "README.md", (FINAL / f"{key}.md").read_text(), "README: redesign (overview, usage, outputs, citations, funding)")
    has_cff = subprocess.run(["gh", "api", f"repos/{repo}/contents/CITATION.cff?ref={base}"], capture_output=True).returncode == 0
    if not has_cff:
        put_file(repo, "CITATION.cff", (FINAL / f"{key}.cff").read_text(), "Add CITATION.cff")
    url = gh("pr", "create", "--repo", repo, "--base", base, "--head", BRANCH, "--title", "README redesign and citation file",
             "--body", "Redesigned README following the brainlife App README style (overview, generated App summary, "
             "versions, usage, outputs, troubleshooting, citations including the software the App uses, authors, "
             "funding and license)" + ("" if has_cff else ", plus a `CITATION.cff` so GitHub shows a \"Cite this "
             "repository\" button") + ". Only documentation changes; the App runs exactly as before.")
    files = json.loads(gh("pr", "view", url, "--json", "files", "--jq", "[.files[].path]"))
    if not set(files) <= {"README.md", "CITATION.cff"}:
        return {"status": "opened, not merged (unexpected files)", "url": url, "files": files}
    for old in json.loads(gh("pr", "list", "--repo", repo, "--head", "readme-app-summary", "--state", "open",
                             "--json", "url") or "[]"):
        gh("pr", "close", old["url"], "--comment", f"Superseded by {url}, which includes the same generated summary.",
           "--delete-branch")
    time.sleep(2)
    gh("pr", "merge", url, "--merge", "--delete-branch")
    return {"status": "merged", "url": url, "cff_added": not has_cff}


def publish():
    only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
    done = {json.loads(l)["repo"] for l in open(LOG)} if LOG.exists() else set()
    n = 0
    for f in sorted(FINAL.glob("*.md")):
        repo = f.stem.replace("__", "/", 1)
        if repo in done or (only and repo not in only) or n >= limit:
            continue
        try:
            result = publish_one(repo, f.stem)
        except Exception as e:
            result = {"status": "error", "error": str(e)[:300]}
        with open(LOG, "a") as fh:
            fh.write(json.dumps({"repo": repo, **result}) + "\n")
        n += 1
        print(f"{n:4d} {result['status']:9s} {repo} {result.get('url', result.get('error', ''))}", flush=True)
        time.sleep(10)


if __name__ == "__main__":
    {"build": build, "publish": publish}[sys.argv[1]]()
