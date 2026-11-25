---
name: brainlife-datatype-metadata
description: Document brainlife.io datatypes in the catalog (abcd-spec datatypes/): what a datatype is, its files, which Apps use it and why, how it maps to BIDS, and governance defaults from the Global Brain Governance toolkit. Use when asked to improve datatype descriptions or readmes, map datatypes to BIDS, assess datatype privacy or sharing risk, or review candidate datatypes drawn from BIDS.
---

# brainlife datatype metadata

A datatype is the contract between Apps on brainlife.io: an App's input and output each name one.
Each datatype has a record in `datatypes/<slug>.json` (schema `schema/datatype-record-1.0.schema.json`;
drafts of datatypes not yet on brainlife.io in `datatypes/drafts/`). The record is the reviewed
source; `tools/bldt.py` drafts it, renders the readme, and writes short text to brainlife.io.
Design: `docs/superpowers/specs/2026-11-25-datatype-catalog-design.md`.

## Safety rules (do not skip)

- Never change `brainlife._id`, `brainlife.name`, `brainlife.original`, or an existing file's
  `id`, `filename`, `dirname`, `required`. Add, never remove.
- A new file entry is always `"required": false` and `"proposed": true`.
- Nothing is written to brainlife.io except by `bldt.py push`, after the owner merges the PR.
- **Do not invent.** Ground every claim in: the live record (`brainlife.original`, `files`), the
  App manifests that use it (`catalog/apps/<app_id>.json`: summary, description, input/output
  descriptions, `config_keys`), the BIDS schema (`snapshots/bids-schema-1.11.2.json`), or the
  file names. If you cannot tell what a datatype is, say so in `desc` ("Unclear: ...") and add a
  `not_suitable_for` line asking for owner review.

## Size limits (records travel with every data object; keep them small)

- `brainlife.desc`: at most 200 characters, one or two plain sentences: what the data is and its
  format. No marketing, no "this datatype".
- `files[].desc`: one short sentence.
- `usage.intended_use`, `usage.not_suitable_for`: 1-3 items each, one sentence each.
- App `purpose`: one short clause ("tractography from preprocessed DWI").
- `governance.*` lists: 1-3 items each; `rationale` at most two sentences.
- `bids.correspondences[].notes`: one sentence or empty.

## Filling a record

1. Read `brainlife.original` and `files`. Read the manifests of every App in
   `usage.inputs_of` and `usage.outputs_of` (`catalog/apps/<app_id>.json`); they say what the
   data is used for and produced from. Infer what the datatype actually holds.
2. Write `brainlife.desc` and each `files[].desc` (replace every `"TODO"`).
3. Write each App's `purpose`, and `intended_use` / `not_suitable_for` (what it can feed, and
   common misuses: wrong space, missing sidecar, not for group stats, etc.).
4. BIDS mapping, one correspondence per BIDS (datatype, suffix) it relates to:
   - `match`: `equivalent` (same content and files as the BIDS suffix), `partial` (subset,
     superset, several suffixes bundled, different file layout, or tags needed to tell apart),
     `none` (no BIDS counterpart; then use `"datatype": "", "suffix": ""` and say why in `notes`).
   - BIDS derivatives count (BEP-defined suffixes such as `dseg`, `probseg`, `mask`, `bold` in
     a derivative space): use `level: "derivative"`.
   - `files`: brainlife file id -> BIDS filename part (`dwi.bvec`). Sidecars: `file` if the
     datatype carries the JSON/TSV, `meta` if brainlife keeps those fields in each data object's
     metadata so the sidecar can be rebuilt (raw MRI imported by ezBIDS/aimport: yes), `missing`
     if neither. For `missing`, add the sidecar as a proposed optional file entry.
   - Leave `extensions` and `entities` as drafted from the BIDS schema unless they are wrong.
5. Governance (toolkit `~/git/braindatagovernance/data/tiers.yml`, Tool 1 steps 1-8):
   - `human_neurodata`: `yes`, `no` (phantom, animal-only, synthetic, software), or `depends`.
   - `default_tier` (highest applicable tier governs; when unsure, the more protective):
     1 aggregated, no participant-level records (group stats, atlases, templates);
     2 participant-level without direct identifiers (most processed MRI, EEG/MEG, derivatives);
     3 directly identifiable or intrinsically traceable (non-defaced T1w/T2w/FLAIR showing the
       face, raw DICOM, recordings with identifying headers, video, voice);
     4 functionally revealing derivatives (connectome fingerprints, embeddings, predictions,
       cognitive/behavioural profiles, decoders);
     5 model-associated (trained model weights or persistent embeddings).
     Datatypes that are not human neurodata: tier 1 with `human_neurodata: "no"`.
   - `tier_conditions`: what moves an object (e.g. "Tier 2 once defaced and header-scrubbed").
   - `information_kinds`: from anatomy, function, behaviour, physiology, identity, health_status,
     demographics, none.
   - `identifying_risks`, `sharing_cautions`: concrete (face, DICOM headers, acquisition dates,
     device serials, free-text metadata, rare conditions in small samples).
   - `rationale`: cite the toolkit step, e.g. "Tool 1 step 5: recognisable facial anatomy".
6. Leave `provenance.todo` alone; `bldt.py draft` recomputes it. Add the sources you used to
   `provenance.sources` and set `provenance.drafted_by` to who wrote it.
7. Check: `python -c "import sys;sys.path.insert(0,'tools');import dtrecord,glob;[print(f,e) for f in glob.glob('datatypes/*.json') for e in dtrecord.validate(dtrecord.load(f))]"`
   prints nothing, and no `"TODO"` remains in your files (`grep -l TODO datatypes/*.json`).

## Worked example: neuro/anat/t1w

- desc: "T1-weighted anatomical MRI volume (NIfTI), the usual reference image for registration
  and cortical reconstruction."
- BIDS: `anat/T1w`, `equivalent`, raw; `t1.nii.gz` -> `T1w.nii.gz`; sidecar `meta`.
- Governance: human `yes`; tier 3; conditions "Tier 2 once defaced and header-scrubbed";
  kinds anatomy, identity; risks "Face is recognisable in non-defaced images"; cautions
  "Deface before sharing outside a controlled project"; rationale "Tool 1 step 5: recognisable
  identifying anatomy."

## Candidate datatypes from BIDS

Drafts in `datatypes/drafts/` come from BIDS suffixes with no brainlife datatype. Do not
register them. List them in `docs/backfill/<date>-datatype-candidates.md` with a recommendation
(create, merge into an existing datatype, or skip) for the owner to review.
