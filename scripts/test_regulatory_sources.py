"""Actual excluded feed routes, proposal/policy separation and complete document dating."""
import datetime as dt
from unittest.mock import patch
from publication_scope import source_lane
from first_party_sources import official_release
from regulatory_sources import publication_status,requires_document
from source_dates import parse,verify_announcement
from source_retrieval import read_source
from ai_cost_guard import preflight_source
from update_feeds import categorise


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
 assert categorise('Premium credit-card firms expand rewards','Banking')=='Banking'
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
