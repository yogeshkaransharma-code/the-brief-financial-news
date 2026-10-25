"""Selection calls, exact candidate coverage, cache and refusal tests. No API."""
import copy
from types import SimpleNamespace
from editorial_selection import choose
from ai_cost_guard import CallBudget

def main():
    source=SimpleNamespace(url='https://www.fca.org.uk/news/press-releases/report',text='A newly published original financial report.',evidence_sha256='a'*64)
    item={'url':source.url,'title':'FCA publishes a new financial reporting policy','source':'FCA','category':'Regulation','dateISO':'2026-10-25'}
    ledger={};meter=CallBudget(ledger)
    decision={'selected':[{'id':'N01','reason':'Substantive new financial reporting announcement.'}],'skipped':[]}
    called=[]
    def ai(prompt):called.append(prompt);return copy.deepcopy(decision)
    picked,report=choose([(item,source)],ledger,meter,ai,edition_date='2026-10-25')
    assert len(picked)==1 and len(called)==1 and report['requests']==1
    _,cached=choose([(item,source)],ledger,meter,ai,edition_date='2026-10-25')
    assert cached['requests']==0 and len(called)==1
    assert choose([],ledger,meter,ai,edition_date='2026-10-25')[1]['requests']==0
    variants=[{'selected':[{'id':'N99','reason':'An invented candidate must be rejected.'}],'skipped':[]},
              {'selected':[],'skipped':[]},
              {'selected':decision['selected']*2,'skipped':[]},
              {'selected':[{'id':'N01','reason':'yes'}],'skipped':[]}]
    for bad in variants:
        state={};budget=CallBudget(state)
        try:choose([(item,source)],state,budget,lambda p:bad,edition_date='2026-10-25')
        except ValueError:pass
        else:raise AssertionError('Invalid selection passed')
        try:choose([(item,source)],state,budget,lambda p:(_ for _ in ()).throw(AssertionError('Repeated bad pool spent another request')),edition_date='2026-10-25')
        except ValueError:pass
        else:raise AssertionError('Invalid pool was retried')
    low=CallBudget({},per_run=2)
    try:choose([(item,source)],{},low,ai,edition_date='2026-10-25')
    except ValueError:pass
    else:raise AssertionError('Selection consumed a reserved writer/reviewer request')
    assert low.run_used==0
    rejected={'selected':[],'skipped':[{'id':'N01','reason':'Routine publicity with no substantive new development.'}]}
    assert not choose([(item,source)],{},CallBudget({}),lambda p:rejected,edition_date='2026-10-25')[0]
    print('PASS: Gemini selects, can reject all, cannot invent/omit/duplicate sources; cache, invalid-response stop and pair reservation')

if __name__=='__main__':main()
