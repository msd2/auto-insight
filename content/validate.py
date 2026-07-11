#!/usr/bin/env python3
"""Validate insight pack content files.

Checks every pack version file under content/packs/<slug>/v<N>.json:

1. JSON Schema validation against content/schema/pack.schema.json
   (skipped with a clear notice if the `jsonschema` package is not
   installed -- e.g. run `uv run --with jsonschema python3 content/validate.py`
   or `pip install jsonschema` for full validation).
2. Referential integrity and semantic rules that JSON Schema cannot
   express (these always run, stdlib only):
   - slug matches the directory name, version matches the file name
   - question ids and block ids are unique
   - every insight_spec block references only manifest question ids
   - chart kinds are appropriate to question types
     (theme_list / quote_list <- free_text only; other kinds <- no free_text)
   - metric_tile `measure` is appropriate to its question type, and
     option_share's `option_label` exists in the question's options
   - sample_dataset.questions covers every manifest question, exactly
   - aggregate shape matches question type; distribution labels match the
     question's options / scale labels; counts arithmetic is consistent
     with response_count; NPS `score` matches the bucket counts
   - every box-office cut used by a block exists in sample_dataset.cuts
     (and vice versa), and each segment covers that block's questions
   - example_themes present if and only if a theme_list block exists

Exits 0 if everything passes, 1 otherwise.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "pack.schema.json"
PACKS_DIR = ROOT / "packs"

LIKERT_5_DEFAULT = [
    "Strongly disagree",
    "Disagree",
    "Neither agree nor disagree",
    "Agree",
    "Strongly agree",
]
LIKERT_7_DEFAULT = [
    "Strongly disagree",
    "Disagree",
    "Somewhat disagree",
    "Neither agree nor disagree",
    "Somewhat agree",
    "Agree",
    "Strongly agree",
]

TEXT_KINDS = {"theme_list", "quote_list"}
QUANT_KINDS = {"metric_tile", "bar", "stacked_bar", "line", "distribution"}
LIKERT_TYPES = {"likert_5", "likert_7"}
CHOICE_TYPES = {"single_choice", "multi_choice", "demographic"}
SHARE_TOLERANCE = 0.02


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def expected_labels(question: dict) -> list[str] | None:
    qtype = question["type"]
    if qtype in CHOICE_TYPES:
        return question.get("options")
    if qtype == "likert_5":
        return question.get("scale_labels", LIKERT_5_DEFAULT)
    if qtype == "likert_7":
        return question.get("scale_labels", LIKERT_7_DEFAULT)
    return None


def check_distribution(
    errors: list[str],
    where: str,
    agg: dict,
    question: dict,
    cap: int,
) -> None:
    """Shared checks for a distribution aggregate against its question.

    `cap` is the maximum number of respondents the aggregate may represent
    (response_count at the top level, segment n inside a cut).
    """
    labels = agg.get("labels", [])
    counts = agg.get("counts", [])
    if len(labels) != len(counts):
        errors.append(f"{where}: labels ({len(labels)}) and counts ({len(counts)}) differ in length")
    expected = expected_labels(question)
    if expected is not None and labels != expected:
        errors.append(
            f"{where}: labels do not match the question's "
            f"{'options' if question['type'] in CHOICE_TYPES else 'scale labels'}: "
            f"{labels!r} != {expected!r}"
        )
    total = sum(counts)
    answered = agg.get("answered")
    if question["type"] == "multi_choice":
        if answered is None:
            errors.append(f"{where}: multi_choice aggregates must declare 'answered'")
        else:
            if answered > cap:
                errors.append(f"{where}: answered ({answered}) exceeds respondent cap ({cap})")
            over = [c for c in counts if c > answered]
            if over:
                errors.append(f"{where}: option count(s) {over} exceed answered ({answered})")
    else:
        if total > cap:
            errors.append(f"{where}: counts sum to {total}, exceeding respondent cap ({cap})")
        if answered is not None and answered != total:
            errors.append(f"{where}: answered ({answered}) != sum of counts ({total})")


def check_nps(errors: list[str], where: str, agg: dict, cap: int) -> None:
    buckets = agg.get("counts_by_score", {})
    total = sum(buckets.values())
    if total > cap:
        errors.append(f"{where}: NPS responses sum to {total}, exceeding respondent cap ({cap})")
    if total > 0:
        promoters = buckets.get("9", 0) + buckets.get("10", 0)
        detractors = sum(buckets.get(str(s), 0) for s in range(0, 7))
        expected = round_half_up(100 * (promoters - detractors) / total)
        if agg.get("score") != expected:
            errors.append(
                f"{where}: score {agg.get('score')} does not match buckets "
                f"(expected {expected}: {promoters} promoters, {detractors} detractors, {total} total)"
            )


def validate_pack(path: Path, schema_validator) -> list[str]:
    errors: list[str] = []
    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"not valid JSON: {exc}"]

    # -- 1. JSON Schema -----------------------------------------------------
    if schema_validator is not None:
        for err in schema_validator.iter_errors(pack):
            loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"schema: at {loc}: {err.message}")
        if errors:
            # Structural problems make the semantic checks noisy/unreliable.
            return errors

    # -- 2. File layout -----------------------------------------------------
    slug = pack.get("slug")
    if slug != path.parent.name:
        errors.append(f"slug '{slug}' does not match directory name '{path.parent.name}'")
    m = re.fullmatch(r"v(\d+)\.json", path.name)
    if not m:
        errors.append(f"file name '{path.name}' is not of the form v<version>.json")
    elif pack.get("version") != int(m.group(1)):
        errors.append(f"version {pack.get('version')} does not match file name '{path.name}'")

    # -- 3. Manifest --------------------------------------------------------
    manifest = pack.get("question_manifest", [])
    questions = {q.get("id"): q for q in manifest if isinstance(q, dict)}
    ids = [q.get("id") for q in manifest if isinstance(q, dict)]
    for dup in {i for i in ids if ids.count(i) > 1}:
        errors.append(f"duplicate question id '{dup}'")
    for q in manifest:
        st = q.get("scale_labels")
        if st is not None:
            want = 5 if q.get("type") == "likert_5" else 7
            if len(st) != want:
                errors.append(f"question '{q.get('id')}': scale_labels has {len(st)} labels, expected {want}")

    # -- 4. Insight spec ----------------------------------------------------
    spec = pack.get("insight_spec", {})
    blocks = spec.get("blocks", [])
    block_ids = [b.get("id") for b in blocks if isinstance(b, dict)]
    for dup in {i for i in block_ids if block_ids.count(i) > 1}:
        errors.append(f"duplicate block id '{dup}'")

    cuts_used: set[str] = set()
    has_theme_list = False
    for b in blocks:
        bid = b.get("id", "?")
        kind = b.get("kind")
        qids = b.get("question_ids", [])
        missing = [qid for qid in qids if qid not in questions]
        if missing:
            errors.append(f"block '{bid}': unknown question id(s) {missing}")
            continue
        qtypes = {qid: questions[qid]["type"] for qid in qids}
        if kind in TEXT_KINDS:
            bad = [qid for qid, t in qtypes.items() if t != "free_text"]
            if bad:
                errors.append(f"block '{bid}' ({kind}): non-free_text question(s) {bad}")
            if kind == "theme_list":
                has_theme_list = True
        elif kind in QUANT_KINDS:
            bad = [qid for qid, t in qtypes.items() if t == "free_text"]
            if bad:
                errors.append(f"block '{bid}' ({kind}): free_text question(s) {bad} — use theme_list/quote_list")
        if kind == "metric_tile":
            measure = b.get("measure")
            if len(qids) != 1:
                errors.append(f"block '{bid}': metric_tile must reference exactly one question")
            elif measure:
                qid = qids[0]
                qtype = qtypes[qid]
                if measure == "nps" and qtype != "nps":
                    errors.append(f"block '{bid}': measure 'nps' on non-nps question '{qid}'")
                if measure in {"mean", "top_two_box_share"} and qtype not in LIKERT_TYPES:
                    errors.append(f"block '{bid}': measure '{measure}' on non-likert question '{qid}'")
                if measure == "option_share":
                    if qtype not in CHOICE_TYPES:
                        errors.append(f"block '{bid}': measure 'option_share' on non-choice question '{qid}'")
                    elif b.get("option_label") not in questions[qid].get("options", []):
                        errors.append(
                            f"block '{bid}': option_label {b.get('option_label')!r} "
                            f"is not an option of question '{qid}'"
                        )
        cut = b.get("cut", "none")
        if cut != "none":
            cuts_used.add(cut)

    # -- 5. Sample dataset --------------------------------------------------
    ds = pack.get("sample_dataset", {})
    response_count = ds.get("response_count", 0)
    ds_questions = ds.get("questions", {})

    missing = sorted(set(questions) - set(ds_questions))
    if missing:
        errors.append(f"sample_dataset missing aggregates for question(s) {missing}")
    extra = sorted(set(ds_questions) - set(questions))
    if extra:
        errors.append(f"sample_dataset has aggregates for unknown question(s) {extra}")

    def check_aggregate(where: str, qid: str, agg: dict, cap: int, allow_free_text: bool) -> None:
        question = questions[qid]
        qtype = question["type"]
        atype = agg.get("type")
        if qtype == "nps":
            if atype != "nps":
                errors.append(f"{where}: question '{qid}' is nps but aggregate type is '{atype}'")
            else:
                check_nps(errors, where, agg, cap)
        elif qtype == "free_text":
            if not allow_free_text:
                errors.append(f"{where}: free_text question '{qid}' cannot appear in a cut segment")
            elif atype != "free_text":
                errors.append(f"{where}: question '{qid}' is free_text but aggregate type is '{atype}'")
            elif agg.get("answered", 0) > cap:
                errors.append(f"{where}: answered ({agg.get('answered')}) exceeds respondent cap ({cap})")
        else:
            if atype != "distribution":
                errors.append(f"{where}: question '{qid}' is {qtype} but aggregate type is '{atype}'")
            else:
                check_distribution(errors, where, agg, question, cap)

    for qid, agg in ds_questions.items():
        if qid in questions and isinstance(agg, dict):
            check_aggregate(f"sample_dataset.questions.{qid}", qid, agg, response_count, True)

    # -- 6. Cuts ------------------------------------------------------------
    ds_cuts = ds.get("cuts", {})
    for cut in sorted(cuts_used - set(ds_cuts)):
        errors.append(f"insight_spec uses cut '{cut}' but sample_dataset.cuts has no entry for it")
    for cut in sorted(set(ds_cuts) - cuts_used):
        errors.append(f"sample_dataset.cuts.{cut} is not used by any insight block")

    for cut_key, cut in ds_cuts.items():
        segments = cut.get("segments", [])
        total_n = sum(s.get("n", 0) for s in segments)
        if total_n > response_count:
            errors.append(f"cuts.{cut_key}: segment n sums to {total_n}, exceeding response_count ({response_count})")
        share_sum = sum(s.get("share", 0) for s in segments)
        if abs(share_sum - 1.0) > SHARE_TOLERANCE:
            errors.append(f"cuts.{cut_key}: segment shares sum to {share_sum:.2f}, expected ~1.0")
        needed = {
            qid
            for b in blocks
            if b.get("cut", "none") == cut_key
            for qid in b.get("question_ids", [])
        }
        seg_keys = [s.get("key") for s in segments]
        for dup in {k for k in seg_keys if seg_keys.count(k) > 1}:
            errors.append(f"cuts.{cut_key}: duplicate segment key '{dup}'")
        for seg in segments:
            skey = seg.get("key", "?")
            where = f"cuts.{cut_key}.{skey}"
            n = seg.get("n", 0)
            if total_n > 0 and abs(seg.get("share", 0) - n / total_n) > SHARE_TOLERANCE:
                errors.append(
                    f"{where}: share {seg.get('share')} inconsistent with n={n} of {total_n} "
                    f"(expected ~{n / total_n:.2f})"
                )
            seg_questions = seg.get("questions", {})
            for qid in sorted(needed - set(seg_questions)):
                errors.append(f"{where}: missing aggregate for question '{qid}' required by a '{cut_key}' block")
            for qid, agg in seg_questions.items():
                if qid not in questions:
                    errors.append(f"{where}: aggregate for unknown question '{qid}'")
                elif isinstance(agg, dict):
                    check_aggregate(f"{where}.questions.{qid}", qid, agg, n, False)

    # -- 7. Themes ----------------------------------------------------------
    has_example_themes = bool(ds.get("example_themes"))
    if has_theme_list and not has_example_themes:
        errors.append("insight_spec has a theme_list block but sample_dataset.example_themes is missing")
    if has_example_themes and not has_theme_list:
        errors.append("sample_dataset.example_themes present but no theme_list block uses it")

    return errors


def main() -> int:
    schema_validator = None
    schema_note = ""
    try:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        schema_validator = jsonschema.Draft202012Validator(schema)
        from importlib.metadata import version as _pkg_version

        schema_note = "schema validation: ON (jsonschema %s)" % _pkg_version("jsonschema")
    except ImportError:
        schema_note = (
            "schema validation: SKIPPED — the 'jsonschema' package is not installed.\n"
            "  Integrity checks still run. For full validation:\n"
            "    uv run --with jsonschema python3 content/validate.py\n"
            "  or: pip install jsonschema"
        )

    pack_files = sorted(PACKS_DIR.glob("*/v*.json"))
    if not pack_files:
        print(f"ERROR: no pack files found under {PACKS_DIR}", file=sys.stderr)
        return 1

    print(schema_note)
    failed = False
    for path in pack_files:
        rel = path.relative_to(ROOT)
        errors = validate_pack(path, schema_validator)
        if errors:
            failed = True
            print(f"FAIL  {rel}")
            for e in errors:
                print(f"      - {e}")
        else:
            print(f"OK    {rel}")

    if failed:
        print("\nValidation FAILED")
        return 1
    print(f"\nValidation passed: {len(pack_files)} pack file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
