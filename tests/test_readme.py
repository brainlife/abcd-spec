import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import readme  # noqa: E402

EXAMPLE = json.loads((ROOT / "examples" / "freesurfer-7.3.2.brainlife.app.json").read_text())


def test_block_has_summary_doi_and_tables():
    block = readme.render(EXAMPLE)
    assert block.startswith(readme.BEGIN) and block.rstrip().endswith(readme.END)
    assert EXAMPLE["summary"] in block
    assert "https://doi.org/10.25663/brainlife.app.664" in block
    assert "| `t1` | `neuro/anat/t1w` |" in block
    assert "| `hires` | boolean | `false` |" in block
    assert "brainlife/freesurfer:7.3.2" in block
    assert "10.1016/j.neuroimage.2012.01.021" in block


def test_unknown_values_are_not_shown_as_text():
    m = json.loads(json.dumps(EXAMPLE))
    m["outputs"][0]["description"] = "unknown"
    block = readme.render(m)
    assert "| `freesurfer` | `neuro/freesurfer` |  |" in block


def test_insert_after_title_keeps_the_rest():
    original = "# app-freesurfer\n\nMaintainer text.\n\n## Usage\nRun it.\n"
    updated = readme.insert(original, readme.render(EXAMPLE))
    assert updated.startswith("# app-freesurfer\n\n" + readme.BEGIN)
    assert updated.endswith("Maintainer text.\n\n## Usage\nRun it.\n")


def test_insert_after_leading_badges():
    original = "[![badge](x)](y)\n\n# app\n\nText.\n"
    updated = readme.insert(original, readme.render(EXAMPLE))
    assert updated.index("# app") < updated.index(readme.BEGIN) < updated.index("Text.")


def test_insert_replaces_an_existing_block():
    once = readme.insert("# app\n\nText.\n", readme.render(EXAMPLE))
    m = dict(EXAMPLE, summary="Changed summary.")
    twice = readme.insert(once, readme.render(m))
    assert twice.count(readme.BEGIN) == 1
    assert "Changed summary." in twice and EXAMPLE["summary"] not in twice
    assert twice.endswith("Text.\n")


def test_insert_into_readme_without_title():
    updated = readme.insert("Just text.\n", readme.render(EXAMPLE))
    assert updated.startswith(readme.BEGIN) and updated.endswith("Just text.\n")


def test_pipes_and_newlines_in_text_do_not_break_tables():
    m = json.loads(json.dumps(EXAMPLE))
    m["parameters"][0]["description"] = "a | b\nc"
    block = readme.render(m)
    assert "a \\| b c" in block


def test_requirements_are_joined_as_a_sentence():
    m = json.loads(json.dumps(EXAMPLE))
    m["inputs"][0]["description"] = "The FreeSurfer directory"
    m["inputs"][0]["requirements"] = "Completed recon-all."
    assert "The FreeSurfer directory. Completed recon-all." in readme.render(m)


def test_quick_facts_card():
    block = readme.render(EXAMPLE)
    assert "| **Inputs** | `neuro/anat/t1w` · `neuro/anat/t2w` (optional) |" in block
    assert "| **Outputs** | `neuro/freesurfer` · `neuro/parcellation/volume` ×3 |" in block
    assert "| **Resources** | 16 CPUs · 29 GB memory · 18 h walltime |" in block
    assert "| **Requires** | `FREESURFER_LICENSE` |" in block


def test_parameters_are_collapsible():
    block = readme.render(EXAMPLE)
    assert f"<summary><b>Parameters</b> ({len(EXAMPLE['parameters'])})</summary>" in block
    assert block.index("<details>") < block.index("| `hires` |") < block.index("</details>")


def test_references_can_be_left_out():
    assert "10.1016/j.neuroimage.2012.01.021" not in readme.render(EXAMPLE, references=False)
