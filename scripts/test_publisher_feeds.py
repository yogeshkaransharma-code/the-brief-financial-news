"""Offline contract tests for GitHub-persistent publisher sources and fair sector discovery."""
import datetime as dt
import json
import tempfile
from pathlib import Path
from update_feeds import FEEDS, registered_feeds, balanced_discovery
from publication_scope import source_lane

additional=registered_feeds()
assert len(additional)>=8
assert all(category=='Banking' for _,_,category in additional)
assert all(url.startswith('https://www.finextra.com/rss/channel.aspx?channel=') for _,url,_ in additional)
assert len({url for _,url,_ in FEEDS})==len(FEEDS),'Feed URLs duplicated'
with tempfile.TemporaryDirectory() as temp:
    tampered=json.loads((Path(__file__).resolve().parents[1]/'data/publisher-feeds.json').read_text())
    tampered['feeds'][0]['url']='https://www.finextra.com.evil.invalid/rss/channel.aspx?channel=retail'
    p=Path(temp)/'feeds.json';p.write_text(json.dumps(tampered))
    try:registered_feeds(p)
    except ValueError:pass
    else:raise AssertionError('Spoofed RSS origin accepted')
    tampered['feeds'][0]['url']='https://www.finextra.com/rss/channel.aspx?channel=retail'
    tampered['feeds'][1]['name']=tampered['feeds'][0]['name']
    p.write_text(json.dumps(tampered))
    try:registered_feeds(p)
    except ValueError:pass
    else:raise AssertionError('Duplicate publisher label accepted')
day=dt.datetime(2026,10,26,9,tzinfo=dt.timezone.utc)
items=[{'url':f'https://finextra.com/newsarticle/{i}/banking', 'published_at':(day+dt.timedelta(seconds=i)).isoformat(),'category':'Banking'} for i in range(720)]
items+=[{'url':f'https://reinsurancene.ws/insurer-{i}/','published_at':(day-dt.timedelta(hours=i+1)).isoformat(),'category':'Insurance'} for i in range(35)]
items+=[{'url':f'https://insuranceage.co.uk/broker-{i}/','published_at':(day-dt.timedelta(hours=i+1)).isoformat(),'category':'Brokers'} for i in range(18)]
chosen=balanced_discovery(items,450)
assert len(chosen)==450
assert sum(x['category']=='Insurance' for x in chosen)==35
assert sum(x['category']=='Brokers' for x in chosen)==18
assert len({x['url'] for x in chosen})==450
print('PASS: persistent curated RSS registry, spoof and duplicate rejection, specialist sector retention')
