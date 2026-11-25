# Datatype Catalog, Plan 1: catalog, tool, records and reviewed sync

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reviewed catalog of all brainlife.io datatypes in `datatypes/`, with a tool that drafts records, maps them to BIDS, renders compact readmes, and writes existing fields to brainlife.io with size limits, drift checks and an undo log.

**Architecture:** One JSON record per datatype, validated by a JSON Schema. Small single-purpose modules in `tools/` (record I/O, BIDS projection, readme rendering, API sync) behind one CLI, `tools/bldt.py`, mirroring `tools/blapp.py`. Mechanical fields are drafted by code; judgement fields (descriptions, intended use, governance) are written in agent sessions following a new skill, then reviewed in the PR.

**Tech Stack:** Python 3.12 standard library + `jsonschema`, `pytest` (the only CI dependencies today, `.github/workflows/test.yml`).

**Spec:** `docs/superpowers/specs/2026-11-25-datatype-catalog-design.md`

Later plans (not here): Plan 2 warehouse-next and brainlife-lite proposals (structured fields, `avatar`, icon fallback, readme `select`); Plan 3 consumers read generated artifacts (bl2bids, aimport, bids_walker, Node walker test); Plan 4 weekly BIDS Action and the `bids-to-brainlife-sync` skill.

## Global Constraints

- Records are JSON at `datatypes/<slug>.json`; drafts at `datatypes/drafts/<slug>.json`. Slug: datatype name with `/` replaced by `.` and spaces by `_` (`neuro/anat/t1w` -> `neuro.anat.t1w`, `zarr v3` -> `zarr_v3`).
- `desc` at most 200 characters. Generated `readme` at most 2048 bytes (UTF-8). Each `files[].desc` one sentence.
- An existing readme longer than 2048 bytes is kept unchanged, never grown.
- `push` refuses, unless `--approve-size` is given, a run that grows the total size of all records on brainlife.io by more than 25%, or any record past 4096 bytes (size = `len(json.dumps(record, separators=(",", ":")))` of the record as returned by the API).
- Never change `_id`, `name`, `validator`, `validator_branch`, `datatype_tags`, or an existing file's `id`, `filename`, `dirname`, `required`. New file entries are always `required: false`.
- Existing `bids.maps` entries are kept as they are (including `_id`); new maps are only appended. `bids.derivatives` is set only when it is empty.
- `match` is one of `equivalent`, `partial`, `none`; `none` produces no maps.
- Sidecar status is one of `file`, `meta`, `missing`.
- Governance `default_tier` is an integer 1-5 (toolkit `~/git/braindatagovernance/data/tiers.yml`); when uncertain, the higher (more protective) tier.
- BIDS reference: bids 1.11.2, schema 2.0.0 (`https://bids-specification.readthedocs.io/en/stable/schema.json`); each record stores the version it was checked against.
- Nothing is written to brainlife.io by tests or by `draft`; only `push` and `undo` write, and only with a token at `~/.config/brainlife.io/.jwt` (from `bl login`).

## Review Focus

1. Datatype names with spaces or unusual characters (`zarr v3`, `test2`) must slug and load back to the same name.
2. A field edited on brainlife.io after `pull` must be skipped by `push` and reported, not overwritten.
3. A datatype whose existing readme is over 2048 bytes must keep its readme byte-for-byte.
4. A datatype that already has `bids.maps` must keep every existing map (with its `_id`) in order, new ones after.
5. A `push` interrupted part-way must leave an undo log that restores every record already written.

---

### Task 1: Record schema and record I/O

**Files:**
- Create: `schema/datatype-record-1.0.schema.json`
- Create: `tools/dtrecord.py`
- Test: `tests/test_dtrecord.py`, fixture `tests/fixtures/dt-neuro.dwi.json` (a complete valid record for `neuro/dwi`, `_id` `58c33c5fe13a50849b25879b`)

**Interfaces:**
- Produces:
  - `slug(name: str) -> str`
  - `load(path) -> dict`, `save(path, record: dict) -> None` (2-space indent, sorted keys, trailing newline)
  - `validate(record: dict) -> list[str]` (error messages; empty when valid)
  - `record_size(api_record: dict) -> int`
  - `load_all(root) -> dict[str, dict]` keyed by datatype name (both `datatypes/` and `datatypes/drafts/`)

