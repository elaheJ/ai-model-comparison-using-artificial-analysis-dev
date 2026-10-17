from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from model_compare.snapshots import demo_snapshot

ROOT=Path(__file__).parents[1]

@pytest.fixture(autouse=True)
def fixed_teaching_data(monkeypatch):
    # UI expectations must not depend on a developer's private download or the
    # release snapshot; deployment tests below exercise the real packaged data.
    monkeypatch.setattr('model_compare.ui.default_snapshot',demo_snapshot)

def widget(elements,label):
    return next(e for e in elements if e.label==label)

def test_python_app_workload_composite_and_empty():
    app=AppTest.from_file(str(ROOT/'python_app.py'),default_timeout=30).run()
    assert not app.exception
    assert widget(app.metric,"Python's choice").value=='Ember (demo)'
    widget(app.number_input,'Input tokens').set_value(200000).run()
    assert widget(app.metric,'Estimated workload cost').value=='$0.0220'
    widget(app.radio,'Ranking method').set_value('Weighted composite').run()
    assert not app.exception and len(app.slider)==8
    widget(app.slider,'Intelligence index').set_value(100).run()
    assert not app.exception
    widget(app.number_input,'Minimum intelligence index').set_value(999).run()
    assert not app.exception and widget(app.metric,"Python's choice").value=='No feasible model'

def test_agent_rehearsal_stale_result_and_no_candidates():
    app=AppTest.from_file(str(ROOT/'agent_app.py'),default_timeout=30).run()
    assert not app.exception
    assert widget(app.selectbox,'Controller').value=='Local Qwen (notebook model)'
    widget(app.selectbox,'Controller').set_value('Scripted rehearsal (no LLM)').run()
    app.button(key='run_agent').click().run()
    assert not app.exception and app.session_state['agent_run']['completed']
    widget(app.number_input,'Maximum workload cost ($)').set_value(1.0).run()
    assert any('changed' in w.value for w in app.warning)
    widget(app.multiselect,'Models to compare').set_value([]).run()
    assert not app.exception and any('Select at least one' in i.value for i in app.info)

def test_zero_weights_and_creator_search():
    app=AppTest.from_file(str(ROOT/'python_app.py'),default_timeout=30).run()
    widget(app.multiselect,'Creators (empty = all)').set_value(['North']).run()
    assert not app.exception and widget(app.metric,'Candidates').value=='2'
    widget(app.text_input,'Search model name or ID').set_value('no-such-model').run()
    assert not app.exception and any('Select at least one' in i.value for i in app.info)
    widget(app.text_input,'Search model name or ID').set_value('').run()
    widget(app.radio,'Ranking method').set_value('Weighted composite').run()
    for s in app.slider: s.set_value(0)
    app.run()
    assert not app.exception and any('positive composite weight' in w.value for w in app.warning)

def test_hosted_mode():
    app=AppTest.from_file(str(ROOT/'agent_app.py'),default_timeout=30)
    app.secrets['HOSTED_ONLY']='true'
    app.run()
    assert not app.exception
    assert widget(app.selectbox,'Controller').value=='Hosted API'
    assert 'Ollama' not in widget(app.selectbox,'Controller').options

def test_similarity_workspace_uses_whole_snapshot():
    app=AppTest.from_file(str(ROOT/'python_app.py'),default_timeout=30).run()
    widget(app.multiselect,'Models to compare').set_value(['demo-atlas']).run()
    widget(app.radio,'Workspace').set_value('Find similar models').run()
    assert not app.exception
    assert len(widget(app.selectbox,'Reference model').options)==8
    widget(app.multiselect,'Similarity features').set_value(['quality']).run()
    assert any('7 matches' in c.value for c in app.caption)
    widget(app.multiselect,'Similarity features').set_value(['cost_usd','ttft_s']).run()
    assert any('5 matches' in c.value for c in app.caption)
    widget(app.slider,'Minimum similarity (%)').set_value(100).run()
    assert any('No models match' in i.value for i in app.info)
    widget(app.multiselect,'Similarity features').set_value([]).run()
    assert not app.exception and any('at least one similarity' in i.value for i in app.info)


@pytest.mark.parametrize('entry', ['python_app.py', 'cloud_agent_app.py'])
def test_aa_refresh_uses_instructor_secret_without_student_prompt(monkeypatch, entry):
    from model_compare.live_data import SnapshotFeed
    calls=[]
    def fake_fetch(key):
        assert key=='test-only-key'
        calls.append(key)
        data=demo_snapshot(); data['is_demo']=False
        return data
    feed=SnapshotFeed(fetch=fake_fetch)
    monkeypatch.setattr('model_compare.ui.shared_feed',lambda: feed)
    app=AppTest.from_file(str(ROOT/entry),default_timeout=30)
    app.secrets['AA_API_KEY']='test-only-key'
    app.run()
    assert not app.exception
    assert any('Latest AA data · 8 models' in c.value for c in app.caption)
    assert not any('AA API key' in w.label for w in app.text_input)
    assert not any('Fetch latest' in w.label for w in app.button)
    widget(app.radio,'Workspace').set_value('Find similar models').run()
    assert len(calls)==1
    widget(app.checkbox,'Use fictional demo data').check().run()
    assert len(calls)==1 and any('Fictional demo' in c.value for c in app.caption)


def test_aa_failure_uses_saved_data_without_asking_students(monkeypatch):
    from model_compare.live_data import SnapshotFeed
    def failing_fetch(key):
        raise RuntimeError('private error '+key)
    feed=SnapshotFeed(fetch=failing_fetch)
    monkeypatch.setattr('model_compare.ui.shared_feed',lambda: feed)
    app=AppTest.from_file(str(ROOT/'python_app.py'),default_timeout=30)
    app.secrets['AA_API_KEY']='test-only-key'
    app.run()
    assert not app.exception and not app.error
    assert any('temporarily unavailable' in c.value for c in app.caption)
    assert all('test-only-key' not in c.value for c in app.caption)
    assert not any('AA API key' in w.label for w in app.text_input)
