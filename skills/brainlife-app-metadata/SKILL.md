---
name: brainlife-app-metadata
description: Audit and enhance the metadata of brainlife.io Apps so agents and people can find, judge and run them. Use when asked to improve App descriptions, GitHub About panels (description, DOI link, topics), App manifests (brainlife.app.json, spec v2), or consistency between an App's GitHub repo and its brainlife.io record.
---

# brainlife App metadata

An App is one branch of a GitHub repo registered on brainlife.io. Its metadata lives in three
places that should say the same thing:

1. **The manifest**, `brainlife.app.json` on the App's branch (spec v2, schema in
   `schema/brainlife-app-2.0.schema.json`). This is the source.
2. **The GitHub About panel** of the repo: description, website, topics. Derived from the
   manifest of the repo's primary App (below).
3. **The brainlife.io record**. `desc` and `tags` are copied from the GitHub About panel whenever
   the App is saved; `desc_override`, if set, is shown instead of `desc`.

## Safety rules (do not skip)

- Metadata only. Never change an App's code, `main`, hooks, branches, inputs, outputs or
  parameters. Pipeline rules match on dataset tags, not App tags, so About-panel edits cannot
  break a running App; anything beyond that can.
- Never write to brainlife.io (saving an App, clearing `desc_override`) without the owner's
  explicit approval for that step. Read-only `GET`s are fine.
- Edit only repos you administer. For other repos, open an issue with the proposed text.
- Never remove an existing topic and never replace a good description; add and fix only.
- Record every previous value before changing it (`apply_about.py` writes an undo log).
- **Do not invent.** Every claim must come from the README, the registry record, `main`, the code,
  or the tool's own documentation. When you cannot ground something, write `unknown` (manifest)
  or leave the current value (About panel).

## Workflow

1. **Snapshot** the registry: `GET https://brainlife.io/api/warehouse/app?limit=2000&find={"removed":false}`
   (public Apps have no `projects`) and the datatype list. Keep the snapshot with the results.
2. **Audit** each repo with GitHub GraphQL: description, `homepageUrl`, topics, default branch,
   `viewerPermission`, archived. Flag: weak description (empty, under 40 characters, or just the
   repo name), website not a DOI, no topics, brainlife override that differs from GitHub.
3. **Draft manifests** with `tools/blapp.py generate <record> --main <main>`; validate with
   `tools/blapp.py validate <manifest> --registry <record>`. Errors block; `unknown` values are
   warnings to fill in later.
4. **Write the About text** for repos that need it, following the style guide below.
5. **Review**: produce a table (repo, current, proposed, source used) and get approval.
6. **Apply** with `apply_about.py --dry-run` first, then for real. Keep the undo log.

**Primary App of a repo** (supplies the website DOI): the App registered on the repo's default
branch; if that one is deprecated or absent, the newest non-deprecated App.

## Style guide: summary (GitHub description and brainlife tagline)

- One sentence, ideally 80–200 characters, never over 350.
- Shape: **verb + what it does + on what input + with which tool, + what it produces.**
  - Good: "Runs FreeSurfer recon-all on a T1-weighted image to produce cortical surfaces, a
    volumetric segmentation and the Desikan-Killiany, Destrieux and DKT parcellations."
  - Good: "Tracks white matter streamlines from preprocessed DWI with MRtrix3 constrained
    spherical deconvolution and outputs a .tck tractogram."
  - Bad: "This app will run freesurfer." (vague, "This app will"), "brainlife.io version of maTT"
    (says nothing), "The best tractography app" (claim).
- Present tense, active voice. No "This app", "This is", "brainlife.io version of", no emoji.
- Name the underlying tool (and version when it is certain), the input datatype and the output in
  plain words (e.g. "T1-weighted image", "DWI", "tractogram", "parcellation").
- One repo may host several App versions on different branches: describe what they share and
  leave version numbers out unless every branch uses the same one.
