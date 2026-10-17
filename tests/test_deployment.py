import io
import json
from pathlib import Path
import ssl
import pytest
from streamlit.testing.v1 import AppTest
from model_compare import snapshots
from model_compare.agent import http_controller
from scripts.build_release import release_files

ROOT=Path(__file__).parents[1]


def test_bundled_snapshot_is_available_away_from_checkout(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('AA_SNAPSHOT_PATH',raising=False)
    snapshot=snapshots.default_snapshot()
    assert not snapshot['is_demo']
    assert len(snapshot['models']) > 100
    assert snapshot['source']=='https://artificialanalysis.ai'
    assert snapshot['retrieved_at']!='Not recorded'


@pytest.mark.parametrize('entry',['python_app.py','cloud_agent_app.py'])
def test_cloud_entry_and_similarity_with_bundled_data(entry,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('AA_SNAPSHOT_PATH',raising=False)
    app=AppTest.from_file(str(ROOT/entry),default_timeout=30).run()
    assert not app.exception
    count=len(snapshots.default_snapshot()['models'])
    assert any(f'Loaded snapshot · {count} models' in c.value for c in app.caption)
    if entry=='cloud_agent_app.py':
        provider=next(w for w in app.selectbox if w.label=='Controller')
        assert provider.value=='Hosted API'
        assert 'Ollama' not in provider.options
        assert not any('Local Qwen' in option for option in provider.options)
        assert app.button(key='run_agent').disabled
    next(w for w in app.radio if w.label=='Workspace').set_value('Find similar models').run()
    assert not app.exception
    assert len(next(w for w in app.selectbox if w.label=='Reference model').options)==count
    assert any('matches ·' in c.value for c in app.caption)


def test_cloud_agent_can_rehearse_without_local_model(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('model_compare.ui.default_snapshot',snapshots.demo_snapshot)
    app=AppTest.from_file(str(ROOT/'cloud_agent_app.py'),default_timeout=30).run()
    next(w for w in app.selectbox if w.label=='Controller').set_value('Scripted rehearsal (no LLM)').run()
    app.button(key='run_agent').click().run()
    assert not app.exception and app.session_state['agent_run']['completed']


def test_hosted_controller_uses_verified_tls_and_parses_json(monkeypatch):
    def respond(request,timeout,context):
        assert request.full_url=='https://provider.example/v1/chat/completions'
        assert request.get_header('Authorization')=='Bearer test-key'
        assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
        assert json.loads(request.data)['model']=='test-model'
        content=json.dumps({'tool':'fetch_metrics','arguments':{}})
        return io.BytesIO(json.dumps({'choices':[{'message':{'content':content}}]}).encode())
    monkeypatch.setattr('model_compare.agent.urlopen',respond)
    controller=http_controller('hosted','test-model','test-key','https://provider.example/v1')
    response=controller([],[],'auto')
    assert response['tool_calls']==[{'name':'fetch_metrics','arguments':{}}]
    assert 'test-key' not in json.dumps(response)


def test_release_allowlist_excludes_private_files():
    files={str(p.relative_to(ROOT)) for p in release_files(ROOT)}
    assert {'python_app.py','cloud_agent_app.py','model_compare/data/aa_snapshot.json','DEPLOY.md'} <= files
    assert '.streamlit/secrets.example.toml' in files
    assert not any(p.startswith(('.venv/','snapshots/')) or p in ('.env','.streamlit/secrets.toml') for p in files)
