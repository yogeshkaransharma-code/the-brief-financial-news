"""Measured multi-day reliability; unobserved weekdays/weekends never pass."""
import collections
import datetime as dt
from same_day_policy import clock

def evaluate(history):
    days={};scheduled=[]
    for row in history:
        if row.get('event')!='schedule':continue
        try:stamp=dt.datetime.fromisoformat(row['checked_at'])
        except (KeyError,TypeError,ValueError):continue
        day=clock(stamp).date();key=day.isoformat()
        bucket=days.setdefault(key,{'weekend':day.weekday()>=5,'cycles':0,'live_verified_cycles':0,
                                    'articles_published':0,'articles_visible':0,'outcomes':{}})
        bucket['cycles']+=1;bucket['live_verified_cycles']+=row.get('technical_status')=='LIVE_VERIFIED'
        bucket['articles_published']+=row.get('published_this_run',0) or 0
        bucket['articles_visible']+=row.get('articles_visible_this_run',0) or 0
        result=row.get('editorial_outcome','UNKNOWN');bucket['outcomes'][result]=bucket['outcomes'].get(result,0)+1
        scheduled.append(stamp)
    scheduled=sorted(set(scheduled));gaps=[(b-a).total_seconds()/60 for a,b in zip(scheduled,scheduled[1:])]
    weekday=any(not d['weekend'] for d in days.values());weekend=any(d['weekend'] for d in days.values())
    return {'observed_uk_days':len(days),'weekday_observed':weekday,'weekend_observed':weekend,
            'scheduled_cycles':len(scheduled),'max_observed_gap_minutes':max(gaps,default=None),
            'gaps_over_75_minutes':sum(g>75 for g in gaps),'days':days,
            'multi_day_reliability':'OBSERVATION_PENDING' if len(days)<7 or not (weekday and weekend) else 'SEVEN_DAY_EVIDENCE_AVAILABLE',
            'note':'Observed outcomes only. Seven days of records are evidence to review, not an automatic production-readiness certification.'}