Record shape (top-level keys, all required unless noted):
`spec` ("brainlife-datatype-record/1.0"), `brainlife` {`_id` (absent for drafts), `name`, `desc`, `readme`, `original` {`desc`, `readme`}}, `files` [{`id`, `filename`|`dirname`, `desc`, `required`, `proposed` (optional bool)}], `usage` {`inputs_of` [{`app_id`, `name`, `purpose`}], `outputs_of` [same], `intended_use` [str], `not_suitable_for` [str]}, `bids` {`correspondences` [{`datatype`, `suffix`, `extensions` [str], `entities` [str], `level` ("raw"|"derivative"), `match`, `files` [{`file_id`, `bids_part`, `sidecar` ("file"|"meta"|"missing", optional), `meta_fields` [str] (optional)}], `tags` [str], `notes`}], `checked_against` {`bids_version`, `schema_version`}}, `governance` {`human_neurodata` ("yes"|"no"|"depends"), `default_tier` (1-5), `tier_conditions` [str], `information_kinds` [enum: anatomy, function, behaviour, physiology, identity, health_status, demographics, none], `identifying_risks` [str], `sharing_cautions` [str], `rationale` (str)}, `provenance` {`drafted_by`, `sources` [str], `todo` [str] (field paths still to fill)}.

- [ ] **Step 1: Write the failing tests**

```python
def test_slug_round_trips_unusual_names():
    assert dtrecord.slug("neuro/anat/t1w") == "neuro.anat.t1w"
    assert dtrecord.slug("zarr v3") == "zarr_v3"

def test_fixture_record_is_valid():
    assert dtrecord.validate(dtrecord.load(FIX / "dt-neuro.dwi.json")) == []

def test_desc_over_200_chars_is_rejected():
    r = dtrecord.load(FIX / "dt-neuro.dwi.json"); r["brainlife"]["desc"] = "x" * 201
    assert any("desc" in e for e in dtrecord.validate(r))

def test_tier_outside_1_to_5_is_rejected():
    r = dtrecord.load(FIX / "dt-neuro.dwi.json"); r["governance"]["default_tier"] = 6
    assert dtrecord.validate(r)

def test_record_size_uses_compact_json():
    assert dtrecord.record_size({"a": 1}) == len('{"a":1}')

def test_save_then_load_is_identical(tmp_path):
    r = dtrecord.load(FIX / "dt-neuro.dwi.json"); dtrecord.save(tmp_path / "x.json", r)
    assert dtrecord.load(tmp_path / "x.json") == r
```

- [ ] **Step 2: Run** `pytest -q tests/test_dtrecord.py` — Expected: FAIL (module missing).
- [ ] **Step 3: Write the schema and `tools/dtrecord.py`.** The 2048-byte readme limit is checked in `validate()` (byte length), except when `readme == original.readme` (kept unchanged).
- [ ] **Step 4: Run** `pytest -q tests/test_dtrecord.py` — Expected: PASS.
- [ ] **Step 5: Commit** `git add schema/datatype-record-1.0.schema.json tools/dtrecord.py tests/test_dtrecord.py tests/fixtures/dt-neuro.dwi.json && git commit -m "Datatype record schema and I/O"`

### Task 2: BIDS index and projections

**Files:**
- Create: `tools/dtbids.py`
- Test: `tests/test_dtbids.py`, fixture `tests/fixtures/bids-schema-mini.json` (the real schema.json cut to `objects.datatypes`, `objects.suffixes`, `objects.extensions`, `rules.files.raw.anat`, `rules.files.raw.dwi`, `rules.sidecars` entries for T1w and dwi, plus `schema_version`, `bids_version`)

**Interfaces:**
- Consumes: `dtrecord.load`
- Produces:
  - `bids_index(schema: dict) -> dict[tuple[str, str], dict]` — (datatype, suffix) -> `{"extensions": [...], "entities": [...], "level": "raw"}`; derivatives keyed the same with `level: "derivative"`
  - `project_maps(record: dict, live_bids: dict | None) -> dict` — the `bids` object to write: existing `live_bids["maps"]` unchanged and in order, then one map per correspondence file not already present by `src`; correspondences with `match: "none"` contribute nothing; a sidecar with status `meta` becomes `{"src": "_meta_", "dest": "<suffix>.json"}`; `derivatives` = live value if set, else the first correspondence's BIDS datatype
  - `aimport_rows(records: dict[str, dict]) -> list[dict]` — rows in the shape of ezbids `bids_brainlife_map.yaml` `mappings` (`bids: {datatype, suffix}`, `brainlife: {datatype, tags}`, `status`), `status` = `active` for records with `_id`, `draft` otherwise; only `equivalent`/`partial` correspondences
  - `unmapped(index, records) -> list[tuple[str, str]]` — BIDS (datatype, suffix) pairs with no correspondence in any record

