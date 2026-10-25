"""Supplementary publisher links, never passed off as The Brief's original articles."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from media_sources import canonical_url,publisher,relevant,diverse
from publication_scope import source_lane
from same_day_policy import source_issued_today
ROOT=Path(__file__).resolve().parents[1]

def select(items,now=None,limit=30):
 seen=set();out=[]
 for raw in items:
  item=dict(raw,url=canonical_url(raw.get('url','')))
  if item.get('discovery_date_basis')=='modified':continue
  if not source_lane(item['url']) or not relevant(item) or not source_issued_today(item,now):continue
  if publisher(item['url']) and re.search(r'(?i)^(?:how|why|what|should|(?:four|five|six|seven|ten|[0-9]+) ways)\b|\b(?:points junkies|squeezed middle|people moves|awards?|webinars?|sponsored|advertorial)\b',item.get('title','')):continue
  fingerprint=''.join(c for c in item.get('title','').casefold() if c.isalnum())
  if item['url'] in seen or fingerprint in seen:continue
  seen.update((item['url'],fingerprint))
  out.append({k:item[k] for k in ('title','url','source','category','dateISO','source_published_at','source_time_precision') if k in item})
  out[-1]['kind']='publisher_link'
  out[-1]['date_basis']='Publisher feed publication date; not independently checked article evidence'
 return diverse(out,limit)

def main():
 feed=json.loads((ROOT/'data/live.json').read_text())
 now=dt.datetime.now(dt.timezone.utc)
 # No stale feed can appear as a fresh successful desk refresh.
 generated=dt.datetime.fromisoformat(feed['generated_at'])
 if now-generated>dt.timedelta(hours=2):raise RuntimeError('Discovery feed is stale; publisher desk not refreshed')
 result={'checked_at':now.isoformat(),'discovery_generated_at':feed['generated_at'],'items':select(feed.get('items',[]),now)}
 (ROOT/'data/headlines.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('HEADLINE_DESK:',json.dumps({'links':len(result['items']),'sectors':sorted({x['category'] for x in result['items']})}))
if __name__=='__main__':main()
