import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "brainlife-app-metadata" / "scripts"))

import apply_about  # noqa: E402


def current(**kw):
    base = {"description": "", "homepage": "", "topics": []}
    base.update(kw)
    return base


DOI = "https://doi.org/10.25663/brainlife.app.1"


def test_empty_homepage_gets_doi():
    change = apply_about.plan(current(), DOI, None)
    assert change["homepage"] == DOI


def test_brainlife_app_link_is_replaced_by_doi():
    change = apply_about.plan(current(homepage="https://brainlife.io/app/abc"), DOI, None)
    assert change["homepage"] == DOI


def test_upstream_tool_link_is_kept():
    change = apply_about.plan(current(homepage="https://github.com/nipreps/fmriprep"), DOI, None)
    assert "homepage" not in change


def test_existing_doi_is_kept():
    change = apply_about.plan(current(homepage="https://doi.org/10.25663/bl.app.0"), DOI, None)
    assert "homepage" not in change


def test_topics_are_added_never_removed():
    proposal = {"add_topics": ["dwi", "Bad Topic!", "analysis"], "keep_current_description": True,
                "confidence": "high"}
    change = apply_about.plan(current(topics=["analysis", "old"]), None, proposal)
    assert change["topics"] == ["analysis", "dwi", "old"]


def test_description_applied_only_with_enough_confidence():
    good = {"description": "Runs X on a T1-weighted image and outputs a mask.", "add_topics": [],
            "keep_current_description": False, "confidence": "medium"}
    assert apply_about.plan(current(), None, good)["description"] == good["description"]
    low = dict(good, confidence="low")
    assert "description" not in apply_about.plan(current(), None, low)


def test_description_lint_rejects_bad_text():
    for text in ("This app will run freesurfer.", "x" * 351, ""):
        bad = {"description": text, "add_topics": [], "keep_current_description": False,
               "confidence": "high"}
        assert "description" not in apply_about.plan(current(), None, bad)


def test_keep_current_description():
    keep = {"description": "ignored", "add_topics": [], "keep_current_description": True,
            "confidence": "high"}
    assert "description" not in apply_about.plan(current(description="Fine text."), None, keep)


def test_no_change_when_nothing_to_do():
    assert apply_about.plan(current(homepage=DOI, topics=["a"]), DOI, None) == {}
