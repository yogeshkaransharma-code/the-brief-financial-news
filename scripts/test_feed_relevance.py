"""Offline RSS relevance regressions: do not confuse publisher sections with newsworthiness."""
import email.utils
from html import escape
from update_feeds import NOW, parse

def sample(title, url):
    published=email.utils.format_datetime(NOW)
    body='A discovery lead only. Source material must still be retrieved, dated and independently verified.'
    return ('<rss version="2.0"><channel><item>'
            f'<title>{escape(title)}</title>'
            f'<description>{escape(body)}</description>'
            f'<link>{escape(url)}</link>'
            f'<pubDate>{published}</pubDate>'
            '</item></channel></rss>').encode()

money='https://www.theguardian.com/money/2026/oct/25/'
kept=parse(sample('Cookie theft: how fraudsters get the digital key to your accounts',
                  money+'cookie-theft-how-fraudsters-get-the-digital-key-to-your-accounts'),
           'The Guardian Money','Banking')
assert len(kept)==1, 'Financial-security reporting must survive title and URL screening'

discarded=parse(sample('How can I get better at baking with my family?',
                       money+'how-can-i-get-better-at-baking-with-my-family'),
                'The Guardian Money','Banking')
assert not discarded, 'A finance-adjacent section must not admit unrelated lifestyle'

sector=parse(sample('Insurers announce changes to commercial underwriting',
                    'https://www.theguardian.com/business/2026/oct/25/insurers-announce-changes-to-commercial-underwriting'),
             'The Guardian Business','Insurance')
assert len(sector)==1, 'Substantive financial-sector headline remains discoverable'

print('PASS: broad publisher feeds require relevant article title and source URL')
