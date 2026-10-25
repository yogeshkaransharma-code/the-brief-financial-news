"""Curated UK primary newsrooms. Paths are release lanes, not whole-domain trust."""
import re
from urllib.parse import urlsplit

EXTRA_INDEXES=(
 ('BIBA','Brokers','https://www.biba.org.uk/press-releases/'),
 ('Hiscox Group','Insurance','https://www.hiscoxgroup.com/news/press-releases'),
 ('Chubb UK','Insurance','https://news.uk.chubb.com/news-releases?category=778'),
 ('Zurich UK','Insurance','https://www.zurich.co.uk/media-centre'),
 ('AXA UK','Insurance','https://www.axa.co.uk/newsroom/'),
 ('FSCS','Regulation','https://www.fscs.org.uk/news/'),
 ('Starling Bank','Technology','https://www.starlingbank.com/news/'),
 ('Revolut UK','Technology','https://www.revolut.com/news/'),
)
EXTRA_PATHS={
 'biba.org.uk':('industry_release',r'/press-releases/[a-z0-9-]+/?'),
 'hiscoxgroup.com':('company_release',r'/news/press-releases/20\d{2}/\d{2}-\d{2}-\d{2}/?'),
 'news.uk.chubb.com':('company_release',r'/news-releases/?'),
 'zurich.co.uk':('company_release',r'/media-centre/[a-z0-9-]+(?:/[a-z0-9-]+)?/?'),
 'axa.co.uk':('company_release',r'/newsroom/media-releases/20\d{2}/[a-z0-9-]+/?'),
 'starlingbank.com':('company_release',r'/news/[a-z0-9-]+/?'),
 'revolut.com':('company_release',r'/news/[a-z0-9_-]+/?'),
 'fscs.org.uk':('official_release',r'/news/[a-z0-9-]+(?:/[a-z0-9-]+)?/?'),
}
EXTRA_HOSTS={host for base in EXTRA_PATHS for host in (base,'www.'+base)}

def extra_lane(url):
 p=urlsplit(url);host=(p.hostname or '').removeprefix('www.')
 rule=EXTRA_PATHS.get(host)
 if rule and re.fullmatch(rule[1],p.path,re.I):
  # Chubb publishes releases as a numeric item on an otherwise generic URL.
  # Never mistake its listing/search parameters for an actual release.
  if host=='news.uk.chubb.com':
   return rule[0] if re.fullmatch(r'item=\d{4,9}',p.query) else None
  # Other supported newsrooms use clean, non-parameterised article URLs.
  return rule[0] if not p.query else None
 return None
