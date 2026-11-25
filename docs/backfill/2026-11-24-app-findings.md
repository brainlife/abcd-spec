# App problems found while writing manifests, 2026-11-24

Six agents read the README, `main` and scripts of the 312 active Apps in repos we administer and
filled in their manifests (`catalog/apps/<id>.json`). Along the way they found the problems below.
**None of them was fixed**: fixing them changes how the Apps run, and each needs its maintainer.
The manifests describe what the code actually does and note several of these in `requirements`
or descriptions. Credentials found in code were reported privately, not listed here.

- app-FSLBET "test" (branch t2) and "test2" (master): test Apps; test2's code reads `.input`/`.fthreshold` but the registry declares `t2`, no parameters, output typed t2w. Broken.
- app-FSLBET fMRI: parameter text says default 0.4, registry default is 0.5.
- app-freesurfer-stats subcort-stats: README promises myelin/qMRI inputs; script only loops over DTI/DKI and NODDI.
- app-freesurfer-stats parc-stats-volume-diffusion: registry declares output `raw` that main never creates.
- app-tracking 1.5: main uses `module load` (MRtrix, FreeSurfer, FSL), tied to IU HPC; registry container covers one helper only.
- app-ensembletracking: exits 1 with no message when num_or_fibers > 25.
- app-warp-standard-label-rois: `apply_affine` has no effect (code tests misspelled `apply_afine == True`).
- app-tractprofiles-agg: container only in a commented-out line; no outputs; deprecated datatype.
- app-removeFirstB0: copies a bvecs file stored in the repo instead of the input's; valid only for one dataset.
- app-epi-t1-registration: README describes tensor fitting/dt6.mat the code does not produce.
- app-trekker: README says T1w required; registry/code use DWI+CSD+5TT; `mask` output never created.
- app-mrtrix3-tensor-fit: `norm` parameter read but unused.
- app-combine-parcellation, app-convert-tractmasks-to-rois: READMEs are template text.
- app-tmp-brain-extract: broken (`singularity -e` without `exec`; output in working dir).
- app-average-tractmasks: broken (`./average/sh`; loop always uses first mask name).
- app-slicer-fsl fmri-t1-v1.0.0 and montage-v1.0: READMEs describe other Apps; fmri-t1 bold input was described as DWI; FLAIR inputs described as t1w/t2w.
- app-FSLTopupEddy 1.1: encode test always true (acq_params always PA). eddy-only (OpenMP, CUDA): `dont_sep_offs_move` and `ol_sqr` never read (script reads `ol_sq`). eddy-only-cuda: registry output `regressors` never produced. topup-eddy_correct: topup field never applied; `mergefull` never read (only first DWI corrected).
- app-subj2reference "- copy": registered for neuro/SNR_and_dMRI_stats but warps NIfTI files; both Apps ignore the mask input.
- app-contrack-visual-white-matter: `minDistanceClean` unused; `contrackThreshold` unused on optic-radiation branch.
- app-template-python: template/test Apps; 5fa46d70 broken (default '1,1,1' unparsable; writes out_dir not out_res).
- app-networkneuro-agg: no output registered; runs without a container.
- app-create-networkneuro labels-v1.0: code needs `raw_mat`/`raw_netmat` inputs the registry lacks and ignores the registered ones.
- app-segment-hippamyg-nuclei: T2 branch never runs (checks a path that never exists).
- app-extract-diffusion-metrics-rois v1.2: README says FSL/NIfTI, code uses Workbench/CSV; myelin handling looks broken.
- app-vistasoft-registration 1.1: registry container only in a commented-out line.
- app-roiGenerator: most branches carry a README for another App; several registry taglines were copied from a FreeSurfer parcellation App (replaced in manifests). glasser-dwi-v1.2: `include_lgn`/`include_oc` never read; `freesurferInflate` uses undefined `fsurfInflate`.
- app-hcp-acpc-alignment 1.4: `reorient` never read. mp2rage-v1.5: volume-selection loop tests undefined `${test_vol}`.
- app-testgradientflip master: not containerised; parameters hard-coded or ignored; legacy test App.
- app-freesurfer-osg master: no `main` (custom hooks, Pegasus); README documents standalone OSG workflow.
- app-filter-tractograms binarize-labels: `binarize_labels` never acted on.
- app-extractTCKfromWMC: two registry Apps on the same branch (duplicates).
- app-apply-warp-to-peaks-bundles v1.0: "Temp…" App, no README.
- app-register-rois-mni 65d52d7f: registry keys `t1`/`inverse-warp` but run.sh reads `.input`/`.inverse_warp`; no parameters registered; probably cannot run. 63dd70b3: template and interp hard-coded (user choice ignored).
- app-eccentricity-classification: mrtrix3-* READMEs are "# app-combine-tracts"; 62a7bf96 freesurfer input never read.
- app-mrtrix3-roi2roi-tracking: thora/optic-tract branches carry the generic README.
- app-checkOrientation dtiinit: legacy host-FSL/`module load`/IUHPC code, no container; likely broken.
- app-tractclassification 5cf8256e: registry text mentioned LiFE fe input; App takes .tck.
- app-intersect-tract-roi: README describes an old vistasoft version; code uses MRtrix3 tckedit.
- app-warp-bold: every template option resolves to MNI152_T1_2mm.
- app-rsHRF: `tempmask` registered but never passed.
- bl_apps_dipy_buan_shapes 5fce6bec: nothing registered but main reads `clust_thr`, `threshold`, `subject_folder`. Broken registration.
- app-template-matlab 5f66ac1f: loads `config.json.example`; no output registered.
- app-eeglab2mne: no README; BIDS sidecar inputs accepted but unused.
- app-predict-ppcs: no output registered.
- app-sift2-connectome-generation 644170e4: registry container dipy but work runs in mrtrix3:3.0.3.
- app-cortex-tissue-mapping qmri-v1.1-nosnr (6115e055): code reads qMRI keys but registry input is `myelinmap`; nothing would be mapped.
- app-cortex-tissue-mapping Native & Template Space (60356cdd, 608da87c, 6115dd26): script reads `inverse_warp`, registry supplies `inverse-warp`; template-space surfaces likely fail.
- app-cortex-tissue-mapping t1-t2-ratio-v1.1-nosnr (608da73d, 608da87c): optional `cortexmap` input ignored. smooth-cortexmap-v1.0: README describes another App. Many registry taglines copied across branches.
- app-contrack-optic-radiation v1.1: `contrackThreshold` only in commented code; `minDistanceClean` never read.
- app-nobrainer: `parc` and `parc_fs` outputs are the reverse of their registry descriptions.
- bl_apps_dipy_buan_profiles 5fce6ccd: nothing registered but main needs `model_bundle_folder`, `subject_folder`, `no_disks`. Broken registration.
- francopestilli/app-helloworld "test-app": no registered inputs; code reads `t1`.
- app-maiaRings: template README; main clones DanNBullock/OCT_scripts at run time.
- app-dwi2t1-nonlinear: registry "branch" v0 is a tag.
- app-compile-tract-profiles: docs say `tracts.csv`, code writes `output_FiberStats.csv`.
- **app-freesurfer 7.3.2: registry parameter id is " localGI" (leading space); code reads `.localGI`, so the option is never applied.**
- app-trekker-roi-tracking: optic-tract-true-v1.2 README describes THORA; master-app* READMEs require a T1 input the registry lacks; tmp-add-rois is a temporary branch.
- app-segment-tracts-between-multiple-regions master: main reads `atlas` but the input key is `ROI`; surface generation likely broken.
- app-cortex-tissue-mapping-stats endpoints-v1.1: `weight` true skips all stats.
- app-fsl-anat mp2rage-v1.0: script reads `.input`, absent from config; likely broken.
- app-synthstrip (all 5): `border` read but never passed to mri_synthstrip.
- app-mrtrix3-act 1.4: copies fa.nii.gz into every tensor output file (md, ad, rd, tensor).
- app-visual-white-matter v1.1/v1.2: parameter `inv_length` but code reads `.inverse_length`; v1.2 single_endpoints branch commented out.
- app-extract-diffusion-metrics-tissue-types: CSF mask binarised from the grey-matter map; CSF stats wrong.
- app-qt1-mrq main: no `main` script; cannot run.
- ezbids enh/eyetracking: placeholder App "my new app" registered on the web-service repo.
- app-freesurfer-agg: runs without a container; registry lists brainlife/mcr.
