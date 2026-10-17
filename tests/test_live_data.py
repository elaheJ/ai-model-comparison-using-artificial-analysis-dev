from model_compare.live_data import SnapshotFeed


def test_shared_refresh_and_last_good_data_after_failure():
    now=[0]
    calls=[]
    def fetch(key):
        calls.append(key)
        if len(calls)==2:
            raise RuntimeError('network error')
        return {'models':[{'name':str(len(calls))}]}
    feed=SnapshotFeed(fetch=fetch,clock=lambda:now[0],refresh_seconds=60,retry_seconds=5)
    first,stale=feed.read('instructor-key')
    assert not stale and len(calls)==1
    first['models'].clear()
    assert feed.read('instructor-key')[0]['models']  # callers cannot mutate the cache
    now[0]=59
    feed.read('instructor-key')
    assert len(calls)==1
    now[0]=60
    saved,stale=feed.read('instructor-key')
    assert stale and saved['models'][0]['name']=='1'
    now[0]=64
    feed.read('instructor-key')
    assert len(calls)==2
    now[0]=65
    fresh,stale=feed.read('instructor-key')
    assert not stale and fresh['models'][0]['name']=='3'


def test_missing_key_and_key_rotation():
    calls=[]
    def fetch(key):
        calls.append(key)
        return {'models':[]}
    feed=SnapshotFeed(fetch=fetch,clock=lambda:0)
    assert feed.read('')==(None,False)
    assert calls==[]
    feed.read('first-key')
    feed.read('replacement-key')
    assert calls==['first-key','replacement-key']
    assert 'replacement-key' not in str(vars(feed))


def test_initial_failure_is_backed_off():
    calls=[]
    def fetch(key):
        calls.append(key)
        raise ValueError('bad credentials')
    feed=SnapshotFeed(fetch=fetch,clock=lambda:0)
    assert feed.read('invalid')==(None,True)
    assert feed.read('invalid')==(None,True)
    assert len(calls)==1
