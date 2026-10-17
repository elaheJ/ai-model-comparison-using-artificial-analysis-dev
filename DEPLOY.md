# Deploy both student apps from GitHub

Hosted URLs: [Model Lab](https://it344-model-lab.streamlit.app/) and [Model Lab · Agent](https://it344-model-agent.streamlit.app/). Both deploy from [`elaheJ/it344-model-lab`](https://github.com/elaheJ/it344-model-lab), branch `main`, using Python 3.12. The instructions below also support deploying your own copy. Actual cloud-agent inference requires the provider configuration in step 3.

Both apps retain **Find similar models**: pick any reference model, select one or more features, and see every comparable alternative with a similarity threshold and downloadable results. They ship with a cleaned **704-model Artificial Analysis snapshot**; students do not need an AA account or key to use that data.

GitHub stores the source. **Streamlit Community Cloud runs the apps** and provides the URLs students open. GitHub Pages cannot run these Python servers.

## 1. Put the project in GitHub

Unzip `model-comparison-apps.zip`. Put the **contents of the `model-comparison-apps` folder at the repository root**, including `model_compare`, `.streamlit`, `.github`, and `requirements.txt`. Do not upload the ZIP as a single file.

If you use Git and GitHub CLI, run these from the project folder (change the repository name if desired):

```bash
git init -b main
git add .
git commit -m "Add student model comparison and similarity apps"
gh repo create it344-model-lab --public --source=. --remote=origin --push
```

`gh` must already be signed into your GitHub account. Alternatively, create a repository on github.com and push these files there. This project does not create a repository or change your GitHub account automatically.

The release builder includes only approved source files, examples, tests, and the cleaned teaching snapshot. It excludes API keys, `.streamlit/secrets.toml`, `.env`, `.venv`, private downloads in `snapshots/`, and the original course notebook/documents.

## 2. Create two Streamlit deployments

Open [Streamlit Community Cloud](https://share.streamlit.io), choose **Create app**, and select your repository and `main` branch. Create these two deployments:

| Student app | Main file path | Python | Secrets |
| --- | --- | --- | --- |
| Model Lab | `python_app.py` | 3.12 | None required |
| Model Lab · Agent | `cloud_agent_app.py` | 3.12 | LLM provider settings below for actual AI runs |

Choose a separate app URL for each deployment. After deployment, share those two URLs with students. Both apps load the bundled snapshot automatically, including when the runtime starts in a different working directory. Dependencies come from the root `requirements.txt`.

The regular `agent_app.py` remains the **local Qwen entry point**. Use `cloud_agent_app.py` on Community Cloud: it avoids downloading local model weights into the web server. It offers a hosted LLM and a clearly labeled scripted rehearsal. The rehearsal is not an AI run.

## 3. Configure the cloud agent

In the agent deployment, open **Advanced settings → Secrets** (or app settings after deployment). Enter real settings for a provider with a compatible HTTPS `/chat/completions` endpoint:

```toml
LLM_BASE_URL = "https://your-provider.example/v1"
LLM_MODEL = "your-provider-model-id"
LLM_API_KEY = "your-provider-key"
```

These are placeholders; replace all three with your provider's values. The provider must support `messages`, `temperature`, `max_tokens`, and text JSON responses at that endpoint. Provider/model compatibility must be checked with an actual run.

With a server key, students can use the agent without their own accounts, and calls use your provider quota. If you prefer students to supply their own keys, omit `LLM_API_KEY`; they can enter session keys under **Controller settings**. No key appears in app exports. Do not commit actual credentials to GitHub. [.streamlit/secrets.example.toml](.streamlit/secrets.example.toml) is a non-secret template.

Without provider settings, **comparison and similarity work immediately**, but the AI Run button is disabled with a setup message. Selecting scripted rehearsal demonstrates the checked workflow without an LLM. A deployment is not a successful live AI test until a real provider has been configured and exercised.

To keep inference local and avoid a hosted LLM API, run `agent_app.py` on your computer or an inference-capable server with `requirements-local.txt` installed. GitHub can still hold that source; Community Cloud is not the local-Qwen deployment target supplied here.

## 4. Check the student experience

1. Confirm Data reports the real snapshot, not fictional demo data.
2. Open **Find similar models** in each app. Select a model with known cost/TTFT, choose those features, and adjust the similarity threshold. Search spans the full snapshot, not just the ranking shortlist.
3. Try single-metric and composite ranking; inspect exclusions and download a result.
4. Run a scripted rehearsal in the agent app to check the workflow.
5. Configure your provider and run the actual agent. Confirm its checked result and inspect its trace. A model can fail the tool/evidence checks; that failure should be reported rather than hidden.

Keep the snapshot retrieval date with student results. It is saved benchmark data, not a live feed.

## 5. Refresh the teaching snapshot

From your local project folder:

```bash
# Use a new filename for each download; the fetch command will not overwrite it.
model-lab fetch --prompt-key --output snapshots/aa_new.json
python scripts/prepare_snapshot.py snapshots/aa_new.json
python -m pytest -q
git add model_compare/data/aa_snapshot.json
git commit -m "Refresh the teaching model snapshot"
git push
```

The preparation script validates and retains only recognized fields. Commit the resulting `model_compare/data/aa_snapshot.json`; the raw download directory stays ignored. Streamlit redeploys code changes from GitHub. API refresh is explicit; no scheduled jobs or student-triggered use of an instructor AA key are required.

## Checks and release package

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/build_release.py --output dist/model-comparison-apps.zip
```

GitHub Actions runs offline tests on Python 3.10 and 3.12, exercises both deployment entry points and similarity search, and uploads the source ZIP as a build artifact. It does not publish an app or invoke a paid LLM.

Official guidance: [deploy from a GitHub repository](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [dependency files](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), and [secrets](https://docs.streamlit.io/deploy/concepts/secrets).
