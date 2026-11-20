from scriptgap.common import ROOT, SCRIPTS, TASK_TYPES, read_jsonl, suggest_reply_lang
from scriptgap.score import stratified_sample
from scriptgap.stats import bootstrap_ci, cohen_kappa, sign_test_p
from scriptgap.validate import progress, validate


def group(g="fact-01", t="factual", **over):
    rows = [
        {"script": "roman_urdu", "prompt": "Nazm Shikwa kis ne likhi?"},
        {"script": "nastaliq", "prompt": "نظم شکوہ کس نے لکھی؟"},
        {"script": "english", "prompt": "Who wrote Shikwa?"},
    ]
    out = []
    for r in rows:
        row = {"item_id": f"{g}.{r['script']}", "task_type": t, "gold": "Iqbal",
               "parallel_group": g, "author": "tania", "built_on": "2026-11-21", **r}
        out.append(row)
    return out


def test_valid_group_has_no_errors():
    errors, warnings = validate(group())
    assert errors == []
    assert warnings  # fewer than 10 groups per type


def test_spec_style_shared_item_id_is_rejected():
    rows = group()
    for r in rows:
        r["item_id"] = "fact-01"
    errors, _ = validate(rows)
    assert any("unique" in e for e in errors)


def test_missing_script_and_wrong_script_detected():
    rows = group()[:2]
    rows[1]["prompt"] = "Nazm Shikwa kis ne likhi?"  # Latin text labelled nastaliq
    errors, _ = validate(rows)
    assert any("needs exactly one of each" in e for e in errors)
    assert any("Arabic-script" in e for e in errors)


def test_progress_counts_only_complete_groups():
    rows = group("fact-01") + group("reason-01", t="reasoning")[:2]  # second group unfinished
    line = progress(rows)
    assert line.startswith("5 of 120 rows; 1 of 40 parallel groups complete")
    assert "factual 1/10" in line and "reasoning 0/10" in line
    assert progress([]).startswith("0 of 120 rows; 0 of 40")


def test_template_fills_into_a_valid_full_dataset():
    rows = read_jsonl(ROOT / "data" / "TEMPLATE.jsonl")
    assert len(rows) == 120
    assert all(r["prompt"] == r["gold"] == r["author"] == r["built_on"] == "" for r in rows)
    for r in rows:  # what the author will do: fill every blank
        r["prompt"] = "یہ ایک سوال ہے" if r["script"] == "nastaliq" else "a question"
        r.update(gold="x", author="tania", built_on="2026-11-21")
    errors, warnings = validate(rows)
    assert errors == [] and warnings == []
    assert {r["task_type"] for r in rows} == set(TASK_TYPES)
    assert {r["script"] for r in rows} == set(SCRIPTS)


def test_reply_lang_heuristic():
    assert suggest_reply_lang("Yeh nazm Allama Iqbal ne likhi thi aur bohat mashhoor hai.") == "r"
    assert suggest_reply_lang("The poem was written by Allama Iqbal in 1909.") == "e"
    assert suggest_reply_lang("یہ نظم علامہ اقبال نے لکھی تھی۔") == "n"
    assert suggest_reply_lang("") == "x"


def test_kappa():
    assert cohen_kappa([0, 1, 2, 2], [0, 1, 2, 2], weights="quadratic") == 1.0
    k = cohen_kappa([0, 1, 2, 2, 1, 0], [0, 2, 2, 1, 1, 0], weights="quadratic")
    assert 0 < k < 1
    assert cohen_kappa(list("eerr"), list("eerr")) == 1.0


def test_sign_test_and_bootstrap():
    assert sign_test_p([0.5] * 10) < 0.01
    assert sign_test_p([0.5, -0.5] * 5) == 1.0
    assert sign_test_p([0, 0, 0]) == 1.0
    lo, hi = bootstrap_ci([0.5] * 8 + [0.0] * 2)
    assert 0 < lo <= 0.4 <= hi <= 0.5


def test_stratified_sample_covers_every_cell():
    rows = [{"model": m, "script": s, "id": i}
            for m in "abc" for s in ("english", "nastaliq", "roman_urdu") for i in range(40)]
    picked = stratified_sample(rows, 45, seed=1)
    assert len(picked) == 45
    cells = {(r["model"], r["script"]) for r in picked}
    assert len(cells) == 9
