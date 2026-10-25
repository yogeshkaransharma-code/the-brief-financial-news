"""Persist the observed end-to-end outcome after deployment; never infer it from article creation."""
import datetime as dt
import json
import os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
state_path=root/'data/status.json'
state=json.loads(state_path.read_text()) if state_path.exists() else {}
passed=os.getenv('BRIEF_TECHNICAL_SUCCESS')=='true'
record={k:state.get(k) for k in ['run_id','event','run_url','editorial_outcome','published_this_run','publisher_links','source_coverage_status','fresh_source_candidates','verified_by_sector','ai_budget']}
record['commissioned_stories']=state.get('editorial_selection',{}).get('selected',[])
record.update(checked_at=dt.datetime.now(dt.timezone.utc).isoformat(),technical_status='LIVE_VERIFIED' if passed else 'FAILED',
              deployment=os.getenv('BRIEF_DEPLOYMENT_RESULT','unknown'),live_check=os.getenv('BRIEF_LIVE_RESULT','unknown'),browser_check=os.getenv('BRIEF_BROWSER_RESULT','unknown'))
path=root/'data/run-history.json'
try:history=json.loads(path.read_text())
except (OSError,ValueError):history=[]
history=[x for x in history if x.get('run_id')!=record.get('run_id')]
history.append(record)
from launch_acceptance import evaluate
acceptance=evaluate(history)
(root/'data/launch-acceptance.json').write_text(json.dumps(acceptance,ensure_ascii=False,indent=2)+'\n')
path.write_text(json.dumps(history[-168:],ensure_ascii=False,indent=2)+'\n')
if os.getenv('GITHUB_STEP_SUMMARY'):
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
  f.write('\n## End-to-end result\n\n'+json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('END_TO_END_RESULT:',json.dumps(record))
