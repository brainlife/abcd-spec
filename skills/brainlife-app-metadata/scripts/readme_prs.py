"""Open README pull requests that add the generated App summary block.

    python readme_prs.py plan                 # writes readme_plan.json
    python readme_prs.py run [--limit N] [--only owner/repo ...]

Own repos (brainlife org): branch in the repo itself. Other authors: fork to the viewer's account.
Only README.md changes. Every PR is logged in readme_prs_log.jsonl; repos already logged are skipped.
"""
import collections, json, pathlib, re, subprocess, sys, tempfile, time

M = pathlib.Path(__file__).parent
SPEC = pathlib.Path.home() / "git/brainlife/abcd-spec"
sys.path.insert(0, str(SPEC / "tools"))
import readme  # noqa: E402

BRANCH = "readme-app-summary"
LOG = M / "readme_prs_log.jsonl"
SKIP_NAME = re.compile(r"\btest\b|test-|-test|\btemp\b|\btmp\b|hello|template|\bwip\b", re.I)


def sh(*args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:4])}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def plan():
    apps = [a for a in json.load(open(M / "apps_full.json"))["apps"] if not a.get("projects")]
    gh = json.load(open(M / "gh_repos.json"))
    editable = {l.split()[0] for l in open(M / "editable.txt")}
    by = collections.defaultdict(list)
    for a in apps:
        by[a["github"].strip()].append(a)
    notes = [l[2:].strip() for l in open(M / "ext_findings.md") if l.startswith("- ") and "not cloneable" not in l]
    out, skipped = [], collections.Counter()
    for repo, L in sorted(by.items(), key=lambda kv: kv[0].lower()):
        v = gh.get(repo)
        if not v or v["isArchived"]:
            skipped["missing or archived"] += 1; continue
        live = [a for a in L if not a.get("deprecated_by")]
        if not live:
            skipped["all deprecated"] += 1; continue
        default = v["defaultBranchRef"]["name"] if v.get("defaultBranchRef") else "master"
        same = [a for a in live if (a.get("github_branch") or "master") == default]
        primary = (same or sorted(live, key=lambda a: a["create_date"])[-1:])[0]
        mpath = M / "enriched" / f"{primary['_id']}.json"
        if not mpath.exists():
            skipped["no enriched manifest"] += 1; continue
        m = json.loads(mpath.read_text())
        if m["summary"] == "unknown" or m.get("description") in (None, "unknown"):
            skipped["manifest incomplete"] += 1; continue
        if SKIP_NAME.search(primary["name"]) or SKIP_NAME.search(repo.split("/")[1]):
            skipped["test/template/temporary App"] += 1; continue
        own = repo in editable
        out.append({"repo": v["nameWithOwner"], "registered_as": repo, "own": own, "default_branch": default,
                    "app_id": primary["_id"], "app_name": primary["name"], "n_apps": len(live),
                    "notes": [] if own else [n for n in notes if n.startswith(repo + " ") or n.startswith(repo + ":")
                                             or n.lower().startswith(repo.lower() + " ")]})
    per_owner = collections.Counter(p["repo"].split("/")[0] for p in out if not p["own"])
    for p in out:
        p["owner_total"] = per_owner[p["repo"].split("/")[0]] if not p["own"] else 0
    json.dump(out, open(M / "readme_plan.json", "w"), indent=1)
    print(len(out), "PRs planned:", sum(p["own"] for p in out), "own,", sum(not p["own"] for p in out), "external;",
          "skipped:", dict(skipped))


