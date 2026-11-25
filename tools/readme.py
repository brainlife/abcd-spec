#!/usr/bin/env python3
"""Render an App manifest as a README block and insert it into a README.

    readme.py <brainlife.app.json> <README.md>      # rewrites README.md in place

The block sits between two HTML comments, right after the README's title, and replaces any
previous block, so it can be regenerated whenever the manifest changes. Text outside the block
is never changed.
"""
import json
import pathlib
import re
import sys

BEGIN = "<!-- brainlife-app:begin (generated from the App manifest; edit the manifest, not this block) -->"
END = "<!-- brainlife-app:end -->"
UNKNOWN = "unknown"


def _cell(text):
    text = "" if text in (None, UNKNOWN) else str(text)
    return re.sub(r"\s+", " ", text.replace("|", "\\|")).strip()


def _sentence(text):
    return text if not text or text[-1] in ".!?" else text + "."


def _value(v):
    if v is None or v == "":
        return ""
    return f"`{v if isinstance(v, str) else json.dumps(v)}`"


def _datatypes(items, optional=False):
    counts = {}
    for i in items:
        label = f"`{i['datatype']}`" + (" (optional)" if optional and i.get("optional") else "")
        counts[label] = counts.get(label, 0) + 1
    return " · ".join(label + (f" ×{n}" if n > 1 else "") for label, n in counts.items())


def _facts(m):
    rows = []
    if m["inputs"]:
        rows.append(("📥", "Inputs", _datatypes(m["inputs"], optional=True)))
    if m["outputs"]:
        rows.append(("📤", "Outputs", _datatypes(m["outputs"])))
    rt = m["runtime"]
    if rt.get("container") not in (None, UNKNOWN):
        rows.append(("🐳", "Container", f"`{rt['container']}`"))
    res = rt.get("resources") or {}
    parts = [f"{res[k]} {label}" for k, label in (("cpus", "CPUs"), ("memory_gb", "GB memory"),
                                                   ("walltime_hours", "h walltime")) if k in res]
    if res.get("gpu"):
        parts.append("GPU")
    if parts:
        rows.append(("⚙️", "Resources", " · ".join(parts)))
    if rt.get("licenses_required"):
        rows.append(("🔑", "Requires", ", ".join(f"`{x}`" for x in rt["licenses_required"])))
    if m.get("doi"):
        rows.append(("🔗", "Run it", f"[doi.org/{m['doi']}](https://doi.org/{m['doi']})"))
    if not rows:
        return []
    return ["| | |", "|---|---|"] + [f"| **{name}** | {value} |" for _, name, value in rows] + [""]


def render(m, references=True):
    lines = [BEGIN, "", f"> **{_cell(m['summary'])}**", ""]
    if m.get("description") not in (None, UNKNOWN):
        lines += [_cell(m["description"]), ""]
    lines += _facts(m)
    if m["inputs"]:
        lines += ["#### Inputs", "", "| Input | Datatype | Required | Description |", "|---|---|---|---|"]
        for i in m["inputs"]:
            tags = f" ({', '.join(i['datatype_tags'])})" if i.get("datatype_tags") else ""
            desc = _cell(i["description"])
            if i.get("requirements"):
                desc = _sentence(desc) + " " + _cell(i["requirements"])
            lines.append(f"| `{i['id']}` | `{i['datatype']}`{tags} | {'no' if i['optional'] else 'yes'} | {desc.strip()} |")
        lines.append("")
    if m["outputs"]:
        lines += ["#### Outputs", "", "| Output | Datatype | Description |", "|---|---|---|"]
        for o in m["outputs"]:
            lines.append(f"| `{o['id']}` | `{o['datatype']}` | {_cell(o['description'])} |")
        lines.append("")
    if m["parameters"]:
        lines += ["<details>", f"<summary><b>Parameters</b> ({len(m['parameters'])})</summary>", "",
                  "| Parameter | Type | Default | Description |", "|---|---|---|---|"]
        for p in m["parameters"]:
            desc = _cell(p["description"])
            if p.get("units"):
                desc += f" ({_cell(p['units'])})"
            if p.get("options"):
                desc += " Options: " + ", ".join(f"`{o['value']}`" for o in p["options"]) + "."
            lines.append(f"| `{p['id'].strip()}` | {p['type']} | {_value(p.get('default'))} | {desc.strip()} |")
        lines += ["", "</details>", ""]
    if references and m.get("citations"):
        lines.append("**References used by this App:**")
        for c in m["citations"]:
            text = _cell(c.get("text")) or ""
            doi = f" [doi:{c['doi']}](https://doi.org/{c['doi']})" if c.get("doi") else ""
            lines.append(f"- {text}{doi}".rstrip())
        lines.append("")
    lines.append(END)
    return "\n".join(lines) + "\n"


def insert(readme_text, block):
    """Put the block after the first Markdown title (or at the top), replacing any old block."""
    pattern = re.compile(re.escape(BEGIN.split(" (")[0]) + r".*?" + re.escape(END) + r"\n*", re.S)
    if pattern.search(readme_text):
        return pattern.sub(lambda _: block + "\n", readme_text, count=1)
    title = re.search(r"^#\s.*\n", readme_text, re.M)
    if not title:
        return block + "\n" + readme_text
    head, tail = readme_text[:title.end()], readme_text[title.end():]
    return head + "\n" + block + "\n" + tail.lstrip("\n")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    manifest = json.loads(pathlib.Path(argv[0]).read_text())
    path = pathlib.Path(argv[1])
    text = path.read_text() if path.exists() else f"# {manifest['name']}\n"
    path.write_text(insert(text, render(manifest)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
