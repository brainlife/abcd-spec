#!/usr/bin/env python3
"""Build the App manifest catalog: one manifest per App plus a compact index for agents.

    catalog.py <manifest-dir> <out-dir>

Writes <out-dir>/apps/<brainlife App id>.json for every manifest and <out-dir>/index.json,
which lists each App's id, name, summary, repo, branch, input and output datatypes, topics,
DOI, deprecation and how many fields are still unknown. Every manifest must validate.
"""
import json
import pathlib
import sys

import blapp


def index_entry(m):
    return {
        "id": m["registry"]["id"],
        "name": m["name"],
        "summary": m["summary"],
        "github": m["registry"]["github"],
        "branch": m["registry"]["branch"],
        "doi": m.get("doi"),
        "inputs": [i["datatype"] for i in m["inputs"]],
        "outputs": [o["datatype"] for o in m["outputs"]],
        "topics": m.get("topics", []),
        "container": m["runtime"]["container"],
        "deprecated": "deprecated_by" in m,
        "unknowns": len(blapp.validate(m)[1]),
        "manifest": f"apps/{m['registry']['id']}.json",
    }


def build(manifests, out):
    out = pathlib.Path(out)
    for m in manifests:
        errors, _ = blapp.validate(m)
        if errors:
            raise ValueError(f"{m['name']}: {'; '.join(errors)}")
    (out / "apps").mkdir(parents=True, exist_ok=True)
    for m in manifests:
        (out / "apps" / f"{m['registry']['id']}.json").write_text(json.dumps(m, indent=2) + "\n")
    index = {"spec": "brainlife-app/2.0", "count": len(manifests),
             "apps": sorted((index_entry(m) for m in manifests), key=lambda e: (e["name"].lower(), e["id"]))}
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return index


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    manifests = [json.loads(p.read_text()) for p in sorted(pathlib.Path(argv[0]).glob("*.json"))]
    index = build(manifests, argv[1])
    print(f"{index['count']} Apps written to {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