def body(p, m):
    topics = ", ".join(f"`{t}`" for t in m.get("topics", []))
    if p["own"]:
        return (f"Adds a short summary of **{p['app_name']}** near the top of the README, generated from its "
                f"manifest in [brainlife/abcd-spec](https://github.com/brainlife/abcd-spec) "
                f"(`catalog/apps/{p['app_id']}.json`): a one-line summary, a short description, the DOI, the "
                f"inputs and outputs with their datatypes, the parameters with their defaults, and runtime needs.\n\n"
                f"- Only `README.md` changes; the rest of the README is untouched. The block sits between two HTML "
                f"comments so it can be regenerated.\n"
                f"- No code, inputs, outputs or parameters change, so the App runs exactly as before.\n")
    owner = p["repo"].split("/")[0]
    lines = [f"Hi @{owner}! 👋", "",
             f"Thank you for building and sharing **{p['app_name']}** on brainlife.io. We're grateful for it.", "",
             "We're making brainlife Apps easier to find and use, both for people and for AI assistants that help "
             "researchers pick the right App. As part of that, we wrote a short machine-readable description of each "
             "App from its code. This PR adds a small summary near the top of your README, generated from that "
             "description: a one-line summary and short description, the inputs and outputs with their datatypes, "
             "the parameters with their defaults, and runtime needs.", "",
             "**Only `README.md` changes.** Your text is untouched, and nothing about how the App runs is affected. "
             "The block sits between two HTML comments, so it's easy to edit or remove.", "",
             "We did our best to get it right from reading the code, but you know your App best. Please feel free to "
             "edit anything, ask us to change it, or simply close this PR if you'd rather not have it. No hard "
             "feelings at all.", "",
             "If you'd like, you could also set the repo's *About* box to:",
             f"- Description: \"{m['summary']}\""]
    if m.get("doi"):
        lines.append(f"- Website: https://doi.org/{m['doi']}")
    if topics:
        lines.append(f"- Topics: {topics}")
    if p["notes"]:
        lines += ["", "While reading the code we noticed a couple of small things you might want to look at "
                  "sometime. Just in case they're useful (and apologies if we misread anything):"]
        prefix = re.compile("^" + re.escape(p["registered_as"]) + r":?\s*", re.I)
        lines += ["- " + prefix.sub("", n) for n in p["notes"][:5]]
    if p["owner_total"] > 3:
        lines += ["", f"(This is one of {p['owner_total']} similar PRs on your brainlife App repos. Please don't feel "
                  "any pressure; merging some, all or none is perfectly fine.)"]
    lines += ["", "Thanks again for your contribution to brainlife.io!", "", "Franco Pestilli and the brainlife.io team"]
    return "\n".join(lines) + "\n"


def open_pr(p):
    m = json.loads((M / "enriched" / f"{p['app_id']}.json").read_text())
    me = sh("gh", "api", "user", "--jq", ".login")
    with tempfile.TemporaryDirectory(dir=M) as tmp:
        if p["own"]:
            push_repo = p["repo"]
        else:
            sh("gh", "repo", "fork", p["repo"], "--clone=false", "--default-branch-only", check=False)
            push_repo = None
            for _ in range(10):
                forks = json.loads(sh("gh", "api", f"repos/{p['repo']}/forks?per_page=100", check=False) or "[]")
                mine = [f["full_name"] for f in forks if f["owner"]["login"] == me]
                if mine:
                    push_repo = mine[0]; break
                time.sleep(3)
            if not push_repo:
                raise RuntimeError("fork not found")
        d = pathlib.Path(tmp) / "r"
        sh("git", "clone", "-q", "--depth", "1", "--branch", p["default_branch"], f"https://github.com/{p['repo']}", str(d))
        sh("git", "switch", "-q", "-c", BRANCH, cwd=d)
        path = d / "README.md"
        text = path.read_text() if path.exists() else f"# {p['app_name']}\n"
        path.write_text(readme.insert(text, readme.render(m)))
        if not sh("git", "status", "--porcelain", cwd=d):
            return {"status": "no change"}
        sh("git", "add", "README.md", cwd=d)
        sh("git", "-c", "user.name=Franco Pestilli", "-c", "user.email=pestilli@utexas.edu", "commit", "-q", "-m",
           "README: add a short summary of the App (inputs, outputs, parameters, runtime)", cwd=d)
        sh("git", "push", "-q", "-f", f"https://github.com/{push_repo}.git", BRANCH, cwd=d)
        head = BRANCH if p["own"] else f"{push_repo.split('/')[0]}:{BRANCH}"
        title = ("README: generated App summary (inputs, outputs, parameters, runtime)" if p["own"] else
                 "Add a short App summary to the README (for brainlife.io users and AI assistants)")
        url = sh("gh", "pr", "create", "--repo", p["repo"], "--base", p["default_branch"], "--head", head,
                 "--title", title, "--body", body(p, m))
        return {"status": "opened", "url": url}


def run():
    only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
    done = {json.loads(l)["repo"] for l in open(LOG)} if LOG.exists() else set()
    planned = json.load(open(M / "readme_plan.json"))
    planned.sort(key=lambda p: (not p["own"], p["repo"].lower()))
    n = 0
    for p in planned:
        if p["repo"] in done or (only and p["repo"] not in only) or n >= limit:
            continue
        try:
            result = open_pr(p)
        except Exception as e:  # keep going; record the failure
            result = {"status": "error", "error": str(e)[:300]}
        with open(LOG, "a") as f:
            f.write(json.dumps({"repo": p["repo"], "own": p["own"], **result}) + "\n")
        n += 1
        print(f"{n:4d} {result['status']:9s} {p['repo']} {result.get('url', result.get('error', ''))}", flush=True)
        time.sleep(15)


if __name__ == "__main__":
    {"plan": plan, "run": run}[sys.argv[1]]()
