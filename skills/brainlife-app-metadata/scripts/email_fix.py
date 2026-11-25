"""Replace Franco's email addresses with his GitHub profile in README files of our App repos,
on every branch, through a PR per branch that changes only that README, then merge it.
Waits until finalize_readmes.py publish has finished. Logs to email_fix_log.jsonl."""
import base64, collections, json, pathlib, re, subprocess, time

M = pathlib.Path(__file__).parent
LOG = M / "email_fix_log.jsonl"
EMAIL = re.compile(r"\b(?:franpest|pestilli|franco\.pestilli|fpestilli)@[A-Za-z0-9.]+\.[a-z]{2,}\b")
README = re.compile(r"(^|/)readme(\.md|\.txt)?$", re.I)


def gh(*args, stdin=None):
    r = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


def replace(text, markdown):
    link = "[@francopestilli](https://github.com/francopestilli)" if markdown else "https://github.com/francopestilli"
    text = re.sub(r"\[([^\]]*)\]\(mailto:" + EMAIL.pattern + r"\)", link, text)
    text = re.sub(r"mailto:" + EMAIL.pattern, "https://github.com/francopestilli", text)
    text = re.sub(r"<" + EMAIL.pattern + r">", link, text)
    return EMAIL.sub(link, text)


while subprocess.run(["pgrep", "-f", "finalize_readmes.py publish"], capture_output=True).returncode == 0:
    time.sleep(60)

hits = [h for h in json.load(open(M / "email_hits.json")) if "email" in h and README.search(h["path"])]
targets = sorted({(h["repo"], h["branch"], h["path"]) for h in hits})
done = {(e["repo"], e["branch"], e["path"]) for e in map(json.loads, open(LOG))} if LOG.exists() else set()
for repo, branch, path in targets:
    if (repo, branch, path) in done:
        continue
    result = {}
    try:
        info = json.loads(gh("api", f"repos/{repo}/contents/{path}?ref={branch}"))
        text = base64.b64decode(info["content"]).decode()
        new = replace(text, path.lower().endswith(".md"))
        if new == text:
            result = {"status": "no email left"}
        else:
            head = gh("api", f"repos/{repo}/git/ref/heads/{branch}", "--jq", ".object.sha")
            work = f"github-contact-{re.sub(r'[^A-Za-z0-9._-]', '-', branch)}"
            subprocess.run(["gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{work}"], capture_output=True)
            gh("api", "-X", "POST", f"repos/{repo}/git/refs", "-f", f"ref=refs/heads/{work}", "-f", f"sha={head}")
            gh("api", "-X", "PUT", f"repos/{repo}/contents/{path}", "--input", "-", stdin=json.dumps({
                "message": "README: link Franco Pestilli's GitHub profile instead of an email address",
                "content": base64.b64encode(new.encode()).decode(), "branch": work, "sha": info["sha"],
                "committer": {"name": "Franco Pestilli", "email": "pestilli@utexas.edu"}}))
            url = gh("pr", "create", "--repo", repo, "--base", branch, "--head", work,
                     "--title", "README: GitHub profile instead of email",
                     "--body", f"Replaces Franco Pestilli's email address in `{path}` with his GitHub profile. "
                               "Only this README changes; the App runs exactly as before.")
            files = json.loads(gh("pr", "view", url, "--json", "files", "--jq", "[.files[].path]"))
            if files != [path]:
                result = {"status": "opened, not merged (unexpected files)", "url": url, "files": files}
            else:
                time.sleep(2)
                gh("pr", "merge", url, "--merge", "--delete-branch")
                result = {"status": "merged", "url": url}
    except Exception as e:
        result = {"status": "error", "error": str(e)[:300]}
    with open(LOG, "a") as f:
        f.write(json.dumps({"repo": repo, "branch": branch, "path": path, **result}) + "\n")
    print(result["status"], repo, branch, path, result.get("url", result.get("error", "")), flush=True)
    time.sleep(6)
print("done", flush=True)
