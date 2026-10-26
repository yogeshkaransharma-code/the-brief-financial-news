"""Independent Actions watchdog: detect stale/failed cycles and dispatch recovery.

GitHub scheduling is best effort. This adds a second schedule and bounded
recovery on workflow completion; it cannot guarantee service during a GitHub outage.
"""
import datetime as dt
import json
import os
import urllib.request

def decision(runs,now):
    active=[r for r in runs if r.get('status') in {'queued','in_progress','waiting','pending','requested'}]
    if active:return False,'A newsroom run is already queued or active'
    completed=sorted(runs,key=lambda r:r['created_at'],reverse=True)
    if not completed:return True,'No newsroom run found'
    latest=completed[0];age=now-dt.datetime.fromisoformat(latest['created_at'].replace('Z','+00:00'))
    recent=[r for r in runs if now-dt.datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))<dt.timedelta(hours=1)]
    recoveries=[r for r in recent if r.get('event')=='workflow_dispatch']
    if len(recoveries)>=2:return False,'Two recovery attempts this hour; bounded retry limit reached'
    if latest.get('conclusion') in {'failure','cancelled','timed_out','action_required'}:
        return True,'Last newsroom run failed or was interrupted'
    if age>dt.timedelta(minutes=65):return True,'No newsroom cycle started within 65 minutes'
    return False,'Latest cycle is recent; editorial output is monitored separately'

def main():
    repo=os.environ['GITHUB_REPOSITORY'];token=os.environ['GH_TOKEN']
    base='https://api.github.com/repos/'+repo
    def api(path,payload=None):
        req=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,
          headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=20) as response:
            data=response.read()
            return json.loads(data) if data else None
    runs=api('/actions/workflows/ai-newsroom.yml/runs?branch=main&per_page=50')['workflow_runs']
    launch,reason=decision(runs,dt.datetime.now(dt.timezone.utc))
    if launch and runs and runs[0].get('conclusion')=='failure':
        jobs=api('/actions/runs/'+str(runs[0]['id'])+'/jobs')['jobs']
        if any(j.get('name')=='Discover, verify and maintain publication' and j.get('conclusion')=='success' for j in jobs):
            launch=False;reason='Cycle completed; editorial blockage is recorded and will retry on schedule'
    report={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'dispatch':launch,'reason':reason}
    if launch:api('/actions/workflows/ai-newsroom.yml/dispatches',{'ref':'main'})
    print('SCHEDULE_RECOVERY:',json.dumps(report))
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('\nSchedule watchdog: '+json.dumps(report)+'\n')

if __name__=='__main__':main()
