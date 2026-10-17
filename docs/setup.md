# Setup for instructors and maintainers

[Back to the quick start](../README.md)

## Hosting

Deploy this repository twice on [Streamlit Community Cloud](https://share.streamlit.io), using branch `main` and Python 3.12:

| App | Entry point | Current URL |
| --- | --- | --- |
| Comparison | `python_app.py` | [Model Lab](https://it344-model-lab.streamlit.app/) |
| Agent | `cloud_agent_app.py` | [Model Lab · Agent](https://it344-model-agent.streamlit.app/) |

Keep the launch files at the repository root. Streamlit installs `requirements.txt` and redeploys when you push changes. GitHub stores the source; GitHub Pages cannot run these Python apps.

## Fresh AA data

Add this in **Settings → Secrets for each deployment**, using your real key:

```toml
AA_API_KEY = "your-instructor-aa-key"
```

Students never enter an AA key. On first use, each server downloads data and shares a six-hour cache across visitors. The next interaction after expiry refreshes it. Failed requests retry after five minutes and retain the last good snapshot, or fall back to the bundled data. Uploads and demo mode bypass fetching. Source details show when the displayed data was retrieved.

For local use, set `AA_API_KEY` in the server environment or `.streamlit/secrets.toml` (gitignored). Without a key, the bundled snapshot works. Never put real credentials in committed files. The [secrets template](../.streamlit/secrets.example.toml) contains placeholders only.

## Agent model

### Local Qwen

From the activated environment, in the repository root:

```bash
python -m pip install -e ".[local]"
python -m streamlit run agent_app.py
```

The first actual agent run downloads Qwen2.5-1.5B-Instruct (roughly 3 GB). No LLM API key is needed. GPU, Apple MPS, then CPU are selected automatically; CPU generation can be slow. Set `QWEN_CACHE_DIR` to retain downloads in a persistent folder. The app also supports Ollama; see the [controller reference](reference.md#agent-controls-and-verification).

### Cloud agent

Add compatible provider settings to the agent deployment's Secrets:

```toml
LLM_BASE_URL = "https://your-provider.example/v1"
LLM_MODEL = "your-model-id"
LLM_API_KEY = "your-provider-key"
```

The provider needs an HTTPS `/chat/completions` endpoint supporting `messages`, `temperature`, `max_tokens`, and text JSON responses. A server key funds student calls through your account. An AA key only downloads benchmark data; it does not provide LLM inference.

Until a provider is configured, cloud comparison, similarity, and scripted rehearsal work; actual AI runs are disabled. A rehearsal is not an LLM test. Run the real provider once to verify compatibility and inspect the checked result.

## Update the bundled snapshot

From the repository root, after installation:

```bash
model-lab fetch --prompt-key --output snapshots/aa_new.json
python scripts/prepare_snapshot.py snapshots/aa_new.json
python -m pytest -q
```

Use a new filename for each download. Commit only `model_compare/data/aa_snapshot.json`; the private download directory is ignored. Local `snapshots/aa_latest.json` or `AA_SNAPSHOT_PATH` can override the bundled fallback. Automatic server refresh keeps its data in memory and does not commit anything.

## Share a source ZIP

```bash
python scripts/build_release.py
```

The package includes the apps, data, documentation, examples, and tests. It excludes local environments, private snapshots, and secrets. GitHub Actions also produces this ZIP after tests pass. Unzip it and work from the project folder.
