"""Merge README-only PRs on our own App repos as readme_prs.py opens them.
Merges only when the PR is open, mergeable and changes README.md alone. Logs to merge_own_log.jsonl."""
import json, pathlib, subprocess, time

M = pathlib.Path(__file__).parent
LOG = M / "merge_own_log.jsonl"
plan = json.load(open(M / "readme_plan.json"))
own_total = sum(p["own"] for p in plan)


def gh(*args):
    r = subprocess.run(["gh", *args], text=True, capture_output=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


while True:
    done = {json.loads(l)["url"] for l in open(LOG)} if LOG.exists() else set()
    opened = [json.loads(l) for l in open(M / "readme_prs_log.jsonl")]
    own = [e for e in opened if e["own"] and e.get("status") == "opened"]
    for e in own:
        url = e["url"]
        if url in done:
            continue
        _, out, _ = gh("pr", "view", url, "--json", "files,state,mergeable")
        info = json.loads(out or "{}")
        files = [f["path"] for f in info.get("files", [])]
        if info.get("state") == "MERGED":
            result = "already merged"
        elif files != ["README.md"] or info.get("state") != "OPEN" or info.get("mergeable") != "MERGEABLE":
            result = f"skipped: state={info.get('state')} mergeable={info.get('mergeable')} files={files}"
        else:
            code, _, err = gh("pr", "merge", url, "--merge")
            result = "merged" if code == 0 else f"error: {err[:200]}"
        with open(LOG, "a") as f:
            f.write(json.dumps({"url": url, "result": result}) + "\n")
        print(result, url, flush=True)
        time.sleep(3)
    attempted = sum(1 for e in opened if e["own"])
    if attempted >= own_total + 1:  # +1 for the pilot logged by hand
        break
    time.sleep(120)
print("done", flush=True)
