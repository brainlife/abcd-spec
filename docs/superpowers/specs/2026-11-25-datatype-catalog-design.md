# brainlife.io datatype catalog: documentation, BIDS mapping and governance

Date: 2026-11-25. Owner: Franco Pestilli. Status: design, approved approach A.

## Why

Many of the 140 datatypes on brainlife.io do not say what they are, what files they hold, or how
they may be used: 47 have a description under 40 characters and about half have no readme.
Only 15 have a BIDS export mapping. The knowledge that connects brainlife datatypes to BIDS is
spread across five places that disagree (see Current state). Franco wants:

1. Every datatype documented: what it is, its files and fields, how it can and cannot be used,
   and which Apps consume or produce it and for what.
2. Every datatype mapped to BIDS (datatype, suffix, other parts of the spec), recording whether
   it is equivalent, partial or has no counterpart.
3. Going from brainlife to BIDS (and back) to be easy and smooth, driven by data rather than
   hand-written per-datatype code.
4. Governance metadata on each datatype: whether it can hold private or identifying information,
   how risky it is to share, and what kind of information it carries, following the Global Brain
   Governance toolkit (braindatagovernance.org; local repo `~/git/braindatagovernance`).
5. A routine system so that new BIDS datatypes and suffixes appear on brainlife.io, available to
   Apps, after review.
6. Skills so this work can be repeated by agents and people.

## Goals, non-goals, anti-goals

Goals
- One canonical, reviewed catalog for datatype knowledge, in this repo under `datatypes/`.
- Enriched records on brainlife.io written from the catalog, using fields that already exist.
- A bidirectional BIDS mapping that the existing consumers read instead of carrying copies.
- Proposals (PRs) to warehouse-next for structured fields, and to brainlife-lite to show them.

Non-goals
- Rewriting the BIDS export in warehouse-next or the import in aimport. They keep working; they
  read better data.
- Changing an App's inputs, outputs or code.
- Assigning a governance tier to a specific dataset. The toolkit tiers data objects; a datatype can
  only carry a default and the conditions that change it.

Anti-goals (a failure even if it technically works)
- Breaking any existing datatype, data object, App or BIDS export on brainlife.io. No field is
  renamed, removed, or made required; no file entry is made required; datatype ids and names do
  not change.
- Writing to brainlife.io without review. Nothing is written until Franco merges the PR that
  contains the change.
- A new, sixth copy of the mapping. Every copy that remains must be generated from, or checked
  against, the catalog.
- Presenting a governance default as a legal determination. It is guidance; the toolkit's Tool 1
  assessment of the actual data governs.

## Current state

Datatype schema (warehouse-next `api/models.js` `datatypeSchema`): `name`, `desc`, `readme`
(markdown), `admins`, `files[]` (`id`, `filename` or `dirname`, `desc`, `ext`, `required`),
`datatype_tags[]` (`datatype_tag`, `desc`), `_datatype_tags[]`, `validator`, `validator_branch`,
`bids` (`derivatives`, `maps[]` of `src`, `dest`, `json`), `uis[]`, `samples[]`, `groupAnalysis`,
`create_date`. Twelve records also carry a `meta` array that is not in the schema.

`PUT /api/warehouse/datatype/:id` (datatype admins or warehouse admins) copies every body key
onto the document and saves. Mongoose strict mode silently drops keys not in the schema, so new
fields need a schema change before they can be stored.

BIDS export (warehouse-next `api/controllers/dataset.js` around line 2680) builds a shell script
from `bids.maps`: each `src` file is symlinked to `<entities>_<dest>`; `src: "_meta_"` writes the
data object's `meta` as the JSON sidecar. Datatypes without maps export nothing ("#no bids
mapping").

Where BIDS <-> brainlife knowledge lives today:

| Location | Direction | Content |
|---|---|---|
| ezbids `aimport/src/aimport/data/bids_brainlife_map.yaml` (769 lines, BIDS 1.11.2) + `datatype_drafts/` (139 drafts) + `tools/draft_datatypes.py` | BIDS -> brainlife | (datatype, suffix) -> brainlife datatype and tags, status active/planned/draft; drafts generated from the BIDS schema |
| pybrainlife / cli `aimport/bids_walker.py` | BIDS -> brainlife | uploader's copy of the table |
| abcd-spec `hooks/bl2bids.py` + `hooks/utils.py` | brainlife -> BIDS | hard-coded rules for t1w, t2w, dwi, func/task, regressors, fmap, meg ctf/fif, eeg eeglab/edf/brainvision/bdf; installed in amaretti's runner image |
| warehouse-next DB `datatype.bids.maps` | brainlife -> BIDS | export rules, 15 datatypes |
| brainlife.io datatype records | - | descriptions, files, readmes |

