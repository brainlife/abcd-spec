# brainlife App specification v2: agent-ready App metadata

Status: draft for review. Author: Franco Pestilli with Claude. Date: 2026-11-24.

## Intent

brainlife.io is becoming the execution and provenance layer that AI agents work through (see the
workspace `CLAUDE.md`, "Direction"). Agents already discover and run Apps: the brainlife assistant
calls `list_apps`, `get_app` and `create_pipeline` over MCP, and the `kb` knowledge graph answers
questions such as "which Apps accept this dataset". What an agent can learn about an App today is
thin and unreliable. This project makes every public App describe itself completely, in a form that
software can check, so that an agent (or a person) can decide **whether** an App fits a task,
**how** to wire its inputs and set its parameters, and **what** a run will cost and produce,
without reading the App's shell scripts.

## What exists today (findings)

- **ABCD spec v1.1** (this repo) defines only execution: `start`, `status` and `stop` hooks plus
  an optional `package.json`. It says nothing about what an App does.
- **Everything else lives only in the warehouse database**, entered through a web form
  (`appSchema` in `warehouse-next/api/models.js`): name, `desc`, `desc_override`, `tags`, `doi`,
  `inputs[]`, `outputs[]`, `config` (parameter template and input wiring), `retry`, `stats`,
  `deprecated_by`.
- **GitHub and brainlife drift.** `common.update_appinfo` copies the GitHub description and
  topics into `desc` and `tags`, and contributors into `contributors`, on registration and on
  every save through `PUT /app/:id` (`controllers/app.js` ~line 400). Apps not saved recently
  carry stale copies, and 263 of 781 Apps have a `desc_override` that hides the GitHub text. A
  consequence: once the GitHub About panel is fixed, each App picks up the new text the next time
  anyone saves it.
- **Coverage across the 776 public Apps (508 repos):** parameters have a description 82% of the
  time (2,419/2,962), inputs 39% (675/1,725), outputs 37% (480/1,304); 519 Apps have no tags;
  93 are deprecated. Parameter types are loose (`number`, `integer`, `float` coexist; enum options
  are free text).
- **Run facts are buried in scripts.** `app-freesurfer/main` hard-codes resources
  (`#PBS -l nodes=1:ppn=16,vmem=29gb,walltime=18:00:00`), the container
  (`docker://brainlife/freesurfer:7.3.2`) and a required licence (`FREESURFER_LICENSE`).
- **One repo, many Apps.** Apps are versioned by branch (`github_branch`); Freesurfer's repo serves
  three registered Apps from three branches, while the GitHub About panel is per repo.
- 171 of the 508 repos are in the `brainlife` org; the rest belong to about 60 other accounts.
- abcd-spec already ships a `bl2bids` hook that builds a BIDS directory from an App's inputs.

## Goals

1. **A machine-checkable App manifest** (spec v2): one file per App version, validated by a
   JSON Schema published in this repo.
2. **One source of truth** for the fields the manifest owns: the GitHub About panel and the
   brainlife record are derived from it.
3. **Agent-facing content:** a one-line summary, a longer description, typed and documented
   inputs, outputs and parameters, runtime needs, software and citations, and known failure modes
   with their fixes.
4. **Served where agents look:** the warehouse API (`GET /app/:id`), the MCP `get_app` and
   `list_apps` tools and the `kb` graph.
5. **A reusable skill** that audits an App against the spec and drafts its manifest and About
   text, so the backfill and future Apps follow one procedure.
6. **Backfill the public Apps**, starting with the `brainlife` org.

## Non-goals

- Changing how Apps run. The ABCD hooks and `main` stay; v2 adds a description layer beside v1.1.
- A workflow language (CWL, Nextflow) or adopting Boutiques descriptors (considered and declined
  by Franco). Field names borrow from Boutiques and CodeMeta where they fit, so a later export is
  easy.
- New web-interface features (out of scope per the workspace rules).

## Anti-goals (failure even if it "works")

- **Invented metadata.** A plausible but wrong description, unit or range is worse for an agent
  than a missing one. Anything not grounded in the code, README, registry record or the tool's own
  documentation is marked `unknown` and left for a human.
- **Two sources of truth** for the same field.
- **Breaking existing Apps or pipelines.** No App may stop running or change its inputs because of
  this project.

