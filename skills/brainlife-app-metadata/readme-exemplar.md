<p align="center">
  <img src="docs/fscortex.png" alt="FreeSurfer cortical parcellation" width="240">
</p>

<h1 align="center">FreeSurfer recon-all</h1>

<p align="center">
  Cortical surfaces, a whole-brain segmentation and three anatomical parcellations from a single T1-weighted image.
</p>

<p align="center">
  <a href="https://doi.org/10.25663/brainlife.app.664"><img src="https://img.shields.io/badge/brainlife.io-run%20this%20App-2b6cb0" alt="Run on brainlife.io"></a>
  <a href="https://doi.org/10.25663/brainlife.app.664"><img src="https://img.shields.io/badge/DOI-10.25663%2Fbrainlife.app.664-blue" alt="DOI"></a>
  <a href="https://github.com/brainlife/abcd-spec"><img src="https://img.shields.io/badge/ABCD%20spec-v1.1-green" alt="ABCD spec v1.1"></a>
  <a href="https://surfer.nmr.mgh.harvard.edu/"><img src="https://img.shields.io/badge/FreeSurfer-7.3.2-orange" alt="FreeSurfer 7.3.2"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT license"></a>
</p>

## At a glance

<!-- BLOCK -->

## Versions on brainlife.io

Each version is a separate App on brainlife.io, built from its own branch of this repository.

| Version | FreeSurfer | Branch | Run it | Status |
|---|---|---|---|---|
| Freesurfer 7.3.2 | 7.3.2 | [`7.3.2`](https://github.com/brainlife/app-freesurfer/tree/7.3.2) | [doi:10.25663/brainlife.app.664](https://doi.org/10.25663/brainlife.app.664) | current |
| Freesurfer 7.1.1 | 7.1.1 | [`7.1.1-1`](https://github.com/brainlife/app-freesurfer/tree/7.1.1-1) | [doi:10.25663/brainlife.app.462](https://doi.org/10.25663/brainlife.app.462) | available |
| Freesurfer | 6.0–7.1 (selectable) | [`1.12`](https://github.com/brainlife/app-freesurfer/tree/1.12) | [doi:10.25663/bl.app.0](https://doi.org/10.25663/bl.app.0) | deprecated |

## Running the App

### On brainlife.io

Open the App at [doi.org/10.25663/brainlife.app.664](https://doi.org/10.25663/brainlife.app.664), choose a T1-weighted dataset (and optionally a T2-weighted one) from your project, set the options and press **Execute**. The outputs are archived to your project and can feed any App that takes a `neuro/freesurfer` or `neuro/parcellation/volume` input.

### Locally

You need [Singularity/Apptainer](https://apptainer.org/), [`jq`](https://jqlang.github.io/jq/) and a [FreeSurfer license](https://surfer.nmr.mgh.harvard.edu/registration.html).

1. Clone this repository and check out the version you want (for example `git checkout 7.3.2`).
2. Create `config.json` with the paths to your inputs and the options you want:

   ```json
   {
       "t1": "/input/t1/t1.nii.gz",
       "hippocampal": false,
       "hires": false,
       "notalcheck": false,
       "localGI": false
   }
   ```

3. Export your license and run the App:

   ```bash
   export FREESURFER_LICENSE="$(cat ~/freesurfer/license.txt)"
   ./main
   ```

### Sample data

Download a T1-weighted sample from brainlife.io with the [brainlife CLI](https://github.com/brainlife/cli):

```bash
npm install -g brainlife
bl login
bl dataset download 5a050966eec2b300611abff2 && mv 5a050966eec2b300611abff2 input/t1
```

## Outputs

`output/` is a standard FreeSurfer subject directory:

```text
output/
├── label/     cortical labels and annotations (aparc, aparc.a2009s, aparc.DKTatlas)
├── mri/       volumes: T1, brainmask, aseg, aparc+aseg, …
├── scripts/   recon-all logs
├── stats/     aseg.stats, lh/rh.aparc.stats, …
└── surf/      white, pial, inflated and sphere surfaces
```

The App also writes the Desikan-Killiany (`parc`), Destrieux (`parc2009`) and DKT (`parcDKT`) volumetric parcellations as separate datasets.

## Troubleshooting

- **`ERROR: Talairach failed`**: set `notalcheck` to skip the Talairach check, and make sure the image is roughly aligned to the anatomical axes (the ACPC alignment Apps on brainlife.io can do this).
- **Submillimetre or HCP 7T data**: set `hires`, and `cw256` if the field of view is larger than 256 mm. Expect a much longer run.

## Citing

If you use this App, please cite FreeSurfer and brainlife.io:

- Fischl B. FreeSurfer. *NeuroImage* 62(2):774–781 (2012). [doi:10.1016/j.neuroimage.2012.01.021](https://doi.org/10.1016/j.neuroimage.2012.01.021)
<!-- BRAINLIFE-CITATIONS -->

## Authors

- Franco Pestilli (project director)
- Lindsey Kitchell

**Contributors:** Soichi Hayashi, Brent McPherson

## Funding

<!-- FUNDING -->

## License

[MIT](LICENSE). FreeSurfer itself is distributed under its own [license](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferSoftwareLicense).
