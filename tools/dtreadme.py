"""Render the compact readme written to a datatype on brainlife.io (at most 2048 bytes).

The full record stays in the catalog; the readme summarises it and links there. A hand-written
readme already on brainlife.io comes first; when it is too long to add to, it is kept unchanged.
"""
from dtrecord import README_MAX_BYTES

TIERS = {
    1: "aggregated, non-revealing",
    2: "pseudonymised participant-level",
    3: "directly identifiable or traceable",
    4: "functionally revealing derivative",
    5: "model-associated",
}


def _apps(title, apps, cap):
    if not apps:
        return []
    names = [a["name"] for a in apps[:cap]]
    more = f", and {len(apps) - cap} more" if len(apps) > cap else ""
    return [f"**{title}:** {', '.join(names)}{more}."]


def _generated(record, url, app_cap, file_descs):
    bl, gov = record["brainlife"], record["governance"]
    out = [bl["desc"]] if bl["desc"] else []
    files = [f"- `{f.get('filename') or f.get('dirname')}`" + (f": {f['desc']}" if file_descs and f["desc"] else "")
             + ("" if f["required"] else " (optional)") for f in record["files"]]
    if files:
        out.append("**Files**\n" + "\n".join(files))
    for title, key in (("Use for", "intended_use"), ("Not for", "not_suitable_for")):
        if record["usage"][key]:
            out.append(f"**{title}:** {' '.join(record['usage'][key])}")
    out += _apps("Input to", record["usage"]["inputs_of"], app_cap)
    out += _apps("Output of", record["usage"]["outputs_of"], app_cap)
    bids = [f"- {c['datatype']}/{c['suffix']} — {c['match']}" for c in record["bids"]["correspondences"]]
    if bids:
        out.append("**BIDS**\n" + "\n".join(bids))
    if gov["default_tier"]:
        cautions = " ".join(gov["sharing_cautions"][:2])
        out.append(f"**Sharing:** Tier {gov['default_tier']} ({TIERS[gov['default_tier']]}) by default. {cautions}".rstrip())
    out.append(f"Full record: {url}")
    return "\n\n".join(out)


def render(record, catalog_url):
    original = record["brainlife"]["original"]["readme"].strip()
    for app_cap, file_descs in ((8, True), (3, True), (3, False)):
        md = _generated(record, catalog_url, app_cap, file_descs)
        if original:
            md = original + "\n\n" + md
        if len(md.encode()) <= README_MAX_BYTES:
            return md
    return record["brainlife"]["original"]["readme"] if original else md
