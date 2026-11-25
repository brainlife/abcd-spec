# Datatype catalog: findings (2026-11-25)

Scope: all 140 datatypes on brainlife.io (snapshot `GET /api/warehouse/datatype?limit=0`,
2026-11-25), BIDS 1.11.2 (schema 2.0.0), App catalog `catalog/index.json` (774 Apps).
Records drafted by `tools/bldt.py draft`, judgement fields written by five agent batches following
`skills/brainlife-datatype-metadata`, then checked by the test suite. Nothing has been written to
brainlife.io.

## Numbers

- BIDS, best match per datatype: 8 equivalent, 31 partial, 101 no BIDS counterpart (mostly
  derivatives BIDS does not standardise: tractography, tract measures, connectivity matrices,
  transforms, surfaces, model fits).
- Sidecars: 60 carried as files, 14 rebuildable from data-object metadata (`_meta_`), 38 missing.
  20 optional sidecar file entries are proposed (`"proposed": true`, `"required": false`).
- Governance default tiers: 9 tier 1, 105 tier 2, 22 tier 3, 2 tier 4, 2 tier 5. Human neurodata:
  101 yes, 31 depends, 8 no.
- 21 datatypes have no App that reads or writes them (list below).
- Size on brainlife.io (`bldt.py diff`): all records 256,428 -> 315,474 bytes (+23%, under the
  25% cap). The readme written to brainlife.io is at most 700 bytes (use / not for, BIDS,
  sharing tier, App counts, link); file and App lists stay in the catalog.
- 11 records end above 4096 bytes and grow, so `push` holds them until approved
  (`--approve-size`); 9 of them were already above 4096 bytes before any change:
  generic/network, neuro/LiFE, neuro/anat/qmri, neuro/anat/t1w, neuro/dwi, neuro/fmap,
  neuro/func/task, neuro/parc-stats, neuro/precomputed/mesh, neuro/tractmeasures, neuro/wmc.

## Needs owner review

