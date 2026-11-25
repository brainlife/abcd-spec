import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import blapp  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


@pytest.fixture
def record():
    return json.loads((FIX / "freesurfer-7.3.2.registry.json").read_text())


@pytest.fixture
def main_text():
    return (FIX / "freesurfer.main").read_text()


@pytest.fixture
def manifest(record, main_text):
    return blapp.generate(record, main_text=main_text)


def test_generated_manifest_is_valid(manifest, record):
    errors, warnings = blapp.validate(manifest, registry=record)
    assert errors == []


def test_generate_maps_identity(manifest, record):
    assert manifest["spec"] == "brainlife-app/2.0"
    assert manifest["name"] == "Freesurfer 7.3.2"
    assert manifest["version"] == "7.3.2"
    assert manifest["doi"] == "10.25663/brainlife.app.664"
    assert manifest["registry"]["id"] == record["_id"]
    assert manifest["kind"] == "native"


def test_generate_maps_inputs_with_datatype_names(manifest):
    t1 = next(i for i in manifest["inputs"] if i["id"] == "t1")
    assert t1["datatype"] == "neuro/anat/t1w"
    assert t1["config_keys"] == ["t1"]
    assert t1["description"] == "t1 to input"


def test_generate_maps_outputs(manifest):
    out = manifest["outputs"][0]
    assert out["id"] == "freesurfer"
    assert out["datatype"] == "neuro/freesurfer"
    assert out["datatype_tags_pass"] == "t1"
    assert out["description"] == "unknown"


def test_generate_maps_parameters(manifest):
    hires = next(p for p in manifest["parameters"] if p["id"] == "hires")
    assert hires["type"] == "boolean"
    assert hires["default"] is False
    assert "submillimeter" in hires["description"]


def test_generate_reads_runtime_from_main(manifest):
    rt = manifest["runtime"]
    assert rt["container"] == "brainlife/freesurfer:7.3.2"
    assert rt["resources"] == {"cpus": 16, "memory_gb": 29, "walltime_hours": 18}
    assert rt["licenses_required"] == ["FREESURFER_LICENSE"]


def test_generate_without_main_marks_runtime_unknown(record):
    m = blapp.generate(record)
    assert m["runtime"]["container"] == "unknown"
    assert blapp.validate(m, registry=record)[0] == []


def test_float_and_integer_types_are_normalised():
    assert blapp.normalise_type({"type": "float"}) == "number"
    assert blapp.normalise_type({"type": "integer"}) == "integer"
    assert blapp.normalise_type({"type": "number"}) == "number"


def test_summary_too_long_is_an_error(manifest):
    manifest["summary"] = "x" * 351
    errors, _ = blapp.validate(manifest)
    assert any("summary" in e for e in errors)


def test_unknown_descriptions_are_warnings_not_errors(manifest):
    errors, warnings = blapp.validate(manifest)
    assert errors == []
    assert any("outputs[freesurfer].description" in w for w in warnings)


def test_unknown_is_not_allowed_in_structural_fields(manifest):
    manifest["inputs"][0]["datatype"] = "unknown"
    errors, _ = blapp.validate(manifest)
    assert errors


def test_unknown_datatype_name_is_an_error(manifest):
    manifest["inputs"][0]["datatype"] = "neuro/does-not-exist"
    errors, _ = blapp.validate(manifest)
    assert any("neuro/does-not-exist" in e for e in errors)


def test_default_outside_options_is_an_error(manifest):
    manifest["parameters"].append({
        "id": "mode", "type": "enum", "description": "d", "default": "c",
        "options": [{"value": "a"}, {"value": "b"}],
    })
    errors, _ = blapp.validate(manifest)
    assert any("mode" in e and "options" in e for e in errors)


def test_default_outside_range_is_an_error(manifest):
    manifest["parameters"].append({
        "id": "n", "type": "number", "description": "d", "default": 5, "minimum": 10,
    })
    errors, _ = blapp.validate(manifest)
    assert any("n" in e and "minimum" in e for e in errors)


