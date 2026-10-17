import io
import json
import socket
import ssl
from urllib.error import URLError
import pytest
from model_compare import snapshots as s


def test_key_aliases(monkeypatch):
    monkeypatch.delenv('AA_API_KEY',raising=False)
    monkeypatch.setenv('ARTIFICIAL_ANALYSIS_API_KEY','legacy-test-value')
    assert s.configured_api_key() == 'legacy-test-value'
    monkeypatch.setenv('AA_API_KEY',' new-test-value ')
    assert s.configured_api_key() == 'new-test-value'


def test_fetch_pagination_and_provenance(monkeypatch):
    pages = iter([
        {'data':[{'slug':'a','quality':1}], 'intelligence_index_version':4.1, 'pagination':{'has_more':True}},
        {'data':[{'slug':'b','quality':2}], 'intelligence_index_version':4.1, 'pagination':{'has_more':False}}])
    calls=[]
    def request(req,timeout,context):
        assert req.get_header('X-api-key') == 'test-value'
        assert context.check_hostname
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.cert_store_stats()['x509_ca'] > 0
        calls.append(req.full_url)
        return io.BytesIO(json.dumps(next(pages)).encode())
    monkeypatch.setattr(s,'urlopen',request)
    result=s.fetch_artificial_analysis('test-value')
    assert [r['slug'] for r in result['models']]==['a','b']
    assert not result['is_demo'] and result['retrieved_at'] != 'Not recorded'
    assert calls[-1].endswith('page=2')
    assert 'test-value' not in json.dumps(result)


def test_version_change_is_rejected(monkeypatch):
    pages=iter([{'data':[{'slug':'a'}],'intelligence_index_version':1,'pagination':{'has_more':True}},
                {'data':[{'slug':'b'}],'intelligence_index_version':2,'pagination':{'has_more':False}}])
    monkeypatch.setattr(s,'urlopen',lambda *a,**k:io.BytesIO(json.dumps(next(pages)).encode()))
    with pytest.raises(ValueError,match='version changed'): s.fetch_artificial_analysis('test-value')


def test_default_saved_snapshot(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('AA_SNAPSHOT_PATH',raising=False)
    monkeypatch.setattr(s,'BUNDLED_SNAPSHOT',tmp_path/'no-bundled-snapshot.json')
    assert s.default_snapshot()['is_demo']
    path=tmp_path/'snapshots'/'aa_latest.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'models':[{'slug':'real'}],'source':'test source'}))
    assert s.default_snapshot()['models'][0]['slug']=='real'
    monkeypatch.setenv('AA_SNAPSHOT_PATH',str(tmp_path/'missing.json'))
    with pytest.raises(OSError): s.default_snapshot()


def test_cli_prompt_saves_only_snapshot(tmp_path,monkeypatch):
    from model_compare import cli
    output=tmp_path/'snapshot.json'
    monkeypatch.setattr('sys.argv',['model-lab','fetch','--prompt-key','--output',str(output)])
    monkeypatch.setattr(cli,'getpass',lambda prompt:'test-terminal-key')
    def fake_fetch(key):
        assert key=='test-terminal-key'
        return {'source':'test','models':[{'slug':'model'}]}
    monkeypatch.setattr(cli,'fetch_artificial_analysis',fake_fetch)
    cli.main()
    assert output.exists()
    assert 'test-terminal-key' not in output.read_text()


@pytest.mark.parametrize('reason,message',[
    (ssl.SSLCertVerificationError('private diagnostic'), 'TLS certificate verification failed'),
    (socket.gaierror('private diagnostic'), 'Could not resolve'),
    (TimeoutError('private diagnostic'), 'timed out'),
    (ConnectionRefusedError('private diagnostic'), 'Could not connect'),
])
def test_connection_errors_are_useful_and_do_not_expose_credentials(monkeypatch,reason,message):
    def fail(*args,**kwargs):
        raise URLError(reason)
    monkeypatch.setattr(s,'urlopen',fail)
    with pytest.raises(RuntimeError,match=message) as error:
        s.fetch_artificial_analysis('test-private-key')
    assert 'private' not in str(error.value)


def test_key_with_control_characters_is_rejected_before_network(monkeypatch):
    def unexpected_request(*args,**kwargs):
        pytest.fail('Invalid key must not trigger a network request')
    monkeypatch.setattr(s,'urlopen',unexpected_request)
    with pytest.raises(ValueError,match='single line'):
        s.fetch_artificial_analysis('private\nkey')