- [ ] **Step 1: Write the failing tests**

```python
def test_index_has_t1w_and_dwi():
    idx = dtbids.bids_index(MINI)
    assert idx[("anat", "T1w")]["level"] == "raw"
    assert ".nii.gz" in idx[("dwi", "dwi")]["extensions"]

def test_existing_maps_kept_in_order_new_ones_appended():
    live = {"derivatives": "dwi", "maps": [{"_id": "m1", "src": "dwi.nii.gz", "dest": "dwi.nii.gz"}]}
    out = dtbids.project_maps(DWI_RECORD, live)
    assert out["maps"][0] == live["maps"][0]
    assert [m["src"] for m in out["maps"]].count("dwi.nii.gz") == 1
    assert out["derivatives"] == "dwi"

def test_meta_sidecar_becomes_meta_map():
    out = dtbids.project_maps(DWI_RECORD, None)
    assert {"src": "_meta_", "dest": "dwi.json"} in out["maps"]

def test_match_none_produces_no_maps():
    r = copy.deepcopy(DWI_RECORD); r["bids"]["correspondences"][0]["match"] = "none"
    assert dtbids.project_maps(r, None)["maps"] == []

def test_aimport_rows_mark_drafts():
    rows = dtbids.aimport_rows({"neuro/dwi": DWI_RECORD, "neuro/anat/angio": ANGIO_DRAFT})
    assert {r["status"] for r in rows} == {"active", "draft"}
```

- [ ] **Step 2: Run** `pytest -q tests/test_dtbids.py` — Expected: FAIL.
- [ ] **Step 3: Implement `tools/dtbids.py`.** Read raw file rules from `rules.files.raw.<group>.<rule>` (`datatypes`, `suffixes`, `extensions`, `entities`) and derivative rules from `rules.files.deriv`.
- [ ] **Step 4: Run** `pytest -q tests/test_dtbids.py` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "BIDS index and bids.maps / aimport projections"`

### Task 3: Compact readme rendering

**Files:**
- Create: `tools/dtreadme.py`
- Test: `tests/test_dtreadme.py`

**Interfaces:**
- Consumes: record shape from Task 1
- Produces: `render(record: dict, catalog_url: str) -> str`

Sections, in order, each omitted when empty: what it is (`desc`), files (one line each), used by (App names, inputs then outputs, at most 8 each then "and N more"), BIDS (one line per correspondence: `anat/T1w — equivalent`), sharing (tier name and the first two `sharing_cautions`), then `Full record: <catalog_url>`. If `original.readme` is non-empty, it comes first under its own text, and the generated part is appended only if the total stays within 2048 bytes; otherwise the original is returned unchanged.

- [ ] **Step 1: Write the failing tests**

```python
def test_render_fits_budget_and_links_catalog():
    md = dtreadme.render(DWI_RECORD, "https://github.com/brainlife/abcd-spec/blob/master/datatypes/neuro.dwi.json")
    assert len(md.encode()) <= 2048
    assert md.rstrip().endswith("datatypes/neuro.dwi.json")

def test_long_original_readme_is_kept_byte_for_byte():
    r = copy.deepcopy(DWI_RECORD); r["brainlife"]["original"]["readme"] = "é" * 1500
    assert dtreadme.render(r, "u") == "é" * 1500

def test_many_apps_are_truncated():
    r = copy.deepcopy(DWI_RECORD)
    r["usage"]["inputs_of"] = [{"app_id": str(i), "name": f"App {i}", "purpose": "p"} for i in range(30)]
    assert "and 22 more" in dtreadme.render(r, "u")
```

- [ ] **Step 2: Run** `pytest -q tests/test_dtreadme.py` — Expected: FAIL.
- [ ] **Step 3: Implement `tools/dtreadme.py`.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Compact datatype readme renderer"`

