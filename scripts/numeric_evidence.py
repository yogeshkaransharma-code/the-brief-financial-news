"""Compare reported quantities without confusing currency spacing or unit style.

This checks values and units, not their meaning or denominator. Every statement
still requires the separate source-entailment review.
"""
import re
from decimal import Decimal

TOKEN=re.compile(r'(?<![\w.])(?P<currency>[£$€])?\s*(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)(?:\s*(?P<scale>billion|million|thousand|bn|m|k)(?!\w))?\s*(?P<percent>%?)(?!\w)',re.I)
MULTIPLIERS={'billion':9,'bn':9,'million':6,'m':6,'thousand':3,'k':3,'':0}

def quantities(text):
    found=[]
    for match in TOKEN.finditer(text):
        scale=(match['scale'] or '').lower()
        value=Decimal(match['value'].replace(',',''))*(Decimal(10)**MULTIPLIERS[scale])
        found.append((value,match['percent'] or '',match['currency'] or '',match.group().strip()))
    return found

def unsupported(text,source):
    evidence=quantities(source)
    return [raw for value,unit,currency,raw in quantities(text)
            if not any(value==v and unit==u and (not currency or currency==c)
                       for v,u,c,_ in evidence)]

def self_test():
    source='£100 million, £ 120m, £165m and 50% in 2026. There were 30 firms.'
    assert not unsupported('£100m and 120 million, with £165 million and 50% in 2026.',source)
    for wrong in ['£101m','£100','100','50','$100m','£30']:
        assert unsupported(wrong,source),wrong
    assert not unsupported('30 firms',source)
    print('PASS: currency spacing and equivalent units; changed value, currency, scale and percentage rejected')

if __name__=='__main__':self_test()
