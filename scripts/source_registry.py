"""Curated UK primary newsrooms. Paths are release lanes, not whole-domain trust."""
import re
from urllib.parse import urlsplit

EXTRA_INDEXES=(
 ('BIBA','Brokers','https://www.biba.org.uk/press-releases/'),
 ('Ageas UK','Insurance','https://www.ageas.co.uk/press-releases/'),
 ("Lloyd's Market Association",'Insurance','https://lmalloyds.com/insights-resources/press-releases/'),
 ('Managing General Agents Association','Brokers','https://mgaa.co.uk/news/'),
 ('Howden Broking Group','Brokers','https://www.howdengroup.com/news-insights'),
 ('Gallagher Investor Relations','Brokers','https://investor.ajg.com/news/default.aspx'),
 ('Hiscox Group','Insurance','https://www.hiscoxgroup.com/news/press-releases'),
 ('Chubb UK','Insurance','https://news.uk.chubb.com/news-releases?category=778'),
 ('Admiral Group','Insurance','https://www.admiralgroup.co.uk/media/news-releases-and-media-contacts'),
 ('Lloyds Bank Retail','Banking','https://www.lloydsbank.com/news-and-insights.html'),
 ("Lloyd's Market",'Insurance','https://www.lloyds.com/insights/media-centre/press-releases'),
 ('Zurich UK','Insurance','https://www.zurich.co.uk/media-centre'),
 ('AXA UK','Insurance','https://www.axa.co.uk/newsroom/'),
 ('FSCS','Regulation','https://www.fscs.org.uk/news/'),
 ('Starling Bank','Technology','https://www.starlingbank.com/news/'),
 ('Revolut UK','Technology','https://www.revolut.com/news/'),
)
EXTRA_PATHS={
 'biba.org.uk':('industry_release',r'/press-releases/[a-z0-9-]+/?'),
 'ageas.co.uk':('company_release',r'/press-releases/20\d{2}-press-releases/[a-z0-9-]+/?'),
 'lmalloyds.com':('industry_release',r'/[a-z0-9-]{24,}/?'),
 'mgaa.co.uk':('industry_release',r'/[a-z0-9-]{24,}/?'),
 'howdengroup.com':('company_release',r'/(?:news-insights|news-and-insights)/[a-z0-9-]{12,}/?'),
 'investor.ajg.com':('company_release',r'/news/news-details/20\d{2}/[a-z0-9-]+/default\.aspx'),
 'hiscoxgroup.com':('company_release',r'/news/press-releases/20\d{2}/\d{2}-\d{2}-\d{2}/?'),
 'news.uk.chubb.com':('company_release',r'/news-releases/?'),
 'admiralgroup.co.uk':('company_release',r'/news-releases/news-release-details/[a-z0-9-]+/?'),
 'lloydsbank.com':('company_release',r'/news-and-insights/20\d{2}/[a-z0-9-]+\.html'),
 'lloyds.com':('industry_release',r'/insights/media-centre/press-releases/[a-z0-9-]+/?'),
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
