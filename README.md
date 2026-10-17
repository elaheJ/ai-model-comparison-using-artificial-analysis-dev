# Model Comparison Lab

## Open the student apps

- **[Model Lab](https://it344-model-lab.streamlit.app/)** — rank models and find similar alternatives across one or more features.
- **[Model Lab · Agent](https://it344-model-agent.streamlit.app/)** — the same comparison and similarity tools, plus a checked agent workflow.

Both use the bundled 704-model snapshot without an AA key. The cloud agent needs an instructor-configured LLM provider for actual AI runs; comparison, similarity, and the clearly labeled scripted rehearsal work without one.

Two runnable apps adapted from **My344-FA26-ArtificialAnalysis-Functions & LLM Agent.ipynb**:

| App | What it does | Requires an LLM? |
| --- | --- | --- |
| **Python Explorer** (`python_app.py`) | Load a snapshot, set requirements, rank models, inspect charts, and export reproducible results. | No |
| **Checked Agent** (`agent_app.py`) | Use the same comparison controls, then let a local LLM request tools. Python checks the sequence, inputs, selected model, and numeric evidence. | Yes for actual AI runs; a clearly labeled scripted rehearsal is also available. |

The default controller is the notebook's **Qwen2.5-1.5B-Instruct**, downloaded and run locally. No hosted LLM account or API key is needed for that mode. The notebook itself is unchanged and is not needed to run either app.

## Deploy from GitHub

**[Follow the deployment guide](DEPLOY.md)** to create two student-facing Streamlit apps from one GitHub repository:

- `python_app.py` — Python comparison and full-catalog similarity search.
- `cloud_agent_app.py` — the same comparison/similarity tools plus a checked hosted-LLM agent.

Both include the real **704-model AA teaching snapshot**, so comparison and similarity need no AA key. Actual cloud-agent inference requires provider settings in Streamlit Secrets. Local `agent_app.py` continues to default to Qwen. The GitHub Actions workflow tests both cloud entry points and produces a clean source ZIP.

## Start locally

Use Python **3.10–3.12** (3.12 recommended). Open a terminal in this folder.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
model-lab python
```

Windows PowerShell (activation is optional with these explicit paths):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\model-lab python
```

The Python app opens at **http://localhost:8501**. Stop it with Ctrl+C.

For the agent app, install the optional local-model dependencies and launch it:

```bash
python -m pip install -r requirements-local.txt
model-lab agent
```

On Windows, use `.\.venv\Scripts\python` and `.\.venv\Scripts\model-lab` in the preceding commands. The agent app opens at **http://localhost:8502**. Run both in separate terminals if desired. You can open the agent app without installing the optional requirements to use its comparison interface and scripted rehearsal.

Equivalent source commands, useful on hosting platforms:

```bash
python -m streamlit run python_app.py
python -m streamlit run agent_app.py --server.port 8502
```

The first **Run checked agent** with Local Qwen downloads roughly 3 GB of model files and loads them into memory. CUDA, Apple MPS, then CPU are selected automatically. CPU generation can be slow. The model is loaded lazily and reused for subsequent calls. Set `QWEN_CACHE_DIR` to a writable persistent location to keep the model across restarts; otherwise the notebook adapter uses the system temporary directory. No model files are bundled in this project.

Once the model has been cached, the local-model workflow can operate offline with an uploaded snapshot. The initial package installation and model download require internet access.

## Use the apps

1. Start with the **bundled real AA snapshot**, or upload your own JSON/CSV. A local `snapshots/aa_latest.json` overrides the bundle. Fictional demo data is available explicitly under Data.
2. Filter creators or search names, then select the exact model IDs to compare. Defaults select the first eight records. The Python app supports up to 1,000 records; an agent run is limited to 12 selected candidates to control context size.
3. Enter input/output token volumes and minimum quality, maximum first-token delay, and maximum workload cost. Optional first-answer and end-to-end limits are available.
4. Pick a single metric, or use weighted composite scoring. Composite presets can be adjusted with individual sliders.
5. Inspect the ranked table. Expand charts, measurements/exclusions, scoring, or exports only when needed. Switch to **Find similar models** for a separate full-catalog search.
6. In the agent app, select a controller and run it. Inspect the tool trace and verification result; a failed agent run never replaces Python's checked choice.

The agent chooses tool actions for the task defined in the form. It cannot reinterpret or loosen those requirements. It is not a general-purpose chatbot.

## Load a real notebook snapshot

After the notebook has downloaded `live_aa`, run this **in that notebook**:

```python
import json
from pathlib import Path
Path("aa_snapshot.json").write_text(
    json.dumps(live_aa, indent=2, allow_nan=False), encoding="utf-8"
)
```

Download that file from the notebook runtime, if needed, and upload it into either app. No API key is needed to compare an existing snapshot. The bundled real snapshot was subsequently downloaded through the AA API and retains its source, retrieval time, and index version.

Accepted JSON shapes:

- A notebook snapshot with `source`, `retrieved_at`, `intelligence_index_version`, and `models`.
- A complete API response with `data`. A paginated response with `has_more: true` is rejected to avoid silently comparing a partial download.
- A list of model records. Metadata that was not recorded is explicitly shown as unspecified.
- Nested Artificial Analysis records, or flat records with the CSV field names below.

CSV columns (see [the template](model_compare/data/snapshot_template.csv)):

```text
slug,name,creator,quality,input_price,output_price,ttft_s,first_answer_s,end_to_end_s,output_tokens_s
```

`slug` is required and must be unique. Prices are **USD per million tokens**, timing is **seconds**, and output speed is **tokens per second**. Blank numeric cells are missing, not zero. `name` defaults to the slug when the column is omitted. CSV source/date/version are unspecified; use JSON when preserving provenance. Do not supply precomputed `cost_usd`: cost is always recalculated from prices and your token counts.

Uploads are limited to 10 MB and 1,000 records. Invalid or negative numbers, booleans as numbers, duplicate IDs, and non-finite values are rejected. Only recognized fields are retained. Uploads are processed by the app's Python server in session memory; they are not automatically saved to disk. Hosted-controller mode additionally sends selected comparison data to that provider.

## Optional live data download

The apps use a minimal red, black, and white interface based on [Illinois State’s digital palette](https://designsystem.illinoisstate.edu/guidelines/color/) (brand red `#CC0000`). Data settings, requirements, charts, and audit details are collapsed by default.

Fetch real data in your terminal without saving the key:

```bash
model-lab fetch --prompt-key --output snapshots/aa_latest.json
```

Enter your key at the hidden prompt. Both apps prefer `snapshots/aa_latest.json` from their working directory when present; otherwise they use the bundled `model_compare/data/aa_snapshot.json`. Refresh the browser after a local download. Start the apps from this project folder. Set `AA_SNAPSHOT_PATH` to use a different default file. The raw local download is gitignored and excluded from the archive; the cleaned teaching copy in `model_compare/data/aa_snapshot.json` is included. See DEPLOY.md for refreshing it. Choose **Use fictional demo data** under Data to switch back temporarily.

If you have already exported your key as `AA_API_KEY`, omit `--prompt-key`. The older `ARTIFICIAL_ANALYSIS_API_KEY` name also works, with `AA_API_KEY` taking priority. Environment variables exported in a new terminal do not propagate into app servers already running in another terminal; the saved-snapshot command works without restarting them.

Alternatively, open **Data → Load or refresh snapshot**, enter your key in the password field, and click **Fetch latest AA snapshot**. The fetched snapshot stays in that browser session; use Download snapshot to save it. An uploaded file or explicit demo selection takes precedence over the fetched snapshot.

The apps are snapshot-first. You can also fetch to another filename using a configured key:

```bash
# Export AA_API_KEY in your terminal first.
model-lab fetch --output snapshots/aa_snapshot.json
```

The downloader reads up to ten pages, verifies a consistent Intelligence Index version and unique IDs, and records retrieval time. It uses the documented [Artificial Analysis free language-model endpoint](https://artificialanalysis.ai/data-api/docs/reference). Existing output files are not overwritten. Uploaded data never triggers a download. Keep private snapshots and keys out of a public repository; the `snapshots/` directory is gitignored.

## Download troubleshooting

The downloader adds the `certifi` CA bundle to Python’s default trust store, keeping hostname and certificate checks enabled. This also supports macOS Python installations whose default CA file is missing. TLS, DNS, timeout, and HTTP errors are reported separately without printing the key.

- **HTTP 401/403:** verify the Artificial Analysis key and API access.
- **TLS certificate verification:** update certifi (`python -m pip install --upgrade certifi`). If your network uses a custom certificate authority, configure `SSL_CERT_FILE` with its trusted CA bundle.
- **Could not resolve:** check your connection, DNS, or VPN.
- **Timed out:** retry when connectivity is restored.

## Scoring and notebook functions

All ten functions remain named and inspectable in [core.py](model_compare/core.py):

| Notebook | Function | Role |
| --- | --- | --- |
| Q1 | `has_measurement` | Distinguish missing values from real zero |
| Q2 | `read_metric` | Read nested fields, including null sections |
| Q3 | `models_for_slugs` | Select exact model IDs |
| Q4 | `workload_cost` | Calculate input plus output cost |
| Q5 | `meets_limits` | Enforce quality, latency, and cost constraints |
| Q6 | `choose_model` | Original cost/latency choice, with slug tie-break |
| Q7 | `valid_tool_call` | Validate tool name and argument shape |
| Q8 | `can_continue` | Enforce the call budget |
| Q9 | `record_trace` | Preserve requests/results; now deep-copied |
| Q10 | `check_recommendation` | Verify status and exact chosen ID |

Extensions include `rank_models`, `pareto_front`, `find_similar_models`, `similar_models`, timing constraints, provenance fingerprints, CSV/JSON import/export, and numeric-evidence verification. The notebook's `similar` helper sorted distances descending; the app returns nearest distances first.

For a composite, apply all requirements first and exclude candidates missing a positive-weight metric. Normalize each active metric across the remaining candidates:

- Higher is better: `utility = (value - min) / (max - min)`.
- Lower is better: `utility = 1 - (value - min) / (max - min)`.
- Constant metric: utility is 1 for everyone, contributing equally.
- `score = 100 * sum(weight * utility) / sum(weights)`.

Zero-weight metrics are ignored. At least one weight must be positive. All candidates still need quality, TTFT, and cost to pass the notebook's three base requirements. Ties use exact model ID ascending. Single-metric rankings use the original values, not rounded scores. Single-metric tables also show a 0–100 relative utility score for consistency.

Changing candidates or limits changes normalization bounds; composite scores are not comparable across different runs. The exported JSON includes bounds and per-metric contributions. The Pareto chart uses its two displayed metrics across all selected candidates, including excluded models, and marks eligibility separately.

Benchmark quality is a proxy, not application-specific evaluation. Prices do not include discounts/caching, and output counts should include billed reasoning tokens. Changing token volume changes estimated cost, not measured benchmark latency. First-token, first-answer, and end-to-end times are different measurements.

## Find similar models

Select **Find similar models** at the top of either app. Choose a reference model and one or more features: workload cost, TTFT, intelligence, first-answer delay, end-to-end time, output speed, or input/output prices. The search covers **every model in the loaded snapshot**, independent of ranking candidates or limits. It also works when no ranking candidates are selected.

All comparable models appear, ordered closest first; there is no top-five cutoff. Raise **Minimum similarity (%)** to show only closer matches. The table includes each feature’s value and signed difference from the reference. Expand the method section to inspect missing-data exclusions and normalization bounds. Download the full results, method, source, snapshot fingerprint, and workload as JSON.

For each feature, `d = abs(candidate - reference) / (snapshot_max - snapshot_min)`. A constant feature has distance zero. Combine selected features with an equally weighted root mean square: `distance = sqrt(mean(d²))`, and `similarity = 100 * (1 - distance)`. A score of 100 means identical values on the selected features; it does not mean a model is better. Different units cannot dominate simply because one metric has larger numeric values. Ranges include all available measurements for each feature; outliers can compress distances. Scores depend on this snapshot and chosen feature set.

A candidate missing any selected feature is excluded and counted. If the reference is missing a selected feature, the app asks you to change the reference or features. Real zero values remain valid. Ties sort by model ID. Cost similarity uses your sidebar workload; choosing input/output prices instead compares unit rates.

Python API:

```python
from model_compare.core import comparison_rows, find_similar_models
rows = comparison_rows(snapshot, [m["slug"] for m in snapshot["models"]], 100_000, 20_000)
report = find_similar_models(rows, "your-model-slug", ["cost_usd", "ttft_s"], min_similarity=80)
# report["matches"] contains every qualifying neighbor, ordered closest first.
```

## Agent controls and verification

The controller must request `fetch_metrics` (loaded-snapshot metadata), `compare_models` (the exact task), then `estimate_cost` if there is a winner. It gets **four tool attempts**, with rejected requests consuming attempts. A final answer is accepted only after all required steps and matching status, ID, and numeric evidence. A no-feasible-model result requires a null ID and empty evidence.

The reason text is displayed as **unverified explanation**: matching structured evidence does not validate every sentence. Small local models can fail; the app reports this and retains the trace. A scripted rehearsal is clearly labeled and never represented as an LLM run. Changing snapshot, token counts, constraints, or weights invalidates the displayed agent result. Generated code is never executed.

Optional controllers:

- **Ollama:** install [Ollama](https://ollama.com), run `ollama pull qwen2.5:1.5b`, and select Ollama in the app. Its [chat API](https://docs.ollama.com/api/chat) must be available on the machine running the app. Override `OLLAMA_HOST` in server settings if needed.
- **Hosted API:** configure `LLM_BASE_URL` to an HTTPS base URL supporting `/chat/completions`, and `LLM_MODEL` to a supported model ID. Supply a session key through the password field, or configure `LLM_API_KEY` on the server. Provider/model compatibility varies; the adapter uses JSON action messages. Requests have a 180-second timeout per turn. This path is optional and was not exercised against a paid provider during development.

A public hosted app cannot use Ollama on a visitor's computer. Local Qwen runs on the **app server**, so hosting it requires enough memory and compute. The bundled Docker image contains the basic apps only; use a hosted controller or a reachable Ollama service with that image, or extend it with local-model dependencies and a persistent model cache.

## Share from GitHub

Use [DEPLOY.md](DEPLOY.md) for the exact repository layout, two entry points, cloud-agent secrets, and snapshot refresh steps. GitHub holds the code; Streamlit Community Cloud runs it. GitHub Pages does not run these Python servers.

The source release contains the real teaching snapshot and the full similarity tools in both apps. No repository or hosted deployment is created automatically. After deployment, add the two returned Streamlit URLs to this README for students.

Docker alternative:

```bash
docker build -t model-lab .
docker run --rm -p 8501:8501 model-lab
# Agent UI with a hosted provider configured in .env:
docker run --rm -p 8502:8501 --env-file .env model-lab \
  python -m streamlit run cloud_agent_app.py --server.address=0.0.0.0 --server.port=8501
```

## Command-line comparison and tests

```bash
model-lab compare --task task.example.json --output result.json
# Use your own data:
model-lab compare --snapshot aa_snapshot.json --task task.json --output result.json
python -m pip install -e '.[dev]'
python -m pytest -q
```

Tests cover notebook functions, weighted arithmetic, ties, missing data, snapshot parsing, changed workloads, no-feasible-model cases, agent rejection/recovery/budgets, fabricated evidence, and both Streamlit interfaces. CI runs on Python 3.10 and 3.12. Local Qwen inference and live external APIs require their optional dependencies/service access and are separate from the offline test suite.

Project layout: `core.py` holds calculations; `snapshots.py` handles data; `agent.py` enforces the agent workflow; `local_qwen.py` preserves the notebook's lazy Qwen adapter; `ui.py` supplies the shared UI; `cli.py` provides installable launch/download/compare commands.
