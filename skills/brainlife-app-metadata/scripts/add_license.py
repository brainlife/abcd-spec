"""Add an MIT LICENSE (Copyright (c) <created year> brainlife.io) to our App repos that have none,
through a PR that only adds LICENSE, then merge it. Uses the GitHub API only (no clones).
    python add_license.py [--limit N]
Logs to add_license_log.jsonl; repos already logged are skipped."""
import base64, json, pathlib, subprocess, sys, time

M = pathlib.Path(__file__).parent
LOG = M / "add_license_log.jsonl"
BRANCH = "add-mit-license"
MIT = """MIT License

Copyright (c) {year} brainlife.io

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def gh(*args, stdin=None):
    r = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


def add(repo):
    info = json.loads(gh("api", f"repos/{repo}"))
    repo = info["full_name"]
    if info.get("license"):
        return {"status": "already licensed", "license": info["license"]["spdx_id"]}
    if info.get("archived"):
        return {"status": "archived"}
    base = info["default_branch"]
    sha = gh("api", f"repos/{repo}/git/ref/heads/{base}", "--jq", ".object.sha")
    try:
        gh("api", "-X", "POST", f"repos/{repo}/git/refs", "-f", f"ref=refs/heads/{BRANCH}", "-f", f"sha={sha}")
    except RuntimeError as e:
        if "Reference already exists" not in str(e):
            raise
    year = info["created_at"][:4]
    content = base64.b64encode(MIT.format(year=year).encode()).decode()
    gh("api", "-X", "PUT", f"repos/{repo}/contents/LICENSE", "--input", "-", stdin=json.dumps({
        "message": "Add MIT license", "content": content, "branch": BRANCH,
        "committer": {"name": "Franco Pestilli", "email": "pestilli@utexas.edu"}}))
    url = gh("pr", "create", "--repo", repo, "--base", base, "--head", BRANCH, "--title", "Add MIT license",
             "--body", "Adds an MIT `LICENSE` (Copyright (c) " + year + " brainlife.io), the licence most brainlife "
             "App repos already use. Only `LICENSE` is added; no code changes, so the App runs exactly as before.")
    files = json.loads(gh("pr", "view", url, "--json", "files", "--jq", "[.files[].path]"))
    if files != ["LICENSE"]:
        return {"status": "opened, not merged (unexpected files)", "url": url, "files": files}
    time.sleep(2)
    gh("pr", "merge", url, "--merge", "--delete-branch")
    return {"status": "merged", "url": url, "year": year}


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
    gh_repos = json.load(open(M / "gh_repos.json"))
    editable = [l.split()[0] for l in open(M / "editable.txt") if l.startswith("brainlife/")]
    todo = [r for r in editable if gh_repos.get(r) and not gh_repos[r].get("licenseInfo")]
    done = {json.loads(l)["repo"] for l in open(LOG)} if LOG.exists() else set()
    n = 0
    for r in todo:
        if r in done or n >= limit:
            continue
        try:
            result = add(r)
        except Exception as e:
            result = {"status": "error", "error": str(e)[:300]}
        with open(LOG, "a") as f:
            f.write(json.dumps({"repo": r, **result}) + "\n")
        n += 1
        print(f"{n:4d} {result['status']:18s} {r} {result.get('url', result.get('error', ''))}", flush=True)
        time.sleep(8)
    print("done", n, "of", len(todo), flush=True)


if __name__ == "__main__":
    main()
