import csv
import io
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session
from .models import Application, Candidate, Job, Offer, RejectionReason, StageHistory, User, now
from .security import database, recruiting
from .seed import STAGES

router = APIRouter()


def ratio(numerator, denominator):
    return round(numerator / denominator * 100, 1) if denominator else None


def report_range(start: date | None, end: date | None):
    end = end or now().date()
    start = start or end - timedelta(days=89)
    if start > end or (end-start).days > 365:
        raise HTTPException(422, 'Choose a date range of at most 366 days, with start before end.')
    return datetime.combine(start, time.min), datetime.combine(end+timedelta(days=1), time.min)


def days_between(db, end, start):
    if db.bind.dialect.name == 'sqlite':
        return func.julianday(end) - func.julianday(start)
    return func.extract('epoch', end-start) / 86400.0


def aggregates(db, start=None, end=None):
    lower, upper = report_range(start, end)
    cohort = select(Application.id).where(Application.created_at >= lower, Application.created_at < upper)
    total = db.scalar(select(func.count()).select_from(Application).where(Application.id.in_(cohort))) or 0
    current = dict(db.execute(select(Application.stage, func.count()).where(Application.id.in_(cohort)).group_by(Application.stage)).all())
    reached = dict(db.execute(select(StageHistory.to_stage, func.count(distinct(StageHistory.application_id))).where(StageHistory.application_id.in_(cohort), StageHistory.occurred_at < upper).group_by(StageHistory.to_stage)).all())
    funnel = []
    previous = None
    for stage in STAGES:
        count = reached.get(stage, 0)
        funnel.append({'stage': stage, 'count': count, 'current': current.get(stage, 0), 'conversion': ratio(count, previous) if previous is not None and stage != 'rejected' else None})
        previous = count
    first_hire = select(StageHistory.application_id.label('application_id'), func.min(StageHistory.occurred_at).label('hired_at')).where(StageHistory.to_stage == 'hired', StageHistory.occurred_at < upper).group_by(StageHistory.application_id).subquery()
    average_hire = db.scalar(select(func.avg(days_between(db, first_hire.c.hired_at, Application.created_at))).select_from(Application).join(first_hire, first_hire.c.application_id == Application.id).where(Application.id.in_(cohort)))
    ordered = select(StageHistory.to_stage.label('stage'), StageHistory.occurred_at.label('entered'), func.lead(StageHistory.occurred_at).over(partition_by=StageHistory.application_id, order_by=(StageHistory.occurred_at, StageHistory.id)).label('left')).where(StageHistory.application_id.in_(cohort), StageHistory.occurred_at < upper).subquery()
    dwell = [{'stage': stage, 'days': round(float(days), 2), 'completed_intervals': count} for stage, days, count in db.execute(select(ordered.c.stage, func.avg(days_between(db, ordered.c.left, ordered.c.entered)), func.count()).where(ordered.c.left.is_not(None)).group_by(ordered.c.stage))]
    sources = [{'source': source, 'candidates': count, 'hires': hires, 'hire_rate': ratio(hires, count)} for source, count, hires in db.execute(select(Candidate.source, func.count(), func.count(first_hire.c.application_id)).select_from(Application).join(Candidate).outerjoin(first_hire, first_hire.c.application_id == Application.id).where(Application.id.in_(cohort)).group_by(Candidate.source))]
    offer_counts = dict(db.execute(select(Offer.status, func.count()).where(Offer.application_id.in_(cohort)).group_by(Offer.status)).all())
    offers = {status: offer_counts.get(status, 0) for status in ['draft', 'sent', 'accepted', 'declined']}
    offers['acceptance_rate'] = ratio(offers['accepted'], offers['accepted']+offers['declined'])
    filled = select(Application.job_id, func.count().label('filled')).where(Application.stage == 'hired').group_by(Application.job_id).subquery()
    positions = [{'job': job, 'status': status, 'openings': openings, 'filled': count, 'remaining': max(0, openings-count)} for job, status, openings, count in db.execute(select(Job.title, Job.status, Job.openings, func.coalesce(filled.c.filled, 0)).outerjoin(filled, filled.c.job_id == Job.id).order_by(Job.id))]
    reasons = [{'reason': reason, 'count': count} for reason, count in db.execute(select(RejectionReason.label, func.count()).join(StageHistory, StageHistory.reason_id == RejectionReason.id).where(StageHistory.to_stage == 'rejected', StageHistory.occurred_at >= lower, StageHistory.occurred_at < upper).group_by(RejectionReason.id, RejectionReason.label))]
    day = func.date(StageHistory.occurred_at)
    activity = [{'date': str(day_value), 'changes': count, 'hires': hires} for day_value, count, hires in db.execute(select(day, func.count(), func.sum(case((StageHistory.to_stage == 'hired', 1), else_=0))).where(StageHistory.occurred_at >= lower, StageHistory.occurred_at < upper).group_by(day).order_by(day))]
    return {'start': lower.date().isoformat(), 'end': (upper-timedelta(days=1)).date().isoformat(), 'applications': total, 'funnel': funnel, 'average_time_to_hire': round(float(average_hire), 2) if average_hire is not None else None, 'stage_time': dwell, 'sources': sources, 'offers': offers, 'positions': positions, 'rejection_reasons': reasons, 'activity': activity, 'definitions': 'Application-created cohort, reached by range end. Time to hire uses first hire; stage time uses completed intervals only. Current stage, offers and positions are present-day snapshots. Sources count applications. Rejection/activity use event dates. Skipped or reopened stages may produce non-monotonic conversion.'}


def safe_csv_cell(value):
    if value is None:
        return ''
    text = str(value)
    probe = text.lstrip(' \t\r\n\x00\x0b\x0c')
    if probe.startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def csv_report(report):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['Section', 'Metric', 'Value', 'Additional value'])
    def write(*cells):
        writer.writerow([safe_csv_cell(x) for x in cells])
    write('Range', report['start'], report['end'])
    write('Summary', 'Applications', report['applications'])
    write('Summary', 'Average time to hire (days)', report['average_time_to_hire'])
    write('Definitions', report['definitions'])
    for item in report['funnel']:
        write('Funnel reached', item['stage'], item['count'], item['conversion'])
        write('Current stage', item['stage'], item['current'])
    for item in report['stage_time']:
        write('Completed stage intervals', item['stage'], item['days'], item['completed_intervals'])
    for item in report['sources']:
        write('Source applications / hires', item['source'], item['candidates'], item['hires'])
        write('Source hire rate (%)', item['source'], item['hire_rate'])
    for key, value in report['offers'].items():
        write('Offers', key, value)
    for item in report['positions']:
        write('Positions / filled', item['job'], item['openings'], item['filled'])
    for item in report['rejection_reasons']:
        write('Rejection reason', item['reason'], item['count'])
    for item in report['activity']:
        write('Activity changes / hires', item['date'], item['changes'], item['hires'])
    return '\ufeff' + out.getvalue()


@router.get('/reports')
def reports(start: date | None = None, end: date | None = None, user: User = Depends(recruiting), db: Session = Depends(database)):
    return aggregates(db, start, end)


@router.get('/reports/export')
def export(start: date | None = None, end: date | None = None, user: User = Depends(recruiting), db: Session = Depends(database)):
    return Response(csv_report(aggregates(db, start, end)), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="recruitboard-report.csv"'})