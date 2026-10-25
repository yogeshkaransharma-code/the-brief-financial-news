"""Accessible original journalism registry. A recognised URL is a candidate, never evidence by itself."""
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Exact publisher domains and article routes; never trust lookalike suffixes.
PUBLISHERS = {
 'theguardian.com': ('The Guardian', r'/(?:business|money)/20\d{2}/[a-z]{3}/\d{1,2}/[^/]+/?'),
 'bbc.co.uk': ('BBC', r'/news/articles/[a-z0-9]+/?'),
 'bbc.com': ('BBC', r'/news/articles/[a-z0-9]+/?'),
 'news.sky.com': ('Sky News', r'/story/[^/]+-\d+/?'),
 'insurancebusinessmag.com': ('Insurance Business', r'/uk/news/[^/]+/[^/]+/?'),
 'reinsurancene.ws': ('Reinsurance News', r'/[^/]+/?'),
 'commercialriskonline.com': ('Commercial Risk', r'/[^/]+/?'),
 'insurancejournal.com': ('Insurance Journal', r'/news/(?:[^/]+/)+[^/]+/?'),
 'insurancetimes.co.uk': ('Insurance Times', r'/(?:[^/]+/)*[^/]+\.article'),
 'insuranceage.co.uk': ('Insurance Age', r'/(?:[^/]+/)+[^/]+/?'),
 'finextra.com': ('Finextra', r'/newsarticle/\d+/[^/]+/?'),
 'professionalpensions.com': ('Professional Pensions', r'/news/\d+/[^/]+/?'),
 'moneymarketing.co.uk': ('Money Marketing', r'/(?:news|analysis)/[^/]+/?'),
 'mortgagesolutions.co.uk': ('Mortgage Solutions', r'/(?:news|news/[^/]+)/20\d{2}/\d{2}/\d{2}/[^/]+/?'),
 'ft.com': ('Financial Times', r'/content/[a-f0-9-]+/?'),
 'bloomberg.com': ('Bloomberg', r'/news/articles/20\d{2}-\d{2}-\d{2}/[^/]+/?'),
 'wsj.com': ('The Wall Street Journal', r'/(?:[^/]+/)+[^/]+/?'),
}
MEDIA_HOSTS={h for host in PUBLISHERS for h in (host,'www.'+host)}
TRACKING=re.compile(r'^(?:utm_.*|at_.*|CMP|cmp|mod|rpc|reflink|feedType|feedName)$',re.I)

def canonical_url(url):
 p=urlsplit(url)
 query=urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not TRACKING.match(k)])
 return urlunsplit((p.scheme,p.netloc,p.path,query,''))

def publisher(url):
 try:
  p=urlsplit(url)
  if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.query:return None
  rule=PUBLISHERS.get((p.hostname or '').lower().removeprefix('www.'))
  if rule and re.fullmatch(rule[1],p.path,re.I):return rule[0]
 except ValueError:pass
 return None

FINANCE=re.compile(r"\b(?:banks?|banking|building societ\w*|insur\w*|reinsur\w*|broker\w*|underwrit\w*|mga[s]?|lloyd['’]s|london market|pension\w*|protection|employee benefits|mortgage\w*|lend\w*|credit|financ\w*|fintech|payment\w*|asset manag\w*|wealth manag\w*|investment fund\w*|fund manag\w*|savings?|fca|pra|treasury|central bank\w*|interest rates?|capital markets?|bond markets?|bonds?|gilts?|budget|fiscal|taxation|tax policy|consumer duty)\b",re.I)
LIFESTYLE=re.compile(r"\b(?:ask (?:our|the)|your problems|dear (?:[a-z]+)|money hacks|best buys?|how (?:can|do|to)|should i|my (?:wife|husband|partner)|travel tips|horoscope|crossword|win a|sponsored|advertorial|partner content)\b",re.I)

def relevant(item):
 title=item.get('title','')
 if LIFESTYLE.search(title):return False
 if FINANCE.search(title):return True
 # Recognise firms in headlines, not incidental references in related-story summaries.
 from market_coverage import ORGANISATIONS
 return any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',title,re.I)
            for entries in ORGANISATIONS.values() for name,_ in entries if len(name)>3)

def diverse(items,limit):
 """Round-robin by sector then source; one prolific feed cannot starve the desk."""
 queues={}
 for item in sorted(items,key=lambda x:x.get('published_at',''),reverse=True):
  queues.setdefault((item.get('category'),item.get('source')),[]).append(item)
 output=[]
 while queues and len(output)<limit:
  for key in list(queues):
   output.append(queues[key].pop(0))
   if not queues[key]:del queues[key]
   if len(output)>=limit:break
 return output