### Task 4: `bldt.py pull`, `bids` and `draft`

**Files:**
- Create: `tools/bldt.py`
- Test: `tests/test_bldt_draft.py`, fixtures `tests/fixtures/dt-api-snapshot.json` (three datatypes from `GET /api/warehouse/datatype?limit=0`: `neuro/dwi`, `neuro/anat/t1w`, `zarr v3`); aimport rows are given inline in the test as a list of three dicts

**Interfaces:**
- Consumes: `dtrecord.*`, `dtbids.bids_index`, `catalog/index.json` (App inputs/outputs by datatype name)
- Produces:
  - `pull(api: str, out: Path) -> Path` — writes `snapshots/<UTC date>/datatypes.json`; `api` default `https://brainlife.io/api/warehouse`
  - `draft(snapshot: dict, bids_schema: dict, app_index: dict, aimport_rows: list[dict], existing: dict[str, dict]) -> dict[str, dict]` — one record per datatype; keeps every non-TODO value already in `existing`; fills `brainlife` (`_id`, `name`, `original` from the live record, `desc`/`readme` copied from original when empty), `files` (live entries, desc copied), `usage.inputs_of`/`outputs_of` (from the App index, `purpose` TODO), `bids.correspondences` (from live `bids.maps` and aimport rows; `match` TODO when not derivable), `checked_against`; lists every unfilled judgement field in `provenance.todo`
  - `import_drafts(dir: Path) -> dict[str, dict]` — converts ezbids `aimport/src/aimport/data/datatype_drafts/*.json` to draft records (no `_id`)
  - CLI: `bldt.py pull`, `bldt.py bids [--version stable]` (saves `snapshots/bids-schema-<version>.json`), `bldt.py draft --snapshot ... --bids ... --aimport <path to bids_brainlife_map.yaml converted with a one-off script, or JSON>`, `bldt.py import-drafts <dir>`
  - `snapshots/` is git-ignored.

- [ ] **Step 1: Write the failing tests**

```python
def test_draft_keeps_reviewed_values():
    existing = {"neuro/dwi": DWI_RECORD}
    out = bldt.draft(SNAP, MINI, APP_INDEX, ROWS, existing)
    assert out["neuro/dwi"]["brainlife"]["desc"] == DWI_RECORD["brainlife"]["desc"]

def test_draft_marks_judgement_fields_todo():
    out = bldt.draft(SNAP, MINI, APP_INDEX, ROWS, {})
    assert "governance.default_tier" in out["neuro/anat/t1w"]["provenance"]["todo"]

def test_draft_lists_apps_from_catalog_index():
    out = bldt.draft(SNAP, MINI, APP_INDEX, ROWS, {})
    assert any(a["name"] == "Freesurfer 7.3.2" for a in out["neuro/anat/t1w"]["usage"]["inputs_of"])

def test_draft_handles_name_with_space():
    out = bldt.draft(SNAP, MINI, APP_INDEX, ROWS, {})
    assert "zarr v3" in out and dtrecord.slug("zarr v3") == "zarr_v3"

def test_import_drafts_have_no_id(tmp_path):
    (tmp_path / "neuro.anat.angio.json").write_text(json.dumps(ANGIO_AIMPORT_DRAFT))
    d = bldt.import_drafts(tmp_path)["neuro/anat/angio"]
    assert "_id" not in d["brainlife"] and d["files"][0]["required"] is False
```

`validate()` must accept records whose TODO fields hold the placeholder; use `"TODO"` for strings and `0` for `default_tier`, and have `validate()` skip the 1-5 check only when `"governance.default_tier"` is in `provenance.todo`.

