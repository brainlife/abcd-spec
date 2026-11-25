"""Candidate new datatypes: BIDS suffixes that brainlife.io has no datatype for.

Lists every draft in datatypes/drafts/ and every BIDS (datatype, suffix) with no record at all,
with a recommendation for the owner to review. Nothing here creates a datatype.
"""
# Head volumes from anat show the face unless defaced (Tool 1 step 5); other raw data defaults to tier 2.
TIER_BY_BIDS_DATATYPE = {"anat": 3}


def _pairs(record):
    return {(c["datatype"], c["suffix"]) for c in record["bids"]["correspondences"] if c["match"] != "none"}


def candidates(records, index):
    registered = {n: r for n, r in records.items() if "_id" in r["brainlife"]}
    by_lower = {n.lower(): n for n in registered}
    rows = []
    for name, r in sorted(records.items()):
        if "_id" in r["brainlife"]:
            continue
        pair = next(iter(sorted(_pairs(r))), ("", ""))
        covered = sorted(n for n, reg in registered.items() if pair in _pairs(reg))
        same_dt = sorted(n for n, reg in registered.items() if any(p[0] == pair[0] for p in _pairs(reg)))
        if name.lower() in by_lower:
            rec = f"merge into {by_lower[name.lower()]} (same name, different case)"
        elif covered:
            rec = f"skip: covered by {', '.join(covered)}"
        else:
            rec = "create"
        files = [f.get("filename") or f.get("dirname") for f in r["files"]]
        rows.append({"proposed": name, "bids": f"{pair[0]}/{pair[1]}", "files": ", ".join(files),
                     "sidecars": sum(f.endswith((".json", ".tsv")) for f in files if f),
                     "tier": TIER_BY_BIDS_DATATYPE.get(pair[0], 2), "closest": ", ".join(same_dt[:3]),
                     "recommendation": rec})
    covered_all = set().union(*(_pairs(r) for r in records.values())) if records else set()
    for datatype, suffix in sorted(k for k in index if k not in covered_all):
        rows.append({"proposed": "", "bids": f"{datatype}/{suffix}", "files": "", "sidecars": 0,
                     "tier": TIER_BY_BIDS_DATATYPE.get(datatype, 2), "closest": "",
                     "recommendation": "no draft yet"})
    return rows


def render(rows):
    head = "| Proposed datatype | BIDS | Files | Sidecars | Default tier | Closest existing | Recommendation |"
    lines = [head, "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['proposed'] or '-'} | {r['bids']} | {r['files'] or '-'} | {r['sidecars']} | "
                     f"{r['tier']} | {r['closest'] or '-'} | {r['recommendation']} |")
    return "\n".join(lines) + "\n"
