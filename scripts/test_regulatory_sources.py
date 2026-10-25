"""Actual excluded feed routes, proposal/policy separation and complete document dating."""
import datetime as dt
from unittest.mock import patch
from publication_scope import source_lane
from first_party_sources import official_release
from regulatory_sources import publication_status,requires_document
from source_dates import parse,verify_announcement
from source_retrieval import read_source
from ai_cost_guard import preflight_source
from update_feeds import categorise,canonical_record,parse as parse_feed


def main():
 pra='https://www.bankofengland.co.uk/prudential-regulation/publication/2026/october/review-of-the-smcr-phase-two-consultation-paper'
 guidance='https://www.fca.org.uk/publications/guidance-consultations/gc26-7-decentralised-finance-guidance'
 data='https://www.fca.org.uk/data/insurance-and-pure-protection-complaints-2026-h1'
 policy='https://www.fca.org.uk/publications/policy-statements/ps26-1-reporting-changes'
 assert source_lane(pra)=='pra_publication' and publication_status(pra,'CP14/26')=='Proposal'
 assert source_lane(guidance)=='regulatory_proposal' and publication_status(guidance,'Guidance consultation')=='Proposal'
 assert source_lane(data)=='fca_data'
 assert official_release(pra,'Bank of England')
 assert official_release(guidance,'Financial Conduct Authority')
 assert source_lane(policy)=='regulatory_policy' and publication_status(policy,'Final policy')=='Published policy'
 assert source_lane('https://www.investegate.co.uk/announcement/rns/example--EXM/new-market-announcement/12345678')=='issuer_rns'
 assert not source_lane(pra.replace('.co.uk/','.co.uk.evil.test/'))
 assert parse('Published on 25 October 2026')==('2026-10-25','2026-10-25','date')
 assert parse('Updated on 25 October 2026') is None
 assert parse('Fri, 23 Oct 2026 07:00 GMT')==('2026-10-23','2026-10-23T07:00:00+00:00','timestamp')
 assert parse('First published: 21st August 2026')==('2026-08-21','2026-08-21','date')
 assert parse('2026-10-24T20:30:00-04:00')==('2026-10-25','2026-10-25T00:30:00+00:00','timestamp')
 from source_dates import published_date
 from same_day_policy import original_date
 overseas=published_date('<meta property="article:published_time" content="2026-10-24T20:30:00-04:00">')
 assert overseas[0]=='2026-10-25'
 assert original_date({'dateISO':overseas[0],'source_published_at':overseas[1],'source_time_precision':overseas[2]})==dt.date(2026,10,25)
 assert categorise('Premium credit-card firms expand rewards','Banking')=='Banking'
 previous=canonical_record({'id':'old-id','url':'https://www.bbc.co.uk/news/articles/c62kep355q02o?at_medium=RSS','category':'Insurance'})
 corrected=canonical_record({'id':'new-id','url':'https://www.bbc.co.uk/news/articles/c62kep355q02o','category':'Banking'})
 cache={previous['url']:previous};cache.update({corrected['url']:corrected})
 assert len(cache)==1 and next(iter(cache.values()))['category']=='Banking'
 atom='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>UK insurers publish financial reporting data</title><summary>A financial reporting development for insurers with original documents to inspect.</summary><link href="https://www.fca.org.uk/data/insurance-reporting-data"/><updated>2026-10-25T09:00:00Z</updated>{published}</entry></feed>'
 with patch('update_feeds.NOW',dt.datetime(2026,10,25,12,tzinfo=dt.timezone.utc)):
  modified=parse_feed(atom.format(published='').encode(),'FCA publications','Regulation')[0]
  original=parse_feed(atom.format(published='<published>2026-10-24T09:00:00Z</published>').encode(),'FCA publications','Regulation')[0]
 assert modified['discovery_date_basis']=='modified'
 assert original['discovery_date_basis']=='published' and original['dateISO']=='2026-10-24'
 # A short landing page is not enough: its central document must be fetched.
 pdf='https://www.bankofengland.co.uk/-/media/boe/files/prudential-regulation/consultation-paper/2026/cp1426.pdf'
 page=('<main><h1>CP14/26 reporting consultation</h1><p class="published-date">Published on 25 October 2026</p><a href="'+pdf+'">Download consultation paper</a></main>').encode()
 evidence='The regulator proposes reporting changes and seeks views from insurers and banks. No rule is final and no effective date is set. '*15
 def retrieve(url,*args):return (b'pdf-bytes','application/pdf',pdf) if url==pdf else (page,'text/html',pra)
 with patch('source_retrieval.retrieve_bytes',side_effect=retrieve) as fetch,patch('source_retrieval.pdf_extract',return_value=evidence):
  doc=read_source(pra)
 assert fetch.call_count==2 and doc.document_urls==[pra,pdf] and evidence in doc.text
 assert doc.extraction=='complete HTML and linked official PDF'
 item={'title':'PRA consults on reporting rules for insurance and banking','category':'Regulation','source':'PRA','url':pra,'dateISO':'2026-10-25','source_time_precision':'date'}
 assert preflight_source(item,doc)
 assert verify_announcement(item,doc,dt.datetime(2026,10,25,12,tzinfo=dt.timezone.utc))['dateISO']=='2026-10-25'
 try:verify_announcement(item,doc,dt.datetime(2026,10,26,12,tzinfo=dt.timezone.utc))
 except ValueError:pass
 else:raise AssertionError('A regulatory document was redated as a current development')
 print('PASS: excluded PRA/FCA routes, original dates, proposal vs policy, full PDF capture and accurate banking categorisation')
if __name__=='__main__':main()
