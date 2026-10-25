"""Curated UK primary newsrooms. Paths are release lanes, not whole-domain trust."""
import re
from urllib.parse import urlsplit

EXTRA_INDEXES=(
 ('BIBA','Brokers','https://www.biba.org.uk/press-releases/'),
 ('Zurich UK','Insurance','https://www.zurich.co.uk/media-centre'),
 ('AXA UK','Insurance','https://www.axa.co.uk/newsroom/'),
 ('FSCS','Regulation','https://www.fscs.org.uk/news/'),
 ('Starling Bank','Technology','https://www.starlingbank.com/news/'),
 ('Revolut UK','Technology','https://www.revolut.com/news/'),
)
EXTRA_PATHS={
 'biba.org.uk':('industry_release',r'/press-releases/[a-z0-9-]+/?'),
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
 if rule and re.fullmatch(rule[1],p.path,re.I):return rule[0]
 return None