- [ ] **Step 2: Run** `pytest -q tests/test_bldt_draft.py` — Expected: FAIL.
- [ ] **Step 3: Implement** (urllib for HTTP; no new dependencies). The aimport YAML is read without PyYAML by having `bldt.py draft --aimport` accept a JSON file; add `tools/yaml2json.md` one-liner instructions (`python3 -c 'import yaml,json,sys;...'` run once locally, where PyYAML exists).
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "bldt pull/bids/draft/import-drafts"`

### Task 5: `diff`, `push`, `undo`

**Files:**
- Modify: `tools/bldt.py`
- Create: `tools/dtsync.py`
- Test: `tests/test_dtsync.py`

**Interfaces:**
- Consumes: `dtrecord.record_size`, `dtbids.project_maps`, `dtreadme.render`
- Produces:
  - `desired(record: dict, live: dict, catalog_url: str) -> dict` — the PUT body: only `desc`, `readme`, `files`, `bids`; `files` = live entries with `desc` updated, plus `proposed` entries appended with `required: False` (and `proposed` key removed)
  - `plan(records, live_now, live_at_pull) -> list[Change]` where `Change = {"name", "_id" | None, "method": "PUT"|"POST", "body", "skipped": [field], "size_before", "size_after"}`; a field whose `live_now` value differs from `live_at_pull` goes to `skipped` and out of `body`
  - `check_budget(changes, approve_size: bool) -> list[str]` — errors per the Global Constraints limits
  - `push(changes, http, undo_path) -> None` — for each change: append `{"_id", "before": live_now record}` to the undo log file and flush, then send; POST bodies (drafts) include `name`, `desc`, `readme`, `files`, `bids`, `datatype_tags: []`, `admins` (from `--admins`); the new `_id` is written back into the record file and the record moves from `datatypes/drafts/` to `datatypes/`
  - `undo(undo_path, http) -> None` — PUT each `before` back (`desc`, `readme`, `files`, `bids` only); for created datatypes, DELETE only if `GET /dataset?find={"datatype": id}&limit=1` and the App index show no use, else report and keep
  - `http` is an injected object with `get(path)`, `put(path, body)`, `post(path, body)`, `delete(path)`; the CLI builds it from the token in `~/.config/brainlife.io/.jwt` and exits with a message telling the user to run `bl login` if it is missing or expired
  - CLI: `bldt.py diff`, `bldt.py push [--only NAME ...] [--approve-size] [--admins SUB,...]`, `bldt.py undo <undo.json>`; undo logs at `docs/backfill/datatypes/<UTC timestamp>-undo.json`

- [ ] **Step 1: Write the failing tests**

```python
def test_drifted_field_is_skipped():
    at_pull = {"_id": "1", "desc": "old", "readme": "", "files": [], "bids": None}
    now = dict(at_pull, desc="edited by an admin")
    ch = dtsync.plan({"x": REC}, {"x": now}, {"x": at_pull})[0]
    assert "desc" in ch["skipped"] and "desc" not in ch["body"]

def test_never_touches_protected_fields():
    body = dtsync.desired(REC, LIVE, "u")
    assert set(body) <= {"desc", "readme", "files", "bids"}
    for old, new in zip(LIVE["files"], body["files"]):
        assert {k: old.get(k) for k in ("id", "filename", "dirname", "required")} == {k: new.get(k) for k in ("id", "filename", "dirname", "required")}

def test_budget_blocks_large_record():
    big = [{"name": "x", "size_before": 1000, "size_after": 5000}]
    assert dtsync.check_budget(big, approve_size=False)
    assert dtsync.check_budget(big, approve_size=True) == []

def test_undo_log_written_before_each_send(tmp_path):
    http = FailingOnSecondPut()
    with pytest.raises(RuntimeError):
        dtsync.push(TWO_CHANGES, http, tmp_path / "undo.json")
    assert len(json.loads((tmp_path / "undo.json").read_text())) == 2

def test_undo_restores_before_values(tmp_path):
    http = RecordingHttp(); dtsync.undo(UNDO_FIXTURE, http)
    assert http.puts[0][1]["desc"] == "old"
