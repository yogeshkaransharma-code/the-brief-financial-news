"""Evidence-based launch checkpoint. Code deployment alone can never pass it."""
import datetime as dt

def evaluate(history,now=None):
 now=now or dt.datetime.now(dt.timezone.utc)
 recent=[]
 for r in history:
  try:
   stamp=dt.datetime.fromisoformat(r['checked_at'])
   if dt.timedelta(0)<=now-stamp<=dt.timedelta(hours=24):recent.append(r)
  except (ValueError,KeyError,TypeError):continue
 verified=[r for r in recent if r.get('technical_status')=='LIVE_VERIFIED']
 scheduled={r['run_id'] for r in verified if r.get('event')=='schedule'}
 sectors={story['category'] for r in verified for story in r.get('commissioned_stories',[]) if story.get('category')}
 checks={
  'repeated_scheduled_hourly_runs':len(scheduled)>=2,
  'original_gemini_publication_live_verified':any(r.get('published_this_run',0)>0 and r.get('ai_budget',{}).get('requests_this_run',0)>=2 for r in verified),
  'worthwhile_same_day_developments_across_sectors':len(sectors)>=3,
  'publisher_desk_live_refresh':any(r.get('publisher_links',0)>0 for r in verified),
  'mobile_and_desktop_reading':any(r.get('browser_check')=='success' for r in verified),
  'latest_run_technically_healthy':bool(recent and recent[-1].get('technical_status')=='LIVE_VERIFIED'),
  'latest_editorial_run_unblocked':bool(recent and recent[-1].get('editorial_outcome')!='BLOCKED'),
 }
 return {'result':'EVIDENCE_COMPLETE' if all(checks.values()) else 'EVIDENCE_PENDING',
         'checks':checks,'verified_scheduled_runs':len(scheduled),'commissioned_sectors':sorted(sectors),
         'pending':[k for k,v in checks.items() if not v],
         'note':'Operational evidence checkpoint, not a guarantee of future events or error-free journalism.'}
