"""Ordinary verified developments commission without a model significance veto."""
from types import SimpleNamespace
from editorial_selection import choose,validate_decision
from ai_cost_guard import CallBudget

def main():
 item={'url':'https://www.fca.org.uk/news/press-releases/report','title':'FCA consults on reporting changes for small banks','source':'FCA','category':'Banking','dateISO':'2026-10-26'}
 doc=SimpleNamespace(url=item['url'],text='Accessible dated original reporting.',evidence_sha256='a'*64)
 ledger={};meter=CallBudget(ledger,per_run=2)
 def never(prompt):raise AssertionError('Commissioning wasted a model request')
 selected,report=choose([(item,doc)],ledger,meter,never,edition_date='2026-10-26')
 assert len(selected)==1 and meter.run_used==0 and report['requests']==0
 assert choose([],ledger,meter,never,edition_date='2026-10-26')[0]==[]
 assert choose([(item,doc)],ledger,meter,never,edition_date='2026-10-26',max_stories=0)[1]['deferred']
 bad=[{'selected':[{'id':'N99','reason':'Unknown source must fail validation'}],'skipped':[]}, {'selected':[],'skipped':[]}]
 for response in bad:
  try:validate_decision(response,{'N01':(item,doc)},3)
  except ValueError:pass
  else:raise AssertionError('Invalid legacy selection accepted')
 print('PASS: deterministic commissioning, no significance threshold, deferred capacity and no model request')
if __name__=='__main__':main()
