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


def test_fetch_aa_button_uses_secret(monkeypatch):
    from model_compare.snapshots import demo_snapshot
    def fake_fetch(key):
        assert key=='test-only-key'
        data=demo_snapshot(); data['is_demo']=False
        return data
    monkeypatch.setattr('model_compare.ui.fetch_artificial_analysis',fake_fetch)
    app=AppTest.from_file(str(ROOT/'python_app.py'),default_timeout=30)
    app.secrets['AA_API_KEY']='test-only-key'
    app.run()
    app.button(key='fetch_aa').click().run()
    assert not app.exception
    assert not app.session_state['downloaded_snapshot']['is_demo']
    assert any('8 real model records' in s.value for s in app.success)