```

- [ ] **Step 2: Run** `pytest -q tests/test_dtsync.py` — Expected: FAIL.
- [ ] **Step 3: Implement `tools/dtsync.py` and the CLI commands.** Undo log is a JSON list rewritten in full after each append (small files).
- [ ] **Step 4: Run** `pytest -q tests` — Expected: all PASS.
- [ ] **Step 5: Commit** `git commit -m "bldt diff/push/undo with drift check, size budget and undo log"`

### Task 6: Skill, the 140 records, aimport drafts and findings

**Files:**
- Create: `skills/brainlife-datatype-metadata/SKILL.md` (how to read a datatype and its Apps, infer what it is, choose `match` and sidecar status, assign governance from the toolkit tiers with `tier_conditions`, write compact text within the limits; worked example `neuro/anat/t1w`)
- Create: `datatypes/*.json` (all 140), `datatypes/drafts/*.json` (from aimport's 139 drafts, deduplicated against existing names)
- Modify: `schema/datatypes.json` — regenerate from records (`bldt.py generate`, add to `tools/bldt.py`: writes `schema/datatypes.json` as `[{"id", "name"}]` sorted by name, unchanged format so `blapp.py` keeps working)
- Create: `docs/backfill/2026-11-25-datatype-candidates.md` — candidate new datatypes for Franco's review, nothing created: one row per draft and per `dtbids.unmapped` pair (BIDS datatype/suffix, proposed brainlife name, files, sidecars, default tier, which existing datatype it is closest to, recommendation create / merge into existing / skip, and why)
- Create: `docs/backfill/2026-11-25-datatype-findings.md` (counts by `match`, sidecars `missing`, tiers, test/orphan datatypes such as `test2` and `zarr v3`, datatypes with no App use, BIDS pairs with no brainlife datatype from `dtbids.unmapped`)
- Test: `tests/test_datatype_records.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_every_record_is_valid_and_complete():
    recs = dtrecord.load_all(ROOT / "datatypes")
    for name, r in recs.items():
        assert dtrecord.validate(r) == [], name
        if "_id" in r["brainlife"]:
            assert r["provenance"]["todo"] == [], name

def test_schema_datatypes_json_matches_records():
    ids = {r["brainlife"]["_id"]: n for n, r in dtrecord.load_all(ROOT / "datatypes").items() if "_id" in r["brainlife"]}
    assert {d["id"]: d["name"] for d in json.loads((ROOT / "schema/datatypes.json").read_text())} == ids

def test_rendered_readmes_fit_budget():
    for n, r in dtrecord.load_all(ROOT / "datatypes").items():
        md = dtreadme.render(r, "u")
        assert len(md.encode()) <= 2048 or md == r["brainlife"]["original"]["readme"], n
```

- [ ] **Step 2: Run** `pytest -q tests/test_datatype_records.py` — Expected: FAIL (no records).
- [ ] **Step 3: Write the skill.**
- [ ] **Step 4: Draft mechanically:** `python tools/bldt.py pull && python tools/bldt.py bids && python tools/bldt.py draft ... && python tools/bldt.py import-drafts ~/git/brainlife/ezbids/aimport/src/aimport/data/datatype_drafts`.
- [ ] **Step 5: Fill judgement fields** for all 140 records following the skill (batches by prefix: `neuro/anat`, `neuro/dwi*`, `neuro/func*`, ephys, derivatives, generic/other). Read each datatype's Apps' manifests in `catalog/apps/` for purposes.
- [ ] **Step 6: Run** `python tools/bldt.py generate && pytest -q tests` — Expected: all PASS.
- [ ] **Step 7: Run** `python tools/bldt.py diff > docs/backfill/2026-11-25-datatype-diff.txt` (read-only; needs no token) and write the findings report, including total size before/after.
- [ ] **Step 8: Commit and open PR** to `brainlife/abcd-spec`. The PR description documents the strategy and plan: the problem and goals, the approach chosen and the alternatives rejected, where knowledge lives now and after (the five-location table), the BIDS mapping model, the governance model and its source, the size budget, the safety rules for writes, the plan sequence (Plans 1-4) with links to the spec and this plan, the findings summary, the candidate-datatype list for review, and what happens after merge. Do not run `push`.

### Task 7: Write to brainlife.io (after Franco merges)

- [ ] **Step 1:** Franco runs `bl login` in a real terminal (token at `~/.config/brainlife.io/.jwt`).
- [ ] **Step 2: Pilot:** `python tools/bldt.py push --only neuro/dwi --only neuro/anat/t1w`; check both pages on brainlife.io and brainlife-lite; Franco confirms.
- [ ] **Step 3: Full run:** `python tools/bldt.py push`; then `pull` again and confirm `diff` is empty except reported skips.
- Creating new datatypes is deferred (Franco, 2026-11-25): only after Franco reviews `datatype-candidates.md`. `push --drafts` stays implemented but is not run in this plan.
- [ ] **Step 4: Commit** the undo logs under `docs/backfill/datatypes/`.
