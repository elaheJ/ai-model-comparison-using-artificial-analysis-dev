import copy
import json
from pathlib import Path
import pytest
from model_compare import core as c
from model_compare.snapshots import demo_snapshot, load_snapshot, normalize_snapshot

@pytest.fixture
def snapshot():
    return demo_snapshot()

@pytest.fixture
def task():
    return json.loads((Path(__file__).parents[1] / 'examples/task.json').read_text())

@pytest.mark.parametrize('value,expected', [(0,True), (1.5,True), (None,False), (True,False), (float('nan'),False), (float('inf'),False), ('2',False)])
def test_measurements(value, expected):
    assert c.has_measurement(value) is expected

def test_notebook_functions():
    assert c.read_metric({'pricing':None}, 'pricing', 'x') is None
    assert c.read_metric({'pricing':{'x':0}}, 'pricing', 'x') == 0
    assert c.models_for_slugs([{'slug':'a'},{'slug':'ab'}], ['a']) == [{'slug':'a'}]
    assert c.workload_cost(1_000_000,1_000_000,2,3) == 5
    assert c.workload_cost(0,0,0,0) == 0
    assert c.workload_cost(0,0,None,1) is None
    with pytest.raises(ValueError): c.workload_cost(True,1,1,1)
    assert c.meets_limits({'quality':1,'ttft_s':1,'cost_usd':1},1,1,1)
    assert not c.meets_limits({'quality':1,'ttft_s':None,'cost_usd':1},1,1,1)
    rows=[{'slug':'b','cost_usd':1,'ttft_s':2},{'slug':'a','cost_usd':1,'ttft_s':1}]
    assert c.choose_model(rows,'cost')['slug'] == 'a'
    assert c.choose_model([],'latency') is None
    assert c.valid_tool_call('fetch_metrics', {})
    assert not c.valid_tool_call([], {})
    assert not c.valid_tool_call('exec', {'code':'print(1)'})
    assert c.can_continue(3,False) and not c.can_continue(4,False) and not c.can_continue(0,True)
    args={'weights':{'quality':40}}; obs={'rows':[1]}; old=[]
    trace=c.record_trace(old,'test',args,obs); args['weights']['quality']=0; obs['rows'].append(2)
    assert old == [] and trace[0]['arguments']['weights']['quality']==40 and trace[0]['observation']['rows']==[1]
    assert c.check_recommendation({'status':'no_feasible_model','slug':None,'reason':'None passes'},None)
    assert not c.check_recommendation({'status':'selected','slug':'a','reason':''},'a')

def test_cost_and_workload(snapshot,task):
    task['objective']='cost'
    result=c.fixed_workflow(snapshot,task)
    assert result['winner']['slug']=='demo-ember' and result['tool_calls']==3
    assert result['winner']['cost_usd']==pytest.approx(.014)
    task['input_tokens']*=2; task['output_tokens']*=2
    assert c.compare_models(snapshot,**task)['winner']['cost_usd']==pytest.approx(.028)
    task['min_quality']=999
    empty=c.fixed_workflow(snapshot,task)
    assert empty['winner'] is None and empty['tool_calls']==2

def test_composite_math():
    rows=[{'slug':'a','quality':10,'cost_usd':10},{'slug':'b','quality':20,'cost_usd':20},{'slug':'c','quality':15,'cost_usd':15}]
    rank,bounds=c.rank_models(rows,'composite',{'quality':75,'cost_usd':25})
    assert [r['slug'] for r in rank]==['b','c','a']
    assert [r['score'] for r in rank]==pytest.approx([75,50,25])
    assert bounds=={'quality':[10,20],'cost_usd':[10,20]}
    tied,_=c.rank_models([{'slug':'b','quality':0},{'slug':'a','quality':0}], 'composite', {'quality':1,'cost_usd':0})
    assert tied[0]['slug']=='a' and tied[0]['score']==100

def test_missing_zero_weight_and_limits(snapshot,task):
    task['slugs']=['demo-atlas','demo-harbor','demo-grove']
    result=c.compare_models(snapshot,**task)
    assert result['feasible_slugs']==['demo-atlas']
    task['weights']={'quality':0}
    with pytest.raises(ValueError): c.compare_models(snapshot,**task)
    task['weights']={'quality':1}; task['extra_limits']={'first_answer_s':1}
    assert c.compare_models(snapshot,**task)['winner'] is None
    task['slugs']=['not-there']
    with pytest.raises(ValueError): c.compare_models(snapshot,**task)

