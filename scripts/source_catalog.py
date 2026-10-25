"""Searchable catalog of configured routes; distinguish configuration from observed success."""
import json
from update_feeds import FEEDS
from first_party_sources import INDEXES
from media_sources import PUBLISHERS

def catalog(root):
 try:feed=json.loads((root/'data/live.json').read_text())
 except (OSError,ValueError):feed={}
 working={x['url']:x for x in feed.get('sources_checked',[])}
 failed={x['url']:x for x in feed.get('errors',[]) if isinstance(x,dict) and 'url' in x}
 rows=[];seen=set()
 for method,entries in [('RSS/Atom',[(n,c,u) for n,u,c in FEEDS]),('Official index',INDEXES)]:
  for name,category,url in entries:
   if url in seen:continue
   seen.add(url)
   observed='Working in last discovery run' if url in working else ('Coverage warning' if url in failed else 'Configured; see evidence artifact for latest result')
   rows.append({'name':name,'category':category,'url':url,'method':method,'observed':observed})
 return {'checked_at':feed.get('generated_at'),'sources':rows,'original_publishers':sorted(set(v[0] for v in PUBLISHERS.values()))}