BIDS publishes a machine-readable schema (`https://bids-specification.readthedocs.io/en/stable/schema.json`;
schema 2.0.0, BIDS 1.11.2 at time of writing): 16 datatypes, 118 suffixes, 35 entities,
45 extensions, file rules for raw data and derivatives, and sidecar metadata rules.

Sidecars: brainlife often keeps BIDS sidecar content as fields in each data object's `meta`
rather than as a file. When `meta` carries enough to rebuild the sidecar, the sidecar is not
dropped and nothing needs to change.

## Approaches considered

A. Reviewed catalog in a repository, synced to brainlife.io. **Chosen.** Files in git hold the
   knowledge; a tool drafts them from brainlife.io, the BIDS schema and App usage; review happens
   in PRs; the tool writes existing fields to brainlife.io after merge; a scheduled job drafts new
   BIDS additions as a PR.
B. Everything in the database with a server-side sync job in warehouse-next. Fastest for new BIDS
   types, but no review, every change needs a deploy, and a sync bug writes straight to production.
C. Hand-written readmes only. Cheapest, but gives no machine-usable mapping, so brainlife -> BIDS
   stays manual. Does not meet goal 3.

Location: abcd-spec (chosen) rather than a new `brainlife/datatypes` repo. abcd-spec is the spec
repo, already ships `bl2bids` (installed into amaretti's runner), and holds the App catalog
(`catalog/apps`, PRs #41/#42), so App <-> datatype links stay in one repo. A separate repo would
be cleaner to version but adds a repo to maintain.

## Design

### 1. Catalog (`datatypes/` in abcd-spec)

One file per brainlife datatype, `datatypes/<name with / replaced by .>.yaml`, keyed by the
brainlife `_id` and `name`, plus `datatypes/drafts/` for proposed datatypes that do not exist on
brainlife.io yet (moved from aimport's `datatype_drafts/`). A JSON Schema in `schema/` validates
every file. Sections of a record:

- `brainlife`: `_id`, `name`, and the enriched `desc` (one or two sentences) and `readme` that are
  written to brainlife.io.
- `files`: the datatype's file entries as on brainlife.io, each with an improved `desc`. Proposed
  additions (optional sidecars, see 4) are marked `proposed: true` until written.
- `usage`: Apps that take it as input and produce it as output (from the App catalog and the
  brainlife API), each with a short purpose; and `intended_use` / `not_suitable_for` lists.
- `bids`: the mapping (see 2).
- `governance`: defaults (see 3).
- `provenance`: who or what drafted each section, from which sources, and the BIDS version.

Readmes are generated from the record (a template renders files, usage, BIDS mapping and
governance into markdown), so the readme on brainlife.io never drifts from the structured data.

### 2. BIDS mapping

Per datatype, a list of correspondences, each with:
- `bids`: `datatype` (anat, dwi, func, ...), `suffix`, `extensions`, `entities` that must or may
  be present, `level` (`raw` or `derivative`, with the derivative's location if any).
- `match`: `equivalent` (same content and files), `partial` (a subset, a superset, bundles several
  suffixes, or needs tags to disambiguate), or `none` (no BIDS counterpart; for example many
  derivatives such as tract measures or white-matter classifications).
- `files`: per-file mapping from brainlife file id to BIDS filename part; sidecars recorded as
  `file` (carried as a file), `meta` (rebuildable from data object `meta`, listing the fields
  needed), or `missing` (cannot be rebuilt; triggers a proposal, see 4).
- `tags`: brainlife datatype tags that select this correspondence (for example a task name).
- `notes` and `checked_against`: BIDS version and schema version.

From this one structure the tool generates both directions: the `bids.maps` for warehouse's
export and the BIDS -> brainlife table for aimport and the uploader (replacing
`bids_brainlife_map.yaml` as a generated artifact with the same shape, so its readers keep
working).

### 3. Governance defaults (Global Brain Governance toolkit)

Per datatype:
- `human_neurodata`: yes / no / depends (Tool 1, step 1).
- `default_tier`: 1-5 per the toolkit (`data/tiers.yml`): 1 aggregated; 2 pseudonymised
  participant-level; 3 directly identifiable or intrinsically traceable (for example non-defaced
  anatomy, identifying headers); 4 functionally revealing derivatives (fingerprints, embeddings,
  predictions, profiles); 5 model-associated.
- `tier_conditions`: what moves an object up or down (for example `neuro/anat/t1w`: tier 3 unless
  defaced, then tier 2; connectivity matrices: tier 2, tier 4 when used as a fingerprint).
- `information_kinds`: what the data can reveal (anatomy, function, behaviour, physiology,
  identity, health status, demographics) — the "value" of the information it holds.
- `identifying_risks`: concrete risks (face in the image, DICOM headers, timestamps, device
  serials, free-text fields in `meta`).
- `sharing_cautions`: what to check before sharing, phrased as the toolkit's required actions.
- `rationale`: one short paragraph citing the toolkit step(s) used.

Uncertain cases default to the more protective tier, as the toolkit requires.

### 4. Changes to datatypes on brainlife.io (existing fields only)

Written by the sync tool after the PR is merged, per datatype: `desc`, `readme`, `files[].desc`,
`bids.maps` / `bids.derivatives`, and new optional file entries. Rules:
- Never change `_id`, `name`, `validator`, existing file `id`/`filename`/`dirname`/`required`, or
  `datatype_tags` semantics.
- Add a sidecar file entry (`required: false`) only when the BIDS counterpart has a sidecar the
  brainlife datatype cannot carry and `meta` cannot rebuild. Before adding, confirm the datatype's
  validator accepts unknown optional files.
- Every write is preceded by a snapshot of the current record into an undo log in the repo
  (`docs/backfill/datatypes/`), and the tool can restore from it.

### 4a. Size budget (Franco: keep datatypes small)

Datatype records travel a lot: brainlife-lite's project data queries populate the full datatype
into every data object row (`src/hooks/datasetQueries.ts`, `populate: {path: 'datatype'}` with no
`select`), and the datatype list loads all records. Today all 140 records are 256 KB (median
1.3 KB, largest 11.7 KB, readmes 54 KB in total). Rules:
- The rich material (App usage detail, full BIDS correspondence, governance rationale, sources)
  stays in the catalog in abcd-spec. The record on brainlife.io gets compact text and a link to
  its catalog page.
- `desc` at most 200 characters; generated `readme` at most 2 KB (longer existing readmes are
  kept, not grown); `files[].desc` one short sentence.
- Proposed structured fields are compact codes, not prose: for example
  `governance: {tier: 3, human: true, kinds: ["anatomy","identity"], conditions: ["defaced->2"]}`
  and `bids_mapping: [{dt: "anat", suffix: "T1w", match: "equivalent"}]`, a few hundred bytes.
- `push` reports the size of every record before and after, and refuses any write that grows the
  total by more than 25% or a record past 4 KB without explicit approval.
- The brainlife-lite proposal also adds a `select` to the datatype populate in data object
  queries (exclude `readme`), which shrinks those responses regardless of this work.

### 4b. Creating new datatypes (deferred; Franco, 2026-11-25)

Not now. First a reviewed list: `docs/backfill/2026-11-25-datatype-candidates.md` lists every BIDS
(datatype, suffix) with no brainlife datatype and every aimport draft, with a recommendation. After
Franco reviews it, the approved ones are registered as below.


After Franco merges a PR that contains drafts, `push` registers them with `POST /datatype`
(warehouse admins only). New datatypes: Franco's account and the existing brainlife admin
accounts as `admins`; no `validator` unless one exists for that BIDS datatype (then it is set
and its acceptance of the files is tested first); `bids.maps` from the catalog. The new `_id` is
written back into the catalog record, the draft moves from `datatypes/drafts/` to `datatypes/`,
and the generated aimport map flips that row from `draft` to `active`. Registration is
undoable only by deleting a datatype nothing uses yet; `undo` refuses once any data object or
App references it.

### 4c. Datatype icons

Datatypes have no icon today. Proposal: an optional `avatar` (URL) field on the datatype schema
(warehouse-next), and in brainlife-lite the existing `BrandAvatar` component with the brainlife
logo as fallback and a small datatype badge, the same pattern as Apps (gear, `Cog`) and
resources (`Cpu`). The badge is the `Shapes` icon the sidebar already uses for Datatypes.
Used on the Datatypes list, the datatype page header, and wherever an App's inputs and outputs
are drawn. The URL adds a few dozen bytes per record.

### 5. warehouse-next proposals (PRs, not merged without Franco)

Add optional schema fields so structured data can live on the record, not only in the readme:
`bids_mapping` (section 2), `governance` (section 3), `usage` summary, and `catalog` (source
commit). All optional, no defaults that change existing behaviour, no migration needed. Also
document the stray `meta` field and either add it to the schema or note it. A matching
brainlife-lite PR shows governance and BIDS mapping on the datatype page; both follow each repo's
AGENTS.md (re-read from origin before starting).

### 6. Consumers read the catalog

- `hooks/bl2bids.py`: replace hard-coded per-datatype rules with lookups in the generated
  mapping, keeping current behaviour for the datatypes it handles today (regression tests on
  `test/bl2bids`).
- ezbids aimport: `bids_brainlife_map.yaml` and `datatype_drafts/` become generated copies of
  the catalog, pinned to an abcd-spec commit; CI fails if they differ from the catalog.
- pybrainlife `bids_walker.py`: same pinned generated table.
- warehouse export: unchanged code; better `bids.maps` written by the sync.

### 7. Tool and routine sync

`tools/bldt.py` (mirrors `tools/blapp.py`): `pull` (snapshot brainlife.io datatypes and App
usage), `bids` (fetch a BIDS schema version), `draft` (fill or refresh catalog records), `diff`
(what would change on brainlife.io), `push` (write, with undo log; requires a token from
`bl login`, `~/.config/brainlife.io/.jwt`), `generate` (consumer artifacts), `undo`.

A scheduled GitHub Action runs weekly: fetch the latest BIDS schema; if its version is new, run
`draft` for added datatypes, suffixes or changed rules and open a PR. Nothing reaches brainlife.io
until the PR is merged and `push` is run (manually at first; automated later only if Franco asks).

### 8. Skills

`skills/brainlife-datatype-metadata` (how to read a datatype, find its Apps, infer what it is,
write the record and governance block) and `skills/bids-to-brainlife-sync` (how to review a BIDS
release PR and register new datatypes), alongside the existing `skills/brainlife-app-metadata`.

## Order of work

1. Catalog schema, `bldt.py pull/bids/draft`, and records for all 140 datatypes (drafted from the
   API, the BIDS schema, aimport's map and drafts, `bl2bids` rules and App usage). PR to abcd-spec
   with a findings report (match levels, missing sidecars, test and orphan datatypes such as
   `test2`, `zarr v3`).
2. Franco reviews; `push` writes existing fields to brainlife.io, with undo log.
3. warehouse-next and brainlife-lite proposal PRs (structured fields, `avatar`, datatype icon
   fallback, readme `select`), then registration of reviewed drafts.
4. Consumers switched to generated artifacts (bl2bids, aimport, bids_walker), each in its own PR.
5. Scheduled BIDS sync and skills.

## Decided by Franco

- Approach A; catalog in abcd-spec.
- Nothing breaks existing datatypes; new structure is added as optional fields via PR proposals.
- If sidecar information is kept in `meta` and the sidecar can be rebuilt, it is not dropped and
  the datatype is not changed; otherwise add an optional sidecar entry or propose what is missing.
- Governance follows the Global Brain Governance toolkit.
- Use Franco's admin account for writes to brainlife.io.
- Keep datatype records small (section 4a).
- New datatypes: first a candidate list for review; creation only after that review (section 4b).
- Datatypes without an icon show the brainlife logo with a small datatype badge (section 4c).

## Calls made after the builder check (Claude's, open to correction)

- Export (`bids.maps`): writing maps for datatypes that export nothing today, where the match is
  `equivalent` or `partial`, is an improvement, not a change to existing behaviour. The 15
  existing maps are only added to, never rewritten. `match: none` gets no maps. Maps aim to be as
  close to BIDS as the current export shape allows (everything under
  `bids/derivatives/<pipeline>/`, one `derivatives` directory per datatype, no tag-dependent maps,
  warehouse's own `_tag-`/`_desc-` entities). Valid BIDS raw output (raw vs derivative,
  tag-selected correspondences) needs export code changes and goes into the warehouse-next
  proposal PR, behind the existing behaviour.
- Hand-written text: existing `desc` and `readme` are kept in the record (`brainlife.original`)
  and folded into the generated readme, never discarded. `push` compares each live value with the
  last `pull`; if a field changed on brainlife.io since then it refuses that field and reports it.
- LLM use: the first 140 records are drafted in agent sessions using the skill. The weekly Action
  is mechanical only (BIDS schema, API, App catalog) and opens a PR whose judgement fields are
  marked TODO; an agent session or a person fills them before merge. No model API key in CI.
- Uploader copies: the Node `cli/bids-walker.js` (behind today's `bl bids upload`) gets a CI test
  against the generated table rather than a rewrite. pybrainlife's `bids_walker.py` (unmerged
  `enh/cli-aimport` branch) switches to the generated table once that branch merges.

## Left to the builder

File naming details, YAML vs JSON for records, readme template wording, how App purposes are
summarised, and the exact JSON Schema.
