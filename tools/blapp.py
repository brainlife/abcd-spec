#!/usr/bin/env python3
"""Generate and validate brainlife App manifests (brainlife.app.json, spec v2).

    blapp.py generate <registry-record.json> [--main main] > brainlife.app.json
    blapp.py validate brainlife.app.json [--registry registry-record.json]
    blapp.py about brainlife.app.json

A registry record is one App as returned by GET /api/warehouse/app.
The manifest only describes the App; nothing here changes how it runs.
"""
import argparse
import json
import pathlib
import re
import sys

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "brainlife-app-2.0.schema.json").read_text())
DATATYPES = json.loads((ROOT / "schema" / "datatypes.json").read_text())
DATATYPE_NAME = {d["id"]: d["name"] for d in DATATYPES}
DATATYPE_NAMES = set(DATATYPE_NAME.values())

UNKNOWN = "unknown"
SUMMARY_MAX = 350


def normalise_type(param):
    t = param.get("type")
    if t == "float":
        return "number"
    return t


def _text(value):
    value = (value or "").strip()
    return value if value else UNKNOWN


def _number(value):
    """A registry min/max as a number, or None when it is not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        f = float(str(value).strip())
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def _option(o):
    value = o.get("value") if o.get("value") not in (None, "") else o.get("label")
    return {k: v for k, v in (("value", value), ("label", o.get("label")),
                              ("description", o.get("desc"))) if v not in (None, "")}


def _parameter(key, c):
    p = {"id": key, "type": normalise_type(c), "description": _text(c.get("desc") or c.get("description"))}
    if "default" in c and c["default"] is not None:
        p["default"] = c["default"]
    for src, dst in (("min", "minimum"), ("max", "maximum")):
        if (n := _number(c.get(src))) is not None:
            p[dst] = n
    if c.get("options"):
        p["options"] = [opt for opt in map(_option, c["options"]) if "value" in opt]
    if "optional" in c:
        p["required"] = not c["optional"]
    for flag in ("advanced", "readonly", "multiline"):
        if c.get(flag):
            p[flag] = True
    if c.get("placeholder") not in (None, ""):
        p["placeholder"] = str(c["placeholder"])
    return p


def _hours(h, m=0, s=0):
    hours = int(h) + int(m or 0) / 60 + int(s or 0) / 3600
    return int(hours) if float(hours).is_integer() else round(hours, 2)


def _summary(record):
    """(summary, description) from the registry tagline. A tagline too long for the
    summary moves to the description; its first sentence becomes the summary if short."""
    text = (record.get("desc_override") or record.get("desc") or "").strip()
    if len(text) <= SUMMARY_MAX:
        return _text(text), UNKNOWN
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].strip()
    return (first if len(first) <= SUMMARY_MAX else UNKNOWN), text


def _expand(text, code):
    """Expand $VAR, ${VAR} and ${VAR:-default} from simple VAR=value assignments in the
    script; leave the container unknown if a variable cannot be resolved."""
    assigned = dict(re.findall(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=['\"]?([^\s'\"$]+)['\"]?\s*$", code, re.M))

    def value(m):
        name, default = m.group(1) or m.group(3), m.group(2)
        return assigned.get(name, default if default is not None else m.group(0))

    expanded = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::?-([^}]*))?\}|\$([A-Za-z_][A-Za-z0-9_]*)", value, text)
    return UNKNOWN if "$" in expanded else expanded


def _runtime(main_text):
    rt = {"container": UNKNOWN}
    if not main_text:
        return rt
    code = "\n".join(line for line in main_text.splitlines() if not line.lstrip().startswith("#"))
    m = re.search(r"docker://([^\s'\"]+)", code)
    if m:
        rt["container"] = _expand(m.group(1), code)
    res = {}
    pbs = re.search(r"#PBS\s+-l\s+(\S+)", main_text)
    if pbs:
        spec = pbs.group(1)
        if (n := re.search(r"ppn=(\d+)", spec)):
            res["cpus"] = int(n.group(1))
        if (n := re.search(r"vmem=(\d+)gb", spec, re.I)):
            res["memory_gb"] = int(n.group(1))
        if (n := re.search(r"walltime=(\d+):(\d+)(?::(\d+))?", spec)):
            res["walltime_hours"] = _hours(*n.groups())
    for pattern, key, conv in ((r"#SBATCH\s+(?:-c|--cpus-per-task)[= ](\d+)", "cpus", int),
                               (r"#SBATCH\s+--mem=(\d+)G", "memory_gb", int),
                               (r"#SBATCH\s+(?:-t|--time)[= ](\d+:\d+(?::\d+)?)", "walltime_hours",
                                lambda t: _hours(*t.split(":")))):
        if key not in res and (n := re.search(pattern, main_text)):
            res[key] = conv(n.group(1))
    if re.search(r"#(PBS|SBATCH).*gpu", main_text, re.I):
        res["gpu"] = True
    if res:
        rt["resources"] = res
    licenses = sorted(set(re.findall(r"\$\{?([A-Z][A-Z0-9_]*LICENSE[A-Z0-9_]*)", main_text)))
    if licenses:
        rt["licenses_required"] = licenses
    return rt


def generate(record, main_text=None):
    config = record.get("config") or {}
    inputs = []
    for i in record.get("inputs", []):
        keys = [k for k, c in config.items() if isinstance(c, dict) and c.get("type") == "input" and c.get("input_id") == i["id"]]
        entry = {
            "id": i["id"],
            "datatype": DATATYPE_NAME.get(i["datatype"], i["datatype"]),
            "datatype_tags": i.get("datatype_tags") or [],
            "optional": bool(i.get("optional")),
            "multi": bool(i.get("multi")),
            "description": _text(i.get("desc")),
            "config_keys": keys,
        }
        if i.get("advanced"):
            entry["advanced"] = True
        inputs.append(entry)
    outputs = []
    for o in record.get("outputs", []):
        entry = {"id": o["id"], "datatype": DATATYPE_NAME.get(o["datatype"], o["datatype"]),
                 "datatype_tags": o.get("datatype_tags") or [], "description": _text(o.get("desc"))}
        if o.get("datatype_tags_pass"):
            entry["datatype_tags_pass"] = o["datatype_tags_pass"]
        outputs.append(entry)
    parameters = [_parameter(k, c) for k, c in config.items()
                  if isinstance(c, dict) and c.get("type") not in ("input", "output")]
    summary, description = _summary(record)
    manifest = {
        "spec": "brainlife-app/2.0",
        "name": record["name"],
        "version": record.get("github_branch") or "master",
        "summary": summary,
        "description": description,
        "kind": "native",
        "topics": sorted({_topic(t) for t in record.get("tags") or [] if _topic(t)}),
        "registry": {"id": record["_id"], "github": record["github"], "branch": record.get("github_branch") or "master"},
        "inputs": inputs,
        "outputs": outputs,
        "parameters": parameters,
        "runtime": _runtime(main_text),
    }
    if record.get("doi"):
        manifest["doi"] = record["doi"]
    if record.get("deprecated_by"):
        manifest["deprecated_by"] = record["deprecated_by"]
    return manifest


def _topic(tag):
    t = re.sub(r"[^a-z0-9-]+", "-", tag.strip().lower()).strip("-")
    return t[:50]


def _check_default(p):
    if "default" not in p or p["default"] in (None, ""):
        return []
    d, t, errs = p["default"], p["type"], []
    if t == "boolean" and not isinstance(d, bool):
        errs.append(f"parameters[{p['id']}].default {d!r} is not a boolean")
    if t in ("number", "integer"):
        if isinstance(d, bool) or not isinstance(d, (int, float)):
            errs.append(f"parameters[{p['id']}].default {d!r} is not a {t}")
        else:
            if t == "integer" and not float(d).is_integer():
                errs.append(f"parameters[{p['id']}].default {d!r} is not an integer")
            if "minimum" in p and d < p["minimum"]:
                errs.append(f"parameters[{p['id']}].default {d!r} is below minimum {p['minimum']}")
            if "maximum" in p and d > p["maximum"]:
                errs.append(f"parameters[{p['id']}].default {d!r} is above maximum {p['maximum']}")
    if t == "enum":
        values = [o["value"] for o in p.get("options", [])]
        if d not in values and str(d) not in [str(v) for v in values]:
            errs.append(f"parameters[{p['id']}].default {d!r} is not one of the options {values}")
    return errs


def _unknowns(m):
    found = []
    if m.get("summary") == UNKNOWN:
        found.append("summary")
    if m.get("description") == UNKNOWN:
        found.append("description")
    for section in ("inputs", "outputs", "parameters"):
        for item in m.get(section, []):
            for field in ("description", "units", "requirements"):
                if item.get(field) == UNKNOWN:
                    found.append(f"{section}[{item['id']}].{field}")
    if m.get("runtime", {}).get("container") == UNKNOWN:
        found.append("runtime.container")
    return found


def validate(manifest, registry=None):
    """Return (errors, warnings). Errors block; warnings list 'unknown' values."""
    errors = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
              for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(manifest)]
    if errors:
        return errors, []
    for section in ("inputs", "outputs"):
        for item in manifest[section]:
            if item["datatype"] not in DATATYPE_NAMES:
                errors.append(f"{section}[{item['id']}].datatype {item['datatype']!r} is not a known datatype")
    for p in manifest["parameters"]:
        errors += _check_default(p)
    if registry is not None:
        config = registry.get("config") or {}
        reg_params = {k for k, c in config.items() if isinstance(c, dict) and c.get("type") not in ("input", "output")}
        man_params = {p["id"] for p in manifest["parameters"]}
        for k in sorted(reg_params - man_params):
            errors.append(f"registry config key {k!r} has no manifest parameter")
        for k in sorted(man_params - reg_params):
            errors.append(f"manifest parameter {k!r} is not in the registry config")
        reg_inputs = {i["id"] for i in registry.get("inputs", [])}
        if reg_inputs != {i["id"] for i in manifest["inputs"]}:
            errors.append(f"inputs differ from registry: {sorted(reg_inputs)}")
        reg_outputs = {o["id"] for o in registry.get("outputs", [])}
        if reg_outputs != {o["id"] for o in manifest["outputs"]}:
            errors.append(f"outputs differ from registry: {sorted(reg_outputs)}")
    warnings = [f"{w} is unknown" for w in _unknowns(manifest)]
    return errors, warnings


def about(manifest):
    """The GitHub About panel derived from a manifest."""
    result = {"description": manifest["summary"]}
    if manifest.get("doi"):
        result["homepage"] = "https://doi.org/" + manifest["doi"]
    result["topics"] = sorted({_topic(t) for t in manifest.get("topics", []) if _topic(t)})
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("record")
    g.add_argument("--main")
    v = sub.add_parser("validate")
    v.add_argument("manifest")
    v.add_argument("--registry")
    a = sub.add_parser("about")
    a.add_argument("manifest")
    args = ap.parse_args(argv)
    if args.cmd == "generate":
        record = json.loads(pathlib.Path(args.record).read_text())
        main_text = pathlib.Path(args.main).read_text() if args.main else None
        print(json.dumps(generate(record, main_text), indent=2))
        return 0
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    if args.cmd == "about":
        print(json.dumps(about(manifest), indent=2))
        return 0
    registry = json.loads(pathlib.Path(args.registry).read_text()) if args.registry else None
    errors, warnings = validate(manifest, registry)
    for e in errors:
        print("ERROR", e)
    for w in warnings:
        print("WARN ", w)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