### Batch 5 (microscopy/generic/test)
- Test datatypes (0 Apps): neuro/fake, neuro/test ("will be deleted"), neuro/test_datatype, test2. Orphans 0 Apps: jupyter/notebook, model/classifyber, openscience/reprolit (bibliometric). neuro/ps-oct: only a test App, marked [In Development]. Dataset counts need login.
- generic/timeseries-deprecated original readme contains "--TODO describe--" (source text).
- BIDS: neuro/ome-zarr holds any micr technique (suffix needs tags; no micr sidecar); neuro/microscopy/nifti — BIDS micr does not allow NIfTI; zarr v3 registers only zarr.json (chunks elsewhere); generic/timeseries follows proposed BIDS derivatives timeseries (spec PR 519, not in 1.11.2); tif: no extension, no sidecar; 2PE is in micr rules but missing from schema suffix objects.
- Proposed sidecars added: neuro/ome-zarr, tif.
### Batch 3 (diffusion derivatives)
- 506 App purposes across 224 Apps. Tiers: all 2 except fgtair 3 (face; 2 once defaced), tract-tracing 1 (animal, human "no"); tractograms/masks/tables tier 4 if used as fingerprints.
- Unclear: neuro/SNR_and_dMRI_stats (original desc "Edit me", file some.csv; Apps use it for an SNR CSV and for warped NIfTI maps) — owner review. neuro/AFQ, neuro/conneval: no Apps.
- Test/orphan/duplicate: neuro/tract-tracing (in development, no Apps); neuro/tractmasks overlaps neuro/rois (self-described possibly deprecated); dsistudio/tractmeasure holds a DWI QC table, outside neuro/, near-duplicate name of neuro/dsistudio/tractmeasures; *-deprecated types used only by converter Apps.
- BIDS: live maps use non-BIDS suffixes tractography (tck/trk), life, ICVF (noddi; map covers only isovf), GFA (tensor) — set match none but kept datatype/suffix so export naming survives (existing maps are never rewritten anyway). tensor -> dwi/FA partial (only FA has a BIDS suffix). dtiinit -> derivative, partial. fgtair -> anat/T1w partial with acq-FGATIR.
### Batch 4 (anat/func derivatives)
- Tier 3: freesurfer, freesurfer/longitudinal-template, fmriprep (hold whole-head T1w), ashs (working dir may hold inputs), myelin-map (ratio images can show the face); each drops to 2 once defaced/brain-extracted. Tier 2 + tier-4 fingerprint condition: conmat, conmats, networkneuro, net-stats, laplace_beltrami_spectrum, cifti, surface/data, surface/gradient. Tier 1: seg-eval-metrics, seg-eval-metric-agg.
- Unclear: neuro/dp/optimal (no Apps, undocumented .mat files) — owner review; neuro/fmriprep (only producer "TDA Computing" has an unknown manifest).
- Orphan/duplicate: dp/optimal; parcellation/surface-deprecated (replaced by surface/data + surface/vertices); conmats overlaps conmat; labels "Experimental (Giulia)".
- neuro/parc-stats original readme contains the word TODO (source text).
- BIDS: networkneuro live map dwi/label-GM_dseg is not valid BIDS -> none; recon map had FA/tensor/CSD as raw -> derivative partial (only FA has a suffix). No BIDS 1.11.2 suffix for xfm transforms (nifti/h5), CIFTI dtseries, surface geometry, connectivity matrices, pRF maps -> none. parcellation/volume, cortexmap, surface/data, mask, rois: partial (label.json is not dseg.tsv; space/label/hemi live in brainlife tags).
### Batch 1 (raw MRI)
- 782 App purposes across 417 Apps. Raw MRI (t1w, t2w, flair, t2starw, dwi, bold, multiecho, asl): sidecar via _meta_ ("meta"). Proposed optional sidecars: qmri (PD, MTV, R2star, T2star), qsm.
- Unclear: neuro/phase-quality (no Apps) — owner review.
- No Apps: neuro/func/multiecho, neuro/hcp/abcd-fmri, neuro/hcp/freesurferpre, neuro/perf/ASL, neuro/phase-quality. Test Apps appear in usage lists (app-testasdsad, Test_1, DWI test, DWI TEST 0, dated brain-extraction tests, Suma app, TDA Computing).
- BIDS: neuro/dwi catalog maps to .bvec/.bval (live export keeps its existing dwi.bvecs/.bvals maps). neuro/fmap split into 8 partial correspondences (drafted map was all "epi"). neuro/regressors: not a BIDS suffix (fMRIPrep desc-confounds_timeseries) -> none; live map sends _meta_ to regressors.json although the datatype has a json file. raw: none. neuro/anat/qmri: R2star/T2star file descs look swapped on brainlife.io; VIP, SIR, WF have no BIDS suffix. neuro/stimulus: NIfTI aperture vs BIDS stim .tsv.gz -> none. neuro/pet: blood file needs recording- entity. mp2rage: MP2RAGE with inv/part entities plus UNIT1.
- Tiers: 3 anatomical, PET, HCP folders, raw (provisional); 2 dwi, fmap, func; 1 stimulus.
### Batch 2 (ephys/behaviour)
- Proposed optional sidecars: eeg.json, meg.json, and for BTi4D and EGI also channels/coordsystem/events. Long BIDS-copied file descs cut to one sentence.
- Unclear: behavior/eyetracking/peekbank (desc "TBD" + schema link, no Apps) — owner review.
- No Apps: peekbank, eyetrack/asc, neuro/meeg/mne/raw/annotation, neuro/meg/BTi4D. Test Apps: "EEG Data Quality" (eeglab), "Matlab docker test" (meg/fif).
- neuro/meg/fif-override original desc contains "(TODO which file stores this?)".
- BIDS: no record carries the REQUIRED *_eeg.json / *_meg.json sidecar -> every EEG/MEG match is partial. EGI .raw is not a BIDS EEG format (unmapped). meg/fif calibration_meg.dat / crosstalk_meg.fif are session-level acq- files in BIDS. mne/raw, fif, ctf, BTi4D all map to meg/meg -> aimport would see several candidates for one BIDS file.
- Datatype misuse by Apps: "Make BEM model" writes BEM solutions as neuro/meg/fif (tag bem); "Coregistration MRI with MEG" writes trans.fif as neuro/meeg/mne/covariance (tag trans); app-forward reads a transform from neuro/meeg/mne/ica; fif-override events.tsv sometimes holds bad-epoch/ICA index lists. neuro/meeg/stc live desc says "Boundary Element Model" (wrong) -> replaced.
- Tiers: 3 for vendor raw formats whose headers hold name/birth date (fif, ctf, BTi4D, edf, bdf); 2 otherwise.
