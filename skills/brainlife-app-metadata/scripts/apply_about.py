#!/usr/bin/env python3
"""Apply drafted GitHub About panels (description, website, topics) to App repos.

    apply_about.py --mechanical about_mechanical.json --proposals proposals.json \
                   --undo undo.json [--apply]

Without --apply it only prints what would change. With --apply it edits each repo with `gh`
and appends the previous values to the undo log before every change. It never removes a topic,
never replaces an upstream website link, and skips low-confidence descriptions.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
BANNED = re.compile(r"^(this (app|is)|brainlife(\.io)? version of)", re.I)
MAX_TOPICS = 20
SUMMARY_MAX = 350


def _replaceable_homepage(url):
    url = (url or "").strip()
    return url == "" or re.match(r"^https?://(www\.)?brainlife\.io/app/", url) is not None


def _good_description(text):
    text = (text or "").strip()
    return 0 < len(text) <= SUMMARY_MAX and not BANNED.match(text)


def plan(current, doi_url, proposal):
    """The fields to change for one repo, given its current About panel, the primary
    App's DOI link and the drafted proposal (or None)."""
    change = {}
    if doi_url and _replaceable_homepage(current.get("homepage")):
        change["homepage"] = doi_url
    if proposal:
        if (not proposal.get("keep_current_description")
                and proposal.get("confidence") in ("high", "medium")
                and _good_description(proposal.get("description"))
                and proposal["description"].strip() != (current.get("description") or "").strip()):
            change["description"] = proposal["description"].strip()
        topics = set(current.get("topics") or [])
        new = topics | {t for t in proposal.get("add_topics", []) if TOPIC.match(t)}
        if new != topics and len(new) <= MAX_TOPICS:
            change["topics"] = sorted(new)
    return change


def _gh(*args, stdin=None):
    subprocess.run(["gh", *args], input=stdin, text=True, check=True, capture_output=True)


def apply(repo, change):
    fields = {k: change[k] for k in ("description", "homepage") if k in change}
    if fields:
        _gh("api", "-X", "PATCH", f"repos/{repo}", "--input", "-", stdin=json.dumps(fields))
    if "topics" in change:
        _gh("api", "-X", "PUT", f"repos/{repo}/topics", "--input", "-",
            stdin=json.dumps({"names": change["topics"]}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mechanical", required=True, help="per-repo current values and DOI link")
    ap.add_argument("--proposals", required=True, help="drafted About text (JSON array)")
    ap.add_argument("--undo", required=True, help="undo log to append to")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    repos = json.loads(pathlib.Path(args.mechanical).read_text())
    proposals = {p["repo"]: p for p in json.loads(pathlib.Path(args.proposals).read_text())}
    undo_path = pathlib.Path(args.undo)
    undo = json.loads(undo_path.read_text()) if undo_path.exists() else []
    changed = 0
    for r in repos:
        current = {"description": r["description_current"], "homepage": r["homepage_current"],
                   "topics": r["topics_current"]}
        change = plan(current, r["homepage_new"], proposals.get(r["repo"]))
        if not change:
            continue
        changed += 1
        print(json.dumps({"repo": r["repo"], "change": change}))
        if args.apply:
            undo.append({"repo": r["repo"], "before": {k: current[k] for k in change}, "after": change})
            undo_path.write_text(json.dumps(undo, indent=1))
            apply(r["repo"], change)
    print(f"{changed} repos {'changed' if args.apply else 'would change'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
