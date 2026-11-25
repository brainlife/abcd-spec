<!--
  brainlife App README template (from the brainlife/app-freesurfer README).
  Replace everything in <ANGLE BRACKETS>, delete sections that do not apply, and keep the order.
  Model: https://github.com/brainlife/app-freesurfer#readme
  Delete this comment when done.
-->

<p align="center">
  <img src="docs/<IMAGE>.png" alt="<WHAT THE IMAGE SHOWS>" width="240">
</p>

<h1 align="center"><APP TITLE></h1>

<p align="center">
  <ONE LINE: WHAT IT PRODUCES FROM WHAT, e.g. "Cortical surfaces and parcellations from a single T1-weighted image.">
</p>

<p align="center">
  <a href="https://github.com/brainlife/abcd-spec"><img src="https://img.shields.io/badge/ABCD_Spec-v1.1-green.svg" alt="ABCD Spec v1.1"></a>
  <a href="https://doi.org/10.25663/brainlife.app.<N>"><img src="https://img.shields.io/badge/Brainlife-brainlife.app.<N>-blue.svg" alt="Run on brainlife.io"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="MIT license"></a>
</p>

## At a glance

<!--
  Generate this block from the App manifest (brainlife.app.json) instead of writing it by hand:
    python tools/readme.py brainlife.app.json README.md
  It adds the summary, a quick-facts table (inputs, outputs, container, resources, licences, DOI),
  input and output tables, and a collapsible parameter list between the markers below.
-->
<!-- brainlife-app:begin (generated from the App manifest; edit the manifest, not this block) -->
<!-- brainlife-app:end -->

## Versions on brainlife.io

<!-- Only if this repository hosts more than one App (one per branch). Otherwise delete this section. -->

| Version | <TOOL> | Branch | Run it | Status |
|---|---|---|---|---|
| <APP NAME> | <TOOL VERSION> | [`<BRANCH>`](https://github.com/brainlife/<REPO>/tree/<BRANCH>) | [doi:10.25663/brainlife.app.<N>](https://doi.org/10.25663/brainlife.app.<N>) | current |

## Running the App

### On brainlife.io

Open the App at [doi.org/10.25663/brainlife.app.<N>](https://doi.org/10.25663/brainlife.app.<N>), choose <THE INPUT DATASETS> from your project, set the options and press **Execute**. The outputs are archived to your project and can feed any App that takes <OUTPUT DATATYPES>.

### Locally

You need [Singularity/Apptainer](https://apptainer.org/) and [`jq`](https://jqlang.github.io/jq/)<, PLUS ANY LICENCE THE TOOL NEEDS>.

1. Clone this repository and check out the version you want (`git checkout <BRANCH>`).
2. Create `config.json` with the paths to your inputs and the options you want:

   ```json
   {
       "<INPUT KEY>": "/input/<path>",
       "<PARAMETER>": <DEFAULT>
   }
   ```

3. Run the App:

   ```bash
   ./main
   ```

### Sample data

Download sample input from brainlife.io with the [brainlife CLI](https://github.com/brainlife/cli):

```bash
npm install -g brainlife
bl login
bl dataset download <DATASET ID> && mv <DATASET ID> input/<INPUT>
```

## Outputs

```text
output/
└── <WHAT IS WRITTEN WHERE>
```

## Troubleshooting

- **`<ERROR MESSAGE>`**: <CAUSE AND FIX>.

## Citing

> [!TIP]
> If you use this App in your work, please cite the App, the software it builds on and brainlife.io (below). GitHub's **Cite this repository** button gives the App citation in APA and BibTeX (add a `CITATION.cff`).

- <APP NAME>. brainlife.io App. [doi:10.25663/brainlife.app.<N>](https://doi.org/10.25663/brainlife.app.<N>)
- <PAPERS FOR THE SOFTWARE THE APP USES; cite each tool's own paper, with its DOI>
- Hayashi S, Caron BA, Heinsfeld AS, et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. *Nature Methods* 21:809–813 (2024). [doi:10.1038/s41592-024-02237-2](https://doi.org/10.1038/s41592-024-02237-2)
- Avesani P, McPherson B, Hayashi S, et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. *Scientific Data* 6:69 (2019). [doi:10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)

## Authors

- <NAME> (<ROLE>)

**Contributors:** <NAMES>

## Funding

[![Wellcome-226486/Z/22/Z](https://img.shields.io/badge/Wellcome-226486%2FZ%2F22%2FZ-purple.svg)](https://wellcome.org/)
[![NIH-NINDS-U24NS140384](https://img.shields.io/badge/NIH_NINDS-U24NS140384-green.svg)](https://reporter.nih.gov/project-details/11261037)
[![NIH-NINDS-UM1NS132207](https://img.shields.io/badge/NIH_NINDS-UM1NS132207-green.svg)](https://reporter.nih.gov/project-details/11411328)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://reporter.nih.gov/project-details/10262925)
[![NIH-NIBIB-R01EB030896](https://img.shields.io/badge/NIH_NIBIB-R01EB030896-green.svg)](https://reporter.nih.gov/project-details/10428625)
[![NIH-NIMH-R01MH126699](https://img.shields.io/badge/NIH_NIMH-R01MH126699-green.svg)](https://reporter.nih.gov/project-details/10460628)
[![NIH-NIDCD-R01DC020088](https://img.shields.io/badge/NIH_NIDCD-R01DC020088-green.svg)](https://reporter.nih.gov/project-details/11140284)
[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-2203524](https://img.shields.io/badge/NSF_BCS-2203524-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2203524)
[![NSF-IIS-1636893](https://img.shields.io/badge/NSF_IIS-1636893-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-OAC-2148729](https://img.shields.io/badge/NSF_OAC-2148729-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2148729)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NSF-IIS-2148700](https://img.shields.io/badge/NSF_IIS-2148700-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2148700)
[![NSF-OAC-1916518](https://img.shields.io/badge/NSF_OAC-1916518-blue.svg)](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1916518)

<sub>brainlife.io is publicly funded, and acknowledging that support helps keep it running. This App was developed with support from Wellcome, the U.S. National Institutes of Health (including the BRAIN Initiative BRAIN CONNECTS program: The Axonal Projectome EXchange, U24NS140384, and the Center for Mesoscale Connectomics, UM1NS132207) and the U.S. National Science Foundation.</sub>

## License

[MIT](LICENSE). <UNDERLYING TOOL> is distributed under its own [license](<URL>).