- If the App is a utility (format conversion, QA, visualisation, data import), say so plainly.
- Deprecated repos (every App deprecated): start with "Deprecated:" and name the replacement
  if known.

## Style guide: topics

- Lowercase, letters, digits and hyphens, up to 50 characters, at most 20 per repo.
- Keep every existing topic. Add up to 6 that help someone search, chosen from:
  - modality: `anatomy`, `dwi`, `fmri`, `meg`, `eeg`, `pet`, `ieeg`, `qsm`
  - task: `preprocessing`, `segmentation`, `parcellation`, `registration`, `tractography`,
    `tract-segmentation`, `diffusion-modeling`, `connectomics`, `network-analysis`,
    `surface-analysis`, `quality-control`, `visualization`, `statistics`, `conversion`,
    `bids`, `denoising`, `source-localization`, `machine-learning`
  - tool: `freesurfer`, `fsl`, `mrtrix3`, `ants`, `afni`, `dipy`, `mne-python`, `fmriprep`,
    `qsiprep`, `vistasoft`, `connectome-workbench`, `spm`, `nibabel`, `nilearn`, `dsi-studio`
- Always add `brainlife-app`, so the repo is findable as a brainlife App.
- Only add a topic the evidence supports.

## Enriching a manifest (filling in `unknown`)

Start from the generated draft and read the App's branch: README, `main`, and the scripts `main`
runs. Fill only descriptive fields; never change `id`, `type`, `datatype`, `datatype_tags`,
`default`, `options` values, `optional`, `multi`, `config_keys` or anything under `registry`.

- `summary`: as in the style guide below, specific to this branch (version numbers allowed when
  this branch pins them).
- `description`: 2–4 sentences: what it does, when to use it, what it needs, when not to use it.
- `inputs[].description` / `requirements`: what the file is and any condition the code checks or
  assumes (shell count, alignment, space, resolution).
- `outputs[].description`: what the output contains, in plain words.
- `parameters[].description`: what the parameter controls, from the code that reads it. Add
  `units` only when the code or README states them.
- `runtime.container`: from `main` or a Dockerfile; `resources` from `#PBS`/`#SBATCH` lines.
- `software[]`: tools the code actually calls, with versions only when pinned.
- `citations[]`: only references given in the README or code, with DOI when present.
- `failure_modes[]`: only error messages that appear in the code or README, with the fix they
  state or that the code makes obvious.
- `topics`: lowercase-hyphen, from the topics vocabulary below.

Run `python tools/blapp.py validate <manifest> --registry <record>`; zero errors is required.
If the README describes a different App or the code contradicts the registry, do not guess:
leave `unknown` and report it.

## Output format for drafted About text

One JSON object per repo:

```json
{"repo": "brainlife/app-freesurfer",
 "description": "Runs FreeSurfer recon-all on ...",
 "add_topics": ["anatomy", "segmentation", "freesurfer", "brainlife-app"],
 "keep_current_description": false,
 "source": "README, registry desc, main (container brainlife/freesurfer:7.3.2)",
 "confidence": "high"}
```

Set `keep_current_description: true` when the current text is already good, and
`confidence: "low"` when the evidence is thin; low-confidence descriptions are not applied
without review.

## READMEs for Apps we maintain

Follow `readme-style.md`, with `readme-exemplar.md` (FreeSurfer) as the model. Agents write the
README with three placeholders; `scripts/finalize_readmes.py` fills them with the generated summary
(`tools/readme.py`), the citations (the App, the verified tool papers in `tool-citations.json` for
software the App uses, and `brainlife-citations.md`) and `funding.md`, adds section icons, the cite
tip and a `CITATION.cff`, then publishes each README through a PR limited to `README.md` and
`CITATION.cff`.

`scripts/` holds the batch tools used for the 2026-11-24 backfill (brainlife record re-save,
README and licence PRs). They expect a working directory with the registry snapshot and manifests,
read the brainlife token from `~/.config/brainlife.io/.jwt`, and write logs so runs can resume.
