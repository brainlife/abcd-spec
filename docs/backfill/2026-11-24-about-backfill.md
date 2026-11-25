# GitHub About backfill, 2026-11-24

Done with the `brainlife-app-metadata` skill. Metadata only:
no App code, branch, input, output or parameter was touched, and nothing was written to
brainlife.io.

## Scope

- 776 public Apps on brainlife.io, 508 repos. Editable by us: 172 (171 in `brainlife`, plus
  `francopestilli/app-helloworld`). Two other personal repos we administer were left alone.
- 171 repos changed: 158 got their primary App's DOI as website, 117 a new description,
  171 now carry the `brainlife-app` topic (ezbids already has the GitHub maximum of 20 topics).
- Kept on purpose: website links to upstream projects (fMRIPrep, QSIPrep, rsHRF, SOCR, Trekker,
  ezBIDS) and any existing DOI; existing topics (topics were only added).
- Every previous value is in `2026-11-24-about-undo.json`; the drafts, with their sources and
  confidence, are in `2026-11-24-about-proposals.json`.

## Held for a human (low confidence, README is a title or describes another tool)

app-average-tractmasks, app-merge-tractmasks, app-tractprofiles-agg, app-combine-tracts,
app-compute-average-tractmeasure, bl_apps_dipy_buan_profiles, bl_apps_dipy_buan_shapes,
app-apply-warp-to-peaks-bundles, app-freesurfer-agg, francopestilli/app-helloworld.
Their topics were added; their descriptions were not changed.

## Problems found in the Apps themselves (not fixed)

- **Wrong description:** app-segment-hippamyg-nuclei was described as thalamic segmentation
  (segmentThalamicNuclei.sh); its README runs segmentHA_T1.sh (hippocampus and amygdala). Fixed on
  GitHub; the brainlife record updates on its next save.
- **README describes a different App:** bl_apps_dipy_buan_profiles and bl_apps_dipy_buan_shapes
  (README is the dipy_mask wrapper); app-segment-tracts-between-multiple-regions (README is
  app-roi2roitracking).
- **Test or template Apps registered as public:** app-FSLBET ("test", "test2"), app-template-python
  (an override says one "should be deleted"), app-register-rois-mni (duplicate with placeholder ids).
- **Possibly stale:** app-freesurfer-osg (override says OSG no longer supports fsurf, App not
  deprecated); app-eccentricity-classification (a live App named "... - Deprecated").
- **One repo, two names:** app-contrack-optic-radiation was renamed app-contrack-visual-white-matter;
  both names are registered as Apps.
- **Registry records that fail the v2 checks (2 of 776):** kitchell/app-AFQ_figures (integer
  parameter `img_min` with default -0.5) and byxnr/Time-Frequency-Analysis-App (an enum parameter
  with no options).
- **No container found in `main`:** 78 Apps; 201 Apps have no usable tagline; input and output
  descriptions are missing for 1,050 inputs and 821 outputs (see the generated manifests).

## Not done yet (needs approval)

- Re-saving brainlife App records so `desc` and `tags` pick up the new GitHub text, and clearing
  the 263 `desc_override` values that now disagree with it. Until then brainlife shows the new text
  only for Apps without an override, after their next save.
- Manifest pull requests to App branches.
- About-panel issues for the 335 repos owned by others.
