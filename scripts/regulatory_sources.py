"""Publication routes and document requirements for UK regulatory evidence."""
import re
from urllib.parse import urlsplit

PRA_ROUTE=re.compile(r'^/prudential-regulation/publication/20\d{2}/[a-z]+/[a-z0-9-]+/?$',re.I)
FCA_ROUTES={
 'policy-statements':'regulatory_policy',
 'finalised-guidance':'regulatory_policy',
 'guidance-consultations':'regulatory_proposal',
 'discussion-papers':'regulatory_proposal',
 'research':'regulatory_report',
 'corporate-documents':'regulatory_report',
 'final-notices':'regulatory_finding',
}

def lane(url):
 p=urlsplit(url);host=(p.hostname or '').removeprefix('www.')
 if host=='fca.org.uk':
  m=re.fullmatch(r'/publications/([a-z-]+)/[a-z0-9-]+/?',p.path,re.I)
  if m and m[1] in FCA_ROUTES:return FCA_ROUTES[m[1]]
  if re.fullmatch(r'/data/(?:[a-z0-9-]+/)*[a-z0-9-]+/?',p.path,re.I):return 'fca_data'
  if re.fullmatch(r'/news/statements/[a-z0-9-]+/?',p.path,re.I):return 'official_release'
 if host=='bankofengland.co.uk' and PRA_ROUTE.fullmatch(p.path):return 'pra_publication'
 return None

def requires_document(url):
 path=urlsplit(url).path.lower()
 return ('consultation' in path or '/policy-statements/' in path or '/finalised-guidance/' in path or '/final-notices/' in path
         or bool(re.search(r'/(?:[^/]*-)?(?:policy-statement|supervisory-statement|statement-of-policy)(?:-|/|$)',path)))

def publication_status(url,title):
 kind=lane(url)
 if kind=='regulatory_proposal':return 'Proposal'
 if kind=='regulatory_policy':return 'Published policy'
 if kind=='regulatory_report':return 'Published report'
 if kind=='regulatory_finding':return 'Confirmed announcement'
 if kind=='pra_publication':
  subject=url+' '+title
  if re.search(r'(?i)consultation|discussion-paper|\bCP\d{1,2}/\d{2}\b',subject):return 'Proposal'
  if re.search(r'(?i)policy.statement|supervisory.statement|statement.of.policy|\b(?:PS|SS)\d{1,2}/\d{2}\b',subject):return 'Published policy'
  return 'Published report'
 return None
