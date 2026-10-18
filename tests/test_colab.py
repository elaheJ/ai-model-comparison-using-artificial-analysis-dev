"""Colab UI wiring, credentials, exports and executable notebook structure."""
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import nbformat
import pytest

from model_compare import colab_ui as ui
from model_compare.snapshots import default_snapshot, demo_snapshot


@pytest.fixture
def userdata(monkeypatch):
    module = SimpleNamespace(
        SecretNotFoundError=type("SecretNotFoundError", (Exception,), {}),
        NotebookAccessError=type("NotebookAccessError", (Exception,), {}),
        get=None)
    monkeypatch.setitem(sys.modules, "google.colab", SimpleNamespace(userdata=module))
    return module


def test_key_is_not_retained_and_failed_refresh_has_no_fallback(monkeypatch, capsys, userdata):
    sentinel = "private-test-key"
    def read_secret(name):
        assert name == "AA_API_KEY"
        return "  " + sentinel + "  "
    userdata.get = read_secret
    def fail(key):
        assert key == sentinel
        raise RuntimeError("request included " + key)
    monkeypatch.setattr(ui, "fetch_artificial_analysis", fail)
    assert ui.load_colab_snapshot() is None
    assert sentinel not in capsys.readouterr().out
    snapshot = demo_snapshot()
    monkeypatch.setattr(ui, "fetch_artificial_analysis", lambda key: snapshot)
    assert ui.load_colab_snapshot() == snapshot
    assert sentinel not in capsys.readouterr().out
    assert sentinel not in repr(vars(ui))


@pytest.mark.parametrize("failure, message", [
    ("missing", "Add AA_API_KEY"), ("denied", "Enable Notebook access"),
    ("empty", "AA_API_KEY is empty"), ("timeout", "Could not read Colab Secrets")])
def test_secret_setup_errors_never_fetch_data(monkeypatch, capsys, userdata, failure, message):
    def read_secret(name):
        if failure == "empty":
            return "  "
        error = {"missing": userdata.SecretNotFoundError, "denied": userdata.NotebookAccessError,
                 "timeout": TimeoutError}[failure]
        raise error("sensitive-test-details")
    userdata.get = read_secret
    monkeypatch.setattr(ui, "fetch_artificial_analysis", lambda key: pytest.fail("Must not fetch without a secret"))
    assert ui.load_colab_snapshot() is None
    output = capsys.readouterr().out
    assert message in output
    assert "sensitive-test-details" not in output


@pytest.mark.parametrize("agent", [False, True])
def test_real_ui_callback_wiring_and_exports(agent):
    snapshot = default_snapshot()
    app = ui.build_app(snapshot, agent)
    callbacks = {fn.fn.__name__: fn.fn for fn in app.fns.values()}
    # Use actual dropdown defaults, and ensure widget ordering matches callback args.
    compare_dep = next(fn for fn in app.fns.values() if fn.fn.__name__ == "compare_click")
    values = [component.value for component in compare_dep.inputs]
    values[6] = "composite"
    status, frame, figure, result, csv_file, json_file = callbacks["compare_click"](*values)
    assert len(frame) > 0
    assert result["winner"]["slug"] == frame.iloc[0]["Model ID"]
    assert result["comparison"]["constraints"]["objective"] == "composite"
    assert json.loads(Path(json_file).read_text())["winner"] == result["winner"]
    assert Path(csv_file).read_text().startswith("Model,Model ID")
    assert figure is not None
    if agent:
        checked = callbacks["agent_click"](*values, "rehearsal")
        assert checked[3]["agent"]["completed"]
        assert "no LLM" in checked[0]
    values[0] = []
    invalid = callbacks["compare_click"](*values)
    assert invalid[1].empty and invalid[3] == {} and invalid[4] is None


def test_similarity_full_catalog_and_missing_data():
    snapshot = default_snapshot()
    output = ui.similarity_outputs(snapshot, "glm-4-5v", ["cost_usd", "ttft_s"], 0, 100_000, 20_000)
    status, reference, frame, result, csv_file, json_file = output
    assert len(frame) > 100  # No shortlist/top-k truncation.
    assert reference.iloc[0]["Model ID"] == "glm-4-5v"
    assert "Δ Workload cost ($)" in frame.columns
    assert len(result["matches"]) + len(result["excluded"]) == len(snapshot["models"]) - 1
    assert frame["Similarity %"].is_monotonic_decreasing
    assert json.loads(Path(json_file).read_text())["snapshot_id"] == snapshot["snapshot_id"]
    with pytest.raises(ValueError, match="one or more"):
        ui.similarity_outputs(snapshot, "glm-4-5v", [], 0, 100_000, 20_000)
    with pytest.raises(ValueError, match="whole numbers"):
        ui.similarity_outputs(snapshot, "glm-4-5v", ["cost_usd"], 0, 0.5, 20_000)


def test_notebooks_clean_compilable_and_secrets_before_launch():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "colab").glob("*.ipynb"))
    assert len(paths) == 2
    for path in paths:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        code = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
        for cell in notebook.cells:
            if cell.cell_type == "code":
                assert cell.outputs == [] and cell.execution_count is None
                compile(cell.source, str(path), "exec")
        assert "load_colab_snapshot()" in code[1]
        text = "\n".join(cell.source for cell in notebook.cells)
        assert "Notebook access" in text and "Colab Secrets" in text
        assert "hidden prompt" not in text and "getpass" not in text
        assert "snapshot = None" in code[1]
        assert "launch_app(snapshot" in code[-1]
        assert "gradio==6.0.2" in code[0]
        assert ("transformers==4.57.6" in code[0]) == ("Agent" in path.name)
