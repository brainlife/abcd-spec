"""Re-save brainlife App records so they pick up the GitHub description/topics; set or clear the
tagline override. Never sends inputs, outputs or config. Stops at the first App whose run-time
fields change. Usage: python bl_sync.py [--limit N]"""
import json, os, pathlib, sys, time, urllib.request, urllib.error, collections

M = pathlib.Path(__file__).parent
API = "https://brainlife.io/api/warehouse/app/"
TOKEN = pathlib.Path(os.path.expanduser("~/.config/brainlife.io/.jwt")).read_text().strip().strip('"')
ALLOWED = {"desc", "desc_override", "tags", "contributors", "__v", "stats"}
PILOT = "63fe2c0cc538c16a825838ae"


def call(method, app_id, body=None):
    req = urllib.request.Request(API + app_id, method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"null")


apps = [a for a in json.load(open(M / "apps_full.json"))["apps"] if not a.get("projects")]
editable = {l.split()[0] for l in open(M / "editable.txt")}
ids_file = sys.argv[sys.argv.index("--ids") + 1] if "--ids" in sys.argv else None
wanted = set(open(ids_file).read().split()) if ids_file else None
if wanted is not None:
    mine = [a for a in apps if a["_id"] in wanted]
else:
    mine = [a for a in apps if a["github"].strip() in editable and a["_id"] != PILOT]
per_repo = collections.Counter(a["github"].strip() for a in apps)
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else len(mine)
log_path = M / ("bl_sync_ext_log.jsonl" if wanted is not None else "bl_sync_log.jsonl")
done = {json.loads(l)["id"] for l in open(log_path)} if log_path.exists() else set()
(M / "bl_before").mkdir(exist_ok=True)
(M / "bl_after").mkdir(exist_ok=True)

n = 0
for a in mine:
    if a["_id"] in done:
        continue
    if n >= limit:
        break
    i = a["_id"]
    before = call("GET", i)
    (M / "bl_before" / f"{i}.json").write_text(json.dumps(before))
    enriched = M / "enriched" / f"{i}.json"
    body = {}
    if wanted is not None:
        summary = json.loads(enriched.read_text())["summary"]
        if summary == "unknown":
            continue
        body = {"desc_override": summary}
    elif enriched.exists():
        summary = json.loads(enriched.read_text())["summary"]
        if per_repo[a["github"].strip()] > 1 and summary != "unknown":
            body = {"desc_override": summary}
        elif (before.get("desc_override") or "").strip():
            body = {"desc_override": None}
    try:
        call("PUT", i, body)
    except urllib.error.HTTPError as e:
        # e.g. the GitHub repo was deleted, so brainlife cannot refresh it; nothing was saved
        with open(log_path, "a") as f:
            f.write(json.dumps({"id": i, "name": a["name"], "body": body, "error": f"{e.code} {e.read()[:200]!r}", "ok": True}) + "\n")
        print(f"     SKIP {a['name'][:60]} (HTTP {e.code})", flush=True)
        n += 1
        continue
    after = call("GET", i)
    (M / "bl_after" / f"{i}.json").write_text(json.dumps(after))
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    bad = [k for k in changed if k not in ALLOWED]
    if "stats" in changed:
        sb, sa = dict(before.get("stats") or {}), dict(after.get("stats") or {})
        sb.pop("stars", None); sa.pop("stars", None)
        if sb != sa:
            bad.append("stats(other than stars)")
    entry = {"id": i, "name": a["name"], "body": body, "changed": changed,
             "override_before": before.get("desc_override"), "ok": not bad}
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    n += 1
    print(f"{len(done) + n:4d} {'OK ' if not bad else 'BAD'} {a['name'][:60]} {changed}", flush=True)
    if bad:
        print("STOP: run-time fields changed:", bad, flush=True)
        sys.exit(1)
    time.sleep(0.5)
print("finished", n, "Apps this run", flush=True)