def test_frontier_and_nearest():
    rows=[{'slug':'a','quality':5,'cost_usd':1,'ttft_s':1}, {'slug':'b','quality':5,'cost_usd':2,'ttft_s':2}, {'slug':'c','quality':10,'cost_usd':3,'ttft_s':3}]
    assert c.pareto_front(rows)==['a','c']
    assert c.similar_models(rows,'a','cost_usd')[0]['slug']=='b'

def test_snapshot_formats(snapshot):
    assert normalize_snapshot(snapshot)['snapshot_id']==snapshot['snapshot_id']
    raw={'data':[{'slug':'x','performance':None,'quality':0,'input_price':0,'output_price':1}]}
    model=normalize_snapshot(raw)['models'][0]
    assert model['evaluations']['artificial_analysis_intelligence_index']==0
    assert model['performance']['median_time_to_first_token_seconds'] is None
    csv=b'slug,name,quality,input_price,output_price,ttft_s\nx,X,0,0,1,\n'
    assert load_snapshot(csv,'x.csv')['models'][0]['slug']=='x'
    for bad in [b'not json', b'{}', b'{"models":[{"slug":"x","quality":NaN}]}', b'{"models":[{"slug":"x","quality":true}]}']:
        with pytest.raises(ValueError): load_snapshot(bad)
    with pytest.raises(ValueError): normalize_snapshot({'models':[{'slug':'x'},{'slug':'x'}]})
    with pytest.raises(ValueError): normalize_snapshot({'data':[{'slug':'x'}], 'pagination':{'has_more':True}})
    with pytest.raises(ValueError): load_snapshot(b'x'* (10*1024*1024+1))

def test_numeric_evidence(snapshot,task):
    winner=c.compare_models(snapshot,**task)['winner']
    evidence={k:winner[k] for k in ('quality','cost_usd','ttft_s','score')}
    assert c.check_numeric_evidence(evidence,winner)
    assert not c.check_numeric_evidence({**evidence,'quality':evidence['quality']+1000},winner)

def test_similarity_multiple_features_all_results_and_threshold():
    rows = [{'slug':str(i), 'quality':i, 'cost_usd':i*2, 'ttft_s':i*100} for i in range(10)]
    result = c.find_similar_models(rows, '0', ['cost_usd','ttft_s'])
    assert len(result['matches']) == 9  # no old top-five cap
    assert result['matches'][0]['slug'] == '1'
    assert result['matches'][0]['similarity_pct'] == pytest.approx(100 * 8/9)
    assert result['matches'][-1]['similarity_pct'] == 0
    assert result['matches'][0]['differences'] == {'cost_usd':2,'ttft_s':100}
    filtered = c.find_similar_models(rows,'0',['cost_usd','ttft_s'],80)
    assert [r['slug'] for r in filtered['matches']] == ['1']
    assert filtered['below_threshold'] == 8
    assert len(c.similar_models(rows,'0','cost_usd')) == 9
    assert len(c.similar_models(rows,'0',['cost_usd','ttft_s'],k=2)) == 2


def test_similarity_missing_ties_constants_and_zero_reference():
    rows = [{'slug':'ref','cost_usd':0,'ttft_s':1}, {'slug':'b','cost_usd':0,'ttft_s':1},
            {'slug':'a','cost_usd':0,'ttft_s':1}, {'slug':'missing','cost_usd':None,'ttft_s':1}]
    result = c.find_similar_models(rows,'ref',['cost_usd','ttft_s'],100)
    assert [r['slug'] for r in result['matches']] == ['a','b']
    assert all(r['similarity_pct']==100 for r in result['matches'])
    assert result['excluded'] == [{'slug':'missing','missing_features':['cost_usd']}]
    for slug,features in [('missing',['cost_usd']),('unknown',['ttft_s']),('ref',[]),('ref',['unknown']),('ref',['ttft_s','ttft_s'])]:
        with pytest.raises(ValueError): c.find_similar_models(rows,slug,features)
    with pytest.raises(ValueError): c.find_similar_models(rows,'ref',['ttft_s'],True)
