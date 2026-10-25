"""Cross-sector paths, freshness, proportional failure and headline isolation. No paid calls."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from media_sources import publisher,canonical_url,relevant,diverse
from headline_desk import select
from publication_scope import source_lane
from newsroom_v2 import original_media_candidates
from newsroom_health import assess
from ai_cost_guard import CallBudget
from editorial_selection import choose
from types import SimpleNamespace

def main():
 now=dt.datetime(2026,10,25,12,tzinfo=dt.timezone.utc)
 routes=[('https://www.reinsurancene.ws/uk-reinsurance-market-expands/','Reinsurance News','Insurance'),
         ('https://www.finextra.com/newsarticle/50000/uk-bank-expands-sme-lending','Finextra','Banking'),
         ('https://www.professionalpensions.com/news/12345/pension-fund-reports-results','Professional Pensions','Pensions'),
         ('https://www.insurancebusinessmag.com/uk/news/breaking-news/broker-announces-acquisition-123456.aspx','Insurance Business','Brokers')]
 items=[dict(title='UK '+category+' firms announce financing and reporting developments',source=name,category=category,url=url,dateISO='2026-10-25',source_time_precision='timestamp',source_published_at='2026-10-25T09:00:00Z',published_at='2026-10-25T09:00:00Z') for url,name,category in routes]
 for url,name,category in routes:
  assert publisher(url)==name and source_lane(url)=='original_reporting'
  assert not publisher(url.replace('.com/','.com.evil.test/').replace('.ws/','.ws.evil.test/'))
 assert canonical_url('https://www.bbc.co.uk/news/articles/c62kep355q02o?at_medium=RSS&at_campaign=rss')=='https://www.bbc.co.uk/news/articles/c62kep355q02o'
 assert canonical_url('https://news.uk.chubb.com/news-releases?item=12345&utm_source=rss').endswith('?item=12345')
 assert len(original_media_candidates(items,now))==4
 assert len(select(items+items,now))==4
 assert not select([dict(items[0],discovery_date_basis='modified')],now),'An update timestamp was misrepresented as new publication'
 assert not select([dict(items[0],source_published_at='2026-10-24T09:00:00Z',published_at='2026-10-24T09:00:00Z',dateISO='2026-10-24')],now)
 for title in ['UK leather firm makes wallets','How can I save on bank fees?','My partner wants my pension','Sponsored insurance product launch']:
  assert not relevant({'title':title}),title
 assert relevant({'title':'Treasury Budget to include new lending guarantees'})
 assert relevant({'title':'PPF confirms zero levy for 2027/28 and one-year pause to ACS levy','url':'https://www.professionalpensions.com/news/4537731/ppf-confirms-zero-levy-2027-pause-acs-levy'})
 assert relevant({'title':'How to interpret new reporting obligations','url':'https://www.professionalpensions.com/news/4537731/reporting-obligations'})
 assert not relevant({'title':'Sponsored adviser product promotion','url':'https://www.professionalpensions.com/news/4537731/adviser-product'})
 assert relevant({'title':'Aon completes acquisition of specialist intermediary'})
 wealth='https://www.investmentweek.co.uk/news/4537796/baillie-gifford-us-growth-narrowly-saba-shareholders-board'
 assert source_lane(wealth)=='original_reporting'
 from test_autonomous import prepared
 from editorial_fixtures import resign
 from publish_autonomous import eligible
 w=prepared();w['draft']['category']='Wealth';resign(w)
 assert not eligible(w),eligible(w)
 assert relevant({'title':'Baillie Gifford US Growth shareholders back board','url':wealth})
 assert source_lane('https://www.theguardian.com/uk-news/2026/oct/25/banking-lobby-group-accused-cherry-picking-data')=='original_reporting'
 assert source_lane('https://www.theguardian.com/uk-news/ng-interactive/2026/oct/25/budget-game') is None
 assert source_lane('https://www.fca.org.uk/news/press-releases/fca-fines-bank-for-misconduct')=='fca_release'
 report={'first_party_indexes_checked':29,'first_party_discovery_errors':['one blocked source'],'editorial_selection':{'result':'NO_VERIFIED_CANDIDATES'}}
 result=assess([],report,now,{'published':[]},{'sources_checked':[{}],'errors':[]})
 assert result['outcome']=='NO_QUALIFYING_NEWS' and result['source_coverage_status']=='PARTIAL'
 assert assess([],dict(report,editorial_selection={'result':'BUDGET_PAUSED'}),now,{'published':[]},{'sources_checked':[{}]})['outcome']=='BLOCKED'
 docs=[(i,SimpleNamespace(url=i['url'],text='New original evidence of a financial-services development.',evidence_sha256=str(n)*64)) for n,i in enumerate(items)]
 ledger={};meter=CallBudget(ledger)
 response={'selected':[{'id':'N01','reason':'Substantive banking development affects industry participants.'},{'id':'N02','reason':'A separate major insurance-sector development is relevant.'}], 'skipped':[{'id':'N03','reason':'Routine publicity without a material new development.'},{'id':'N04','reason':'Not significant enough for a full original article.'}]}
 # Distinct titles ensure this tests multi-story commissioning, not duplicate refusal.
 for n,(i,_) in enumerate(docs):i['title']=['Lloyds reports profits and deposit growth','Aviva expands commercial insurance products','Pension tax consultation published','Broker buys regional intermediary'][n]
 selected,decision=choose(docs,ledger,meter,lambda _:copy.deepcopy(response),edition_date='2026-10-25')
 assert len(selected)==2 and meter.run_used==1
 assert len(ledger['editorial_rejections'])==2
 from launch_acceptance import evaluate
 assert evaluate([])['result']=='EVIDENCE_PENDING'
 one={'live_check':'success','deployment':'success','run_id':'1','checked_at':now.isoformat(),'event':'push','technical_status':'LIVE_VERIFIED','editorial_outcome':'PUBLISHED','published_this_run':1,'publisher_links':2,'ai_budget':{'requests_this_run':3},'browser_check':'success','commissioned_stories':[{'category':'Banking'},{'category':'Insurance'},{'category':'Pensions'}]}
 assert evaluate([one],now)['result']=='EVIDENCE_PENDING','A technical/code run was mislabelled launch-ready'
 two=dict(one,event='schedule',run_id='2');three=dict(one,event='schedule',run_id='3')
 assert evaluate([one,two,three],now)['result']=='EVIDENCE_COMPLETE'
 assert evaluate([one,two,two],now)['result']=='EVIDENCE_PENDING','Duplicate schedule run counted twice'
 print('PASS: original journalism across four sectors, clean URLs, spoof/freshness/lifestyle rejection, warning isolation, multi-story selection and rejection cache')
if __name__=='__main__':main()
