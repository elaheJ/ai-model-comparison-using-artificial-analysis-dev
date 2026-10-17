import json
from pathlib import Path
import pytest
from model_compare.agent import context_id, http_controller, rehearsal_controller, run_agent
from model_compare.core import compare_models
from model_compare.local_qwen import parse_local_reply
from model_compare.snapshots import demo_snapshot

@pytest.fixture
def setup():
    return demo_snapshot(), json.loads((Path(__file__).parents[1]/'examples/task.json').read_text())

def scripted(actions):
    iterator=iter(actions)
    return lambda *_: parse_local_reply(json.dumps(next(iterator)))

def final(snapshot,task,**changes):
    w=compare_models(snapshot,**task)['winner']
    return dict(status='selected' if w else 'no_feasible_model',slug=w['slug'] if w else None,reason='Checked',
                evidence={k:w[k] for k in ('quality','cost_usd','ttft_s','score')} if w else {},**changes)

def steps(snapshot,task):
    w=compare_models(snapshot,**task)['winner']
    return [{'tool':'fetch_metrics','arguments':{}}, {'tool':'compare_models','arguments':task},
            {'tool':'estimate_cost','arguments':{'slug':w['slug'],'input_tokens':task['input_tokens'],'output_tokens':task['output_tokens']}}]

@pytest.mark.parametrize('empty',[False,True])
def test_complete_rehearsal(setup,empty):
    snapshot,task=setup
    if empty: task['min_quality']=999
    result=run_agent(snapshot,task,rehearsal_controller(snapshot,task))
    assert result['completed'] and result['tool_calls']==(2 if empty else 3) and result['invalid_calls']==0

def test_rejected_constraint_can_recover(setup):
    snapshot,task=setup
    good=steps(snapshot,task)
    bad={'tool':'compare_models','arguments':{**task,'max_cost':999}}
    result=run_agent(snapshot,task,scripted([good[0],bad,*good[1:],final(snapshot,task)]))
    assert result['completed'] and result['tool_calls']==4 and result['invalid_calls']==1

def test_wrong_order_and_budget(setup):
    snapshot,task=setup
    bad={'tool':'estimate_cost','arguments':{'slug':'demo-atlas','input_tokens':100000,'output_tokens':20000}}
    result=run_agent(snapshot,task,scripted([bad]*4+[final(snapshot,task)]))
    assert not result['completed'] and result['tool_calls']==4 and result['invalid_calls']==4

def test_early_final_and_fabricated_numbers(setup):
    snapshot,task=setup
    assert not run_agent(snapshot,task,scripted([final(snapshot,task)]))['completed']
    answer=final(snapshot,task); answer['evidence']['quality']+=1000
    result=run_agent(snapshot,task,scripted(steps(snapshot,task)+[answer]))
    assert not result['completed'] and result['stop']=='invalid_or_early_finish'

def test_malformed_responses_and_safe_errors(setup):
    snapshot,task=setup
    for proposal in [None,[], {'tool_calls':[1]}, {'tool_calls':[{},{}]}]:
        assert not run_agent(snapshot,task,lambda *_:proposal)['completed']
    def broken(*_): raise RuntimeError('secret-token-not-for-output')
    result=run_agent(snapshot,task,broken)
    assert not result['completed'] and 'secret-token' not in json.dumps(result)

def test_adapter_parser_and_config():
    parsed=parse_local_reply('<tool_call>{"name":"fetch_metrics","arguments":{}}</tool_call>')
    assert parsed['tool_calls'][0]['name']=='fetch_metrics'
    assert not parse_local_reply('random prose')['tool_calls']
    with pytest.raises(ValueError): http_controller('hosted','model',base_url='http://example.com/v1')

def test_context_tracks_weights(setup):
    snapshot,task=setup
    before=context_id(snapshot,task)
    task['weights']['quality']+=1
    assert context_id(snapshot,task)!=before
