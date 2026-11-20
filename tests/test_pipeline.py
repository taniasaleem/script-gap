"""End to end on synthetic data: validate -> run -> score pass1 and pass2 ->
agreement -> analyze, with a fake provider in place of real models and a
scripted rater in place of a person.

The fake models answer every Roman Urdu prompt wrongly and every other prompt
correctly, so the analysis must report a +100 point gap for both comparisons.
That pins the pairing logic, not just "the commands ran".
"""
import json

import pytest

from scriptgap import agreement, analyze, run, score
from scriptgap.common import TASK_TYPES, read_jsonl

GROUPS_PER_TYPE = 2
# RUBRIC.md, "Which dimensions apply to which task type". Written out here, not
# imported from score.py, so the test catches score.py drifting from the rubric.
RUBRIC_DIMENSIONS = {
    "factual": {"correctness"},
    "instruction": {"correctness", "compliance"},
    "reasoning": {"correctness"},
    "abstention": {"abstention"},
}
CFG = {
    "samples": 1,
    "models": [
        {"name": "model-a", "provider": "fake", "model": "a-1"},
        {"name": "model-b", "provider": "fake", "model": "b-1"},
    ],
}


def synthetic_items():
    rows = []
    for t in TASK_TYPES:
        for i in range(1, GROUPS_PER_TYPE + 1):
            g = f"{t}-{i:02d}"
            for script, prompt in (("roman_urdu", f"ru sawal {g}"),
                                   ("nastaliq", "یہ ایک سوال ہے"),
                                   ("english", f"en question {g}")):
                rows.append({"item_id": f"{g}.{script}", "parallel_group": g,
                             "task_type": t, "script": script, "prompt": prompt,
                             "gold": "RIGHT", "author": "test", "built_on": "2026-11-20"})
    return rows


def fake_provider(cfg, prompt):
    answer = "WRONG answer" if prompt.startswith("ru ") else "RIGHT answer"
    return {"response": answer, "model_version": f"{cfg['model']}-served",
            "stop_reason": "end_turn", "usage": {}, "params": {}}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    data = tmp_path / "items.jsonl"
    runs, scores = tmp_path / "runs", tmp_path / "scores"
    for mod in (run, score):
        monkeypatch.setattr(mod, "DATA", data)
    for mod in (run, score, analyze):
        monkeypatch.setattr(mod, "RUNS_DIR", runs)
    for mod in (score, agreement, analyze):
        monkeypatch.setattr(mod, "SCORES_DIR", scores)
    for mod in (agreement, analyze):
        monkeypatch.setattr(mod, "OUT_DIR", tmp_path)
    for mod in (run, analyze):
        monkeypatch.setattr(mod, "load_config", lambda: CFG)
    monkeypatch.setitem(run.PROVIDERS, "fake", fake_provider)
    return tmp_path


def scripted_rater(capsys):
    """Stands in for input(): reads the response the scorer just printed and
    scores it 2 if it says RIGHT, 0 otherwise. Accepts the suggested reply
    language and leaves the note empty."""
    state = {"response": ""}

    def rater(prompt=""):
        shown = capsys.readouterr().out
        if "RESPONSE:" in shown:
            state["response"] = shown.rsplit("RESPONSE:", 1)[1]
        if prompt.startswith(("Correctness", "Compliance", "Abstention")):
            return "2" if "RIGHT" in state["response"] else "0"
        return ""

    return rater


def test_pipeline_end_to_end(workspace, monkeypatch, capsys):
    items = synthetic_items()
    (workspace / "items.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items), encoding="utf-8")

    assert run.main(["--run-id", "t1"]) == 0
    responses = read_jsonl(workspace / "runs" / "t1.jsonl")
    assert len(responses) == len(items) * len(CFG["models"])
    assert not any(r.get("error") for r in responses)

    monkeypatch.setattr("builtins.input", scripted_rater(capsys))
    assert score.main(["--run-id", "t1", "--pass", "pass1"]) == 0
    assert score.main(["--run-id", "t1", "--pass", "pass2", "--sample", "6"]) == 0
    pass1 = read_jsonl(workspace / "scores" / "t1.pass1.jsonl")
    pass2 = read_jsonl(workspace / "scores" / "t1.pass2.jsonl")
    assert len(pass1) == len(responses)
    for s in pass1:
        scored = {d for d in ("correctness", "compliance", "abstention") if d in s}
        assert scored == RUBRIC_DIMENSIONS[s["task_type"]], s["item_id"]
    assert len(pass2) == 6
    assert len({(s["model"], s["script"]) for s in pass2}) == 6  # every cell rechecked

    assert agreement.main(["--run-id", "t1"]) == 0
    assert "| correctness | " in (workspace / "agreement.md").read_text(encoding="utf-8")

    assert analyze.main(["--run-id", "t1"]) == 0
    summary = (workspace / "summary.md").read_text(encoding="utf-8")
    n_groups = GROUPS_PER_TYPE * len(TASK_TYPES)
    # Both comparisons, both models: every group pairs a right answer with a wrong one.
    assert summary.count(f"+100.0 [+100.0, +100.0] (n={n_groups}, ties=0") == 4
    assert "a-1-served" in summary and "b-1-served" in summary
    assert (workspace / "gap_by_task_type.png").stat().st_size > 0
    assert (workspace / "english_switch.png").stat().st_size > 0


def test_run_refuses_an_empty_dataset(workspace):
    (workspace / "items.jsonl").write_text("", encoding="utf-8")
    assert run.main(["--run-id", "t1"]) == 1
    assert not (workspace / "runs" / "t1.jsonl").exists()