## Constraints

- Workspace rules: no deploys; never commit to `master`; a branch and pull request for every
  change; tests first; add, then switch, then remove.
- Writes to live brainlife App records (saving Apps, clearing `desc_override`) need Franco's
  explicit go-ahead and an admin token, as a separate step.
- Repos outside the `brainlife` org (and Franco's own) cannot be edited by us; their owners get a
  pull request (manifest) or an issue (About text).

## Approaches considered

- **A. A brainlife manifest file in each App branch, schema published in abcd-spec (chosen by
  Franco).** Versioned with the code, one per branch, validated in CI, read by brainlife.
- **B. Keep the warehouse database as the source; tighten its schema and publish it in OpenAPI.**
  No repo changes, but GitHub and brainlife keep drifting and nothing is versioned with the code.
- **C. Adopt Boutiques descriptors.** Established standard with tooling, but brainlife Apps are
  configured by `config.json` rather than a command line, and datatypes, datatype tags,
  tag pass-through and multi-input wiring would all need extensions. Considered and declined.

## The manifest

File: `brainlife.app.json` at the root of each App branch. Draft fields (the schema is the
deliverable; names are proposals):

| Field | Purpose for agents | Source for backfill |
|---|---|---|
| `spec` | `"brainlife-app/2.0"` | constant |
| `name`, `version` | display name, App version | registry `name`, branch |
| `summary` | one line, ≤ 350 characters; the GitHub description and brainlife tagline | rewritten from `desc`, `desc_override`, README |
| `description` | what it does, when to use it, when not to | README, `desc` |
| `category`, `topics` | controlled vocabulary (e.g. `preprocessing`, `tractography`) plus free topics; become GitHub topics and brainlife `tags` | registry `tags`, README |
| `doi` | citable identifier | registry `doi` |
| `inputs[]` | `id`, `datatype` (by name, e.g. `neuro/anat/t1w`), `datatype_tags`, `optional`, `multi`, `description`, `requirements` (e.g. "submillimetre needs `hires`") | registry `inputs`, datatypes |
| `outputs[]` | `id`, `datatype`, `datatype_tags`, `datatype_tags_pass`, `description` | registry `outputs` |
| `parameters[]` | `id`, `type` ∈ `string, integer, number, boolean, enum`, `description`, `default`, `units`, `minimum`, `maximum`, `options[{value, label}]`, `required`, `advanced` | registry `config` |
| `runtime` | `container` (image and tag; digest when known), `resources` (`cpus`, `memory_gb`, `walltime_hours`, `gpu`), `licenses_required[]` | `main`, hooks, Dockerfile |
| `software[]` | underlying tools and versions (FreeSurfer 7.3.2, MRtrix3 …) | `main`, container |
| `citations[]` | DOI or text of papers to cite | README, registry `references` |
| `license` | SPDX identifier of the App code | repo licence |
| `failure_modes[]` | `{message, cause, fix}`, e.g. "Talairach failed" → set `notalcheck` | parameter descriptions, README, issues |
| `examples[]` | links to public example runs or test configs | `stats.examples`, `config.json.sample` |
| `maintainers[]` | who to contact | registry `admins`, contributors |
| `deprecated_by` | successor App | registry |
| `kind` | `native` (runs `./main`) or `bids-app` (reserved; see BIDS Apps) | constant `native` for the backfill |

Rules enforced (the "reliable" part): required fields; `summary` length; each parameter's
`default` satisfies its own type, range and options; every registry `config` key maps to exactly
one manifest input or parameter; every datatype name exists in brainlife's datatype list.

**`unknown` values (Claude's call).** Descriptive fields (`description` of an input, output or
parameter, `units`, `failure_modes`, `software`, `citations`) may hold the literal `"unknown"`.
Structural fields (ids, types, datatypes, defaults) may not. The validator reports unknowns as
warnings, so a manifest with unknowns can merge, and the warehouse applies its known fields. The
review table lists every unknown so the gaps are visible.

## BIDS Apps

BIDS Apps (Gorgolewski et al., 2017) are containers with one fixed command line,
`<bids_dir> <output_dir> participant|group [--participant_label …]`, published under `bids/` on
Docker Hub and elsewhere (fMRIPrep, MRIQC, QSIPrep …). brainlife already has half the bridge in
`bl2bids`. v2 reserves `kind: "bids-app"` with `runtime.container` and a `bids` block (analysis
levels, the BIDS inputs it needs, the derivatives it writes and how they map to brainlife
outputs) so that a BIDS App could be registered from its container plus a manifest, without a
hand-written wrapper. The execution side (staging, `bl2bids`, mapping derivatives back) is a later
phase; v2 only fixes the contract and documents it with one worked example.

## Source of truth: who owns which field (Claude's call)

- **Manifest-owned:** `summary` (→ `desc`), `description`, `tags`, `doi`, and the descriptive
  fields of inputs, outputs and parameters. When an App branch has a valid manifest, the warehouse
  fills these from it on every save; `PUT /app/:id` rejects edits to them with a message naming
  the repo file (an API rule, no UI change; the form shows the API's error).
- **Still form- and registry-owned in v2:** run-time wiring: `config` input entries, `includes`,
  `output_on_root`, `files`, `archive`, `retry`, `projects`, `admins`, `avatar`. The manifest
  repeats inputs, outputs and parameters for agents, and the validator checks it agrees with the
  registry, but the warehouse does not build run-time wiring from it in v2 (see open question 1).
- **Repos with several App branches:** the GitHub About panel and topics come from the manifest on
  the repo's default branch; if that App is deprecated, from the newest non-deprecated App branch.
  Each App's brainlife record uses its own branch's manifest.
- **`desc_override`:** the skill moves existing override text into the draft `summary` as a
  candidate for review. The override is cleared only once that App's manifest supplies a summary.
  Apps without a manifest keep today's behaviour.

## Components

1. **abcd-spec v2 (this repo):** `schema/brainlife-app-2.0.json`, a v2 section in `README.md`,
   worked examples (Freesurfer, one MEG App, one BIDS App), a validator (small Python CLI using
   `jsonschema`, with the datatype list it checks against), and a GitHub Action that App repos can
   add.
2. **Skill `brainlife-app-metadata`:** given an App (or a list), it (a) gathers the registry
   record, repo, `main`, README and container hints; (b) drafts `brainlife.app.json`, the GitHub
   summary and topics; (c) validates the draft; (d) marks every ungrounded value `unknown`;
   (e) writes a review table; and only after approval (f) applies: `gh repo edit` for the About
   panel, a pull request adding the manifest to each App branch, and, with the separate go-ahead,
   the brainlife record update. Built with the skill-creator workflow and evaluated on five known
   Apps before wider use.
3. **Warehouse (warehouse-next):** read and validate `brainlife.app.json` from the App's branch in
   `update_appinfo`, apply the manifest-owned fields, store the full manifest, and return it from
   `GET /app/:id`. Added beside the current GitHub copy (add, then switch), with tests first.
4. **Agent surfaces:** MCP `get_app` and `list_apps` return `summary`, typed parameters, runtime and
   failure modes; `kb` ingests the new fields.
5. **Backfill:** `brainlife` org first, in batches of about 20 repos, each batch reviewed by Franco
   before anything is applied; then pull requests and issues to external owners.

## Order of work

1. Schema, validator and two hand-written example manifests (proves the format).
2. Skill, evaluated on five Apps.
3. GitHub About backfill for the `brainlife` org. Note: brainlife records pick up the new text on
   their next save, so this step also changes what brainlife shows over time.
4. Manifest pull requests to App branches.
5. Warehouse read path and API exposure, then MCP and kb.
6. Re-save brainlife records and clear overrides (separate approval), then external owners.

## Open questions for Franco

1. Is the manifest a description layer only in v2 (as written above), or should the warehouse also
   build the run-time record (`inputs`, `outputs`, `config` wiring) from it?
2. May the skill and validator read brainlife.io with read-only `GET` requests (App records,
   datatype list), or must they work from a snapshot?

## Left to the builder

- Exact JSON Schema structure, `$id` URL and versioning scheme.
- The controlled vocabulary for `category` (derived from the existing tags).
- Whether the validator ships as a pip package or a script.
- Skill layout, evals and where it lives (a `skills/` folder in this repo is the default).