def test_registry_mismatch_is_an_error(manifest, record):
    reg = copy.deepcopy(record)
    reg["config"]["extra_param"] = {"type": "string", "default": ""}
    errors, _ = blapp.validate(manifest, registry=reg)
    assert any("extra_param" in e for e in errors)


def test_about_panel_from_manifest(manifest):
    manifest["summary"] = "Runs FreeSurfer recon-all on a T1w image."
    manifest["topics"] = ["Anatomy Preprocessing", "analysis", "analysis"]
    about = blapp.about(manifest)
    assert about == {
        "description": "Runs FreeSurfer recon-all on a T1w image.",
        "homepage": "https://doi.org/10.25663/brainlife.app.664",
        "topics": ["analysis", "anatomy-preprocessing"],
    }


def test_walltime_under_an_hour_is_fractional(record):
    m = blapp.generate(record, main_text="#PBS -l nodes=1:ppn=2,vmem=8gb,walltime=00:30:00\n")
    assert m["runtime"]["resources"]["walltime_hours"] == 0.5


def test_long_tagline_moves_to_description(record):
    long = "First sentence of a long tagline. " + "More text. " * 40
    record = dict(record, desc_override=long)
    m = blapp.generate(record)
    assert m["summary"] == "First sentence of a long tagline."
    assert m["description"] == long.strip()
    assert blapp.validate(m)[0] == []


def test_long_tagline_without_short_first_sentence_is_unknown(record):
    record = dict(record, desc_override="x" * 400)
    m = blapp.generate(record)
    assert m["summary"] == "unknown"
    assert m["description"] == "x" * 400


def test_registry_type_quirks_are_normalised(record):
    record = copy.deepcopy(record)
    record["config"]["q"] = {"type": "number", "desc": "d", "default": 2, "min": "1", "max": "n/a",
                             "placeholder": 3}
    record["config"]["e"] = {"type": "enum", "desc": "d", "default": "a",
                             "options": [{"label": "a"}, {"value": "b", "label": "b"}]}
    m = blapp.generate(record)
    q = next(p for p in m["parameters"] if p["id"] == "q")
    assert q["minimum"] == 1 and "maximum" not in q and q["placeholder"] == "3"
    e = next(p for p in m["parameters"] if p["id"] == "e")
    assert [o["value"] for o in e["options"]] == ["a", "b"]
    assert blapp.validate(m, registry=record)[0] == []


def test_container_ignores_commented_lines(record):
    main = "#!/bin/bash\n# singularity exec docker://old/image:1 x\nsingularity exec docker://new/image:2 ./run\n"
    assert blapp.generate(record, main_text=main)["runtime"]["container"] == "new/image:2"


def test_container_expands_simple_variables(record):
    main = 'VERSION=22.0.6\nsingularity exec docker://nipreps/mriqc:${VERSION} ./run\n'
    assert blapp.generate(record, main_text=main)["runtime"]["container"] == "nipreps/mriqc:22.0.6"


def test_container_expands_variables_with_defaults(record):
    main = 'singularity exec docker://brainlife/fsl:${FSL_VERSION:-6.0.4} ./run\n'
    assert blapp.generate(record, main_text=main)["runtime"]["container"] == "brainlife/fsl:6.0.4"


def test_datatype_version_range_is_accepted(manifest):
    manifest["inputs"][0]["datatype_version"] = ">=1.0 <2.0"
    manifest["outputs"][0]["datatype_version"] = ">=1.0 <2.0"
    errors, _ = blapp.validate(manifest)
    assert errors == []


def test_datatype_version_is_optional(manifest):
    for item in manifest["inputs"] + manifest["outputs"]:
        item.pop("datatype_version", None)
    errors, _ = blapp.validate(manifest)
    assert errors == []


@pytest.mark.parametrize("section", ["inputs", "outputs"])
def test_datatype_version_must_be_a_string(manifest, section):
    manifest[section][0]["datatype_version"] = 1
    errors, _ = blapp.validate(manifest)
    assert any(e.startswith(f"{section}/0/datatype_version:") and "is not of type 'string'" in e
               for e in errors), errors
