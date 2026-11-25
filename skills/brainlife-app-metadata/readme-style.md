# README style for brainlife App repos we maintain

Use `readme-exemplar.md` (the FreeSurfer README) as the model. Keep its section order and look;
adapt every section to the App. Write in plain, precise English; present tense; no hype.

Sections, in order (drop a section only if it truly does not apply):

1. **Header** (centred HTML): an image only if the repo has one (e.g. `docs/*.png`) or the README
   already shows one that still loads; the App's title; one-line pitch (what it produces from what);
   badges: "brainlife.io run this App" and DOI (primary App's DOI), ABCD spec v1.1, the main tool and
   version if pinned, license (MIT unless the repo has another).
2. **At a glance**: exactly the line `<!-- BLOCK -->` (the generated summary is inserted there).
3. **Versions on brainlife.io**: only when the repo hosts more than one App: a table of every
   registered App (name, tool version if known, branch link, DOI link, status current/available/
   deprecated). Mark the newest non-deprecated as current.
4. **Running the App**: on brainlife.io (what to pick, what it outputs into the project), and
   locally (requirements actually used by `main`: Singularity/Apptainer, jq, licences; a
   `config.json` example with the real keys of this App; `./main`). Keep useful specifics from the
   old README (sample datasets, CLI commands) and fix obviously stale ones (brain-life → brainlife).
5. **Outputs**: what is written and where, as a short list or tree.
6. **Troubleshooting**: only real failure modes from the manifest, code or old README.
7. **Citing**: the underlying method/tool papers (only ones the old README, manifest or code
   names; never invent a DOI), then exactly the line `<!-- BRAINLIFE-CITATIONS -->`.
8. **Authors**: keep every person from the old README (authors, contributors, project director);
   drop outdated email addresses; never add people who are not in the old README or git history.
9. **Funding**: exactly the line `<!-- FUNDING -->`.
10. **License**: `[MIT](LICENSE)` unless the repo has another licence; mention the underlying
    tool's licence when relevant.

Keep anything App-specific from the old README that a user needs (warnings, notes on inputs,
references, links to tutorials), folded into the right section. Remove badges for individual grants
(the Funding section replaces them) and the old "Abcdspec-compliant" badge (replaced in the header).
