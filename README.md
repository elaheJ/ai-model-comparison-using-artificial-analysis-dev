# AI Model Comparison using Artificial Analysis — Developer Repository

This is the full maintenance project: app source, tests, data preparation, packaging, and technical documentation.

**Students and instructors using the apps: [start with the minimal classroom repository](https://github.com/elaheJ/it344-model-lab).**

The classroom repository contains only runnable app files, shared code, data, and a short README. The live Streamlit deployments continue to track that classroom repository.

**[Open Model Lab](https://it344-model-lab.streamlit.app/)** · **[Open Model Lab · Agent](https://it344-model-agent.streamlit.app/)**

Both include a 704-model Artificial Analysis snapshot. Students need no AA API key. An instructor can enable automatic data refresh. The agent adds a tool workflow whose result is checked by Python; actual AI runs need a local model or configured provider.

## Run locally

For student-owned Colab sessions: **[Compare notebook](https://colab.research.google.com/github/elaheJ/it344-model-lab/blob/main/colab/Model_Lab_Compare.ipynb)** · **[Agent notebook](https://colab.research.google.com/github/elaheJ/it344-model-lab/blob/main/colab/Model_Lab_Agent.ipynb)**. Each reads the student's `AA_API_KEY` from Colab Secrets (with Notebook access enabled) and fetches a fresh snapshot before launching Gradio. The agent downloads Qwen into the runtime; no hosted LLM key is needed. `colab/` contains the notebooks and `model_compare/colab_ui.py` their interface. Colab code downloads the classroom repository's current `main` runtime modules. Keep these files synchronized between repositories.

Use Python 3.12. In a terminal:

```bash
git clone https://github.com/elaheJ/ai-model-comparison-using-artificial-analysis-dev.git
cd ai-model-comparison-using-artificial-analysis-dev
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m streamlit run python_app.py
```

Windows: use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` for the environment steps. In GitHub Codespaces, dependencies are installed automatically; run only the last command.

Open the local URL printed in the terminal. Choose **Rank models** for single-metric or weighted comparisons, or **Find similar models** to pick a reference model and one or more features.

For the agent interface, run `python -m streamlit run agent_app.py`. Select **Scripted rehearsal (no LLM)** to explore it without a model download. For actual AI, follow [agent setup](docs/setup.md#agent-model).

## Work on the code

| What you want to change | Start here |
| --- | --- |
| Layout, labels, and controls | [model_compare/ui.py](model_compare/ui.py) |
| Colab interface and launch notebooks | [model_compare/colab_ui.py](model_compare/colab_ui.py), [colab/](colab/) |
| Ranking, costs, similarity, and the notebook's ten functions | [model_compare/core.py](model_compare/core.py) |
| Agent tools and result checks | [model_compare/agent.py](model_compare/agent.py) |
| Snapshot format and AA downloads | [model_compare/snapshots.py](model_compare/snapshots.py) |
| Automatic data refresh | [model_compare/live_data.py](model_compare/live_data.py) |
| Expected behavior | [tests/](tests/) |

The three small launch files share the same code: `python_app.py` starts the comparison app, `agent_app.py` starts the local agent, and `cloud_agent_app.py` starts the agent on Streamlit Cloud.

After making a change:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

GitHub runs these checks on every push. Keep keys in Streamlit Secrets or your environment; never commit them.

**More detail:** [Hosting, keys, and local models](docs/setup.md) · [Data formats and scoring methods](docs/reference.md) · [Example comparison task](examples/task.json)

## Maintaining the classroom version

Make and test changes here first. Copy reviewed runtime changes (the three app launchers, `requirements.txt`, `.streamlit/config.toml`, and shared modules/data under `model_compare/`) into the classroom repository, then commit and push there to update the live apps. Do not copy `cli.py`, `python_entry.py`, `agent_entry.py`, developer documentation, tests, scripts, examples, package metadata, or development configuration. Keep the classroom README short. Never copy real credentials.

The release script packages this **full developer project**. It is not the minimal classroom download. The classroom repository's GitHub **Code → Download ZIP** is the student package.
