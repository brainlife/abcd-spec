"""Render the short readme written to a datatype on brainlife.io.

Datatype records are sent with every data object, so the readme stays small: what to use it for,
how it maps to BIDS, its default sharing tier, how many Apps use it, and a link to the full
catalog record (files, App list, governance rationale). A hand-written readme already on
brainlife.io is kept and only gets the sharing line and the link; when that would push it past
2048 bytes it is kept unchanged.
"""
from dtrecord import README_MAX_BYTES

SUMMARY_MAX_BYTES = 700
TIERS = {
    1: "aggregated, non-revealing",
    2: "pseudonymised participant-level",
    3: "directly identifiable or traceable",
    4: "functionally revealing derivative",
    5: "model-associated",
}


def _sharing(record):
    tier = record["governance"]["default_tier"]
    return f"**Sharing:** Tier {tier} ({TIERS[tier]}) by default." if tier else ""


def _clip(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _apps(record):
    n_in, n_out = len(record["usage"]["inputs_of"]), len(record["usage"]["outputs_of"])
    parts = [f"Input to {n_in} App{'s' * (n_in != 1)}"] if n_in else []
    parts += [f"output of {n_out} App{'s' * (n_out != 1)}"] if n_out else []
    return ("**Apps:** " + ", ".join(parts) + ".") if parts else ""


def _summary(record, url, clip):
    usage = record["usage"]
    lines = [f"**{title}:** {_clip(' '.join(usage[key]), clip)}"
             for title, key in (("Use for", "intended_use"), ("Not for", "not_suitable_for")) if usage[key]]
    bids = [f"{c['datatype']}/{c['suffix']} ({c['match']})" for c in record["bids"]["correspondences"]
            if c["match"] != "none"]
    lines.append("**BIDS:** " + (_clip(", ".join(bids), clip) if bids else "no BIDS counterpart."))
    lines += [_sharing(record), _apps(record), f"Full record: {url}"]
    return "\n\n".join(x for x in lines if x)


GENERATED = ("**Use for:**", "**Not for:**", "**BIDS:**", "**Sharing:**", "**Apps:**", "Full record: ")


def strip_generated(text):
    """Remove what render() appended last time, so a pushed readme is not taken as hand-written."""
    paragraphs = text.split("\n\n")
    if not paragraphs or not paragraphs[-1].startswith("Full record: "):
        return text
    while paragraphs and paragraphs[-1].startswith(GENERATED):
        paragraphs.pop()
    return "\n\n".join(paragraphs).rstrip()


def render(record, catalog_url):
    original = strip_generated(record["brainlife"]["original"]["readme"])
    if original.strip():
        md = "\n\n".join(x for x in (original.rstrip(), _sharing(record), f"Full record: {catalog_url}") if x)
        return md if len(md.encode()) <= README_MAX_BYTES else original
    for clip in (300, 160, 80):
        md = _summary(record, catalog_url, clip)
        if len(md.encode()) <= SUMMARY_MAX_BYTES:
            return md
    return md
