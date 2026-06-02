"""
EKAM Reports Service

Implements:
- list_reports_service        — list stored reports for an event
- create_report_service       — persist a raw report row
- generate_event_summary_report_service
      Builds a rich HTML event report (standings, score distribution,
      submission-status breakdown, per-round averages, participant
      performance) with inline SVG charts (bar + pie), stores it as a
      Report row, and emails it to the organizer.
"""

from collections import defaultdict
from statistics import mean
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, Round
from app.models.judge import Judge
from app.models.participant import Participant
from app.models.report import Report as ReportModel
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.models.team import Team, TeamMember
from app.models.anomaly import Anomaly
from app.services.email_service import send_direct_email


# =========================================================
# BASIC CRUD
# =========================================================

async def create_report_service(
    db: AsyncSession,
    report_data,
    current_user=None,
):
    """Persist a report row from a ReportCreate schema."""
    report = ReportModel(
        event_id=report_data.event_id,
        title=report_data.title,
        type=report_data.type,
        data=report_data.data or {},
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports_service(
    db: AsyncSession,
    event_id,
):
    """List all reports for an event, newest first."""
    result = await db.execute(
        select(ReportModel)
        .where(ReportModel.event_id == event_id)
        .order_by(ReportModel.created_at.desc())
    )
    return list(result.scalars().all())


# =========================================================
# SVG CHART HELPERS (no external dependencies)
# =========================================================

_PALETTE = [
    "#6366f1", "#e8503a", "#059669", "#f59e0b", "#3b82f6",
    "#a855f7", "#14b8a6", "#ef4444", "#84cc16", "#ec4899",
]


def _esc(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _bar_chart_svg(data: list[tuple[str, float]], title: str = "") -> str:
    """Horizontal bar chart as inline SVG. data = [(label, value), ...]."""
    if not data:
        return "<p style='color:#888;font-size:13px;'>No data available.</p>"

    max_value = max((value for _, value in data), default=0) or 1
    row_h = 34
    label_w = 170
    chart_w = 360
    width = label_w + chart_w + 60
    height = row_h * len(data) + 20

    rows = []
    for index, (label, value) in enumerate(data):
        y = 10 + index * row_h
        bar_w = max(2, (value / max_value) * chart_w)
        color = _PALETTE[index % len(_PALETTE)]
        rows.append(
            f'<text x="0" y="{y + 18}" font-size="13" fill="#cbd5e1">'
            f'{_esc(label)[:26]}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{bar_w:.1f}" height="20" '
            f'rx="4" fill="{color}"></rect>'
            f'<text x="{label_w + bar_w + 8:.1f}" y="{y + 18}" font-size="12" '
            f'fill="#f8fafc">{value:.1f}</text>'
        )

    title_html = (
        f"<div style='font-weight:600;color:#e2e8f0;margin-bottom:6px;'>"
        f"{_esc(title)}</div>"
        if title
        else ""
    )
    return (
        f"{title_html}"
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="max-width:100%;">{"".join(rows)}</svg>'
    )


def _pie_chart_svg(data: list[tuple[str, float]], title: str = "") -> str:
    """Pie chart as inline SVG with a legend. data = [(label, value), ...]."""
    data = [(label, value) for label, value in data if value > 0]
    if not data:
        return "<p style='color:#888;font-size:13px;'>No data available.</p>"

    total = sum(value for _, value in data) or 1
    cx, cy, r = 90, 90, 80
    import math

    start_angle = -math.pi / 2  # start at top
    slices = []
    legend = []
    for index, (label, value) in enumerate(data):
        frac = value / total
        end_angle = start_angle + frac * 2 * math.pi
        x1 = cx + r * math.cos(start_angle)
        y1 = cy + r * math.sin(start_angle)
        x2 = cx + r * math.cos(end_angle)
        y2 = cy + r * math.sin(end_angle)
        large = 1 if frac > 0.5 else 0
        color = _PALETTE[index % len(_PALETTE)]
        if len(data) == 1:
            slices.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"></circle>'
            )
        else:
            slices.append(
                f'<path d="M{cx},{cy} L{x1:.2f},{y1:.2f} '
                f'A{r},{r} 0 {large},1 {x2:.2f},{y2:.2f} Z" '
                f'fill="{color}"></path>'
            )
        legend.append(
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'font-size:12px;color:#cbd5e1;margin:2px 0;">'
            f'<span style="width:10px;height:10px;border-radius:2px;'
            f'background:{color};display:inline-block;"></span>'
            f'{_esc(label)} — {value:.0f} ({frac * 100:.0f}%)</div>'
        )
        start_angle = end_angle

    title_html = (
        f"<div style='font-weight:600;color:#e2e8f0;margin-bottom:6px;'>"
        f"{_esc(title)}</div>"
        if title
        else ""
    )
    return (
        f"{title_html}"
        f'<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">'
        f'<svg width="180" height="180" viewBox="0 0 180 180" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(slices)}</svg>'
        f'<div>{"".join(legend)}</div></div>'
    )


# =========================================================
# EVENT SUMMARY REPORT
# =========================================================

def _evaluation_score(evaluation: Evaluation) -> float | None:
    raw = getattr(evaluation, "total_score", None)
    if raw is None:
        raw = getattr(evaluation, "score", None)
    return None if raw is None else float(raw)


async def _gather_event_data(db: AsyncSession, event_id: UUID) -> dict:
    event = (
        await db.execute(select(Event).where(Event.id == event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    rounds = (
        await db.execute(
            select(Round).where(Round.event_id == event_id).order_by(Round.created_at)
        )
    ).scalars().all()

    teams = (
        await db.execute(select(Team).where(Team.event_id == event_id))
    ).scalars().all()

    participants = (
        await db.execute(
            select(Participant).where(Participant.event_id == event_id)
        )
    ).scalars().all()

    judges = (
        await db.execute(select(Judge).where(Judge.event_id == event_id))
    ).scalars().all()

    # Submissions + their round, scoped to this event.
    submission_rows = (
        await db.execute(
            select(Submission, Round)
            .join(Round, Submission.round_id == Round.id)
            .where(Round.event_id == event_id)
        )
    ).all()

    submissions = [s for s, _ in submission_rows]
    submission_ids = [s.id for s in submissions]

    evaluations = []
    if submission_ids:
        evaluations = (
            await db.execute(
                select(Evaluation).where(
                    Evaluation.submission_id.in_(submission_ids)
                )
            )
        ).scalars().all()

    anomalies = (
        await db.execute(select(Anomaly).where(Anomaly.event_id == event_id))
    ).scalars().all()

    team_members = (
        await db.execute(
            select(TeamMember, Team)
            .join(Team, TeamMember.team_id == Team.id)
            .where(Team.event_id == event_id)
        )
    ).all()

    return {
        "event": event,
        "rounds": rounds,
        "teams": teams,
        "participants": participants,
        "judges": judges,
        "submission_rows": submission_rows,
        "submissions": submissions,
        "evaluations": evaluations,
        "anomalies": anomalies,
        "team_members": team_members,
    }


def _build_summary_html(d: dict) -> tuple[str, dict]:
    event: Event = d["event"]
    rounds: list[Round] = d["rounds"]
    teams: list[Team] = d["teams"]
    participants: list[Participant] = d["participants"]
    judges: list[Judge] = d["judges"]
    submissions: list[Submission] = d["submissions"]
    evaluations: list[Evaluation] = d["evaluations"]
    anomalies = d["anomalies"]
    team_members = d["team_members"]

    team_by_id = {t.id: t for t in teams}
    round_by_id = {r.id: r for r in rounds}

    # ---- evaluation scores ----
    all_scores = [
        s for s in (_evaluation_score(e) for e in evaluations) if s is not None
    ]

    # ---- per-submission average ----
    scores_by_submission: dict[Any, list[float]] = defaultdict(list)
    for ev in evaluations:
        score = _evaluation_score(ev)
        if score is not None:
            scores_by_submission[ev.submission_id].append(score)

    submission_avg = {
        sub.id: (
            mean(scores_by_submission[sub.id])
            if scores_by_submission.get(sub.id)
            else (sub.final_score if sub.final_score is not None else None)
        )
        for sub in submissions
    }

    # ---- team standings (avg of that team's submission scores) ----
    team_scores: dict[Any, list[float]] = defaultdict(list)
    for sub in submissions:
        avg = submission_avg.get(sub.id)
        if avg is not None:
            team_scores[sub.team_id].append(avg)

    standings = sorted(
        (
            (team_by_id.get(tid).name if team_by_id.get(tid) else str(tid)[:8],
             mean(scores))
            for tid, scores in team_scores.items()
        ),
        key=lambda x: x[1],
        reverse=True,
    )

    # ---- score distribution buckets ----
    buckets = [("0-20", 0), ("20-40", 0), ("40-60", 0), ("60-80", 0), ("80-100", 0)]
    bucket_counts = [0, 0, 0, 0, 0]
    for s in all_scores:
        idx = min(int(s // 20), 4)
        bucket_counts[idx] += 1
    distribution = [(buckets[i][0], bucket_counts[i]) for i in range(5)]

    # ---- submission status breakdown ----
    status_counts: dict[str, int] = defaultdict(int)
    for sub in submissions:
        status_counts[getattr(sub.status, "value", str(sub.status))] += 1
    status_breakdown = [(k, v) for k, v in status_counts.items()]

    # ---- per-round average ----
    round_scores: dict[Any, list[float]] = defaultdict(list)
    for sub in submissions:
        avg = submission_avg.get(sub.id)
        if avg is not None:
            round_scores[sub.round_id].append(avg)
    per_round = [
        (round_by_id.get(rid).name if round_by_id.get(rid) else str(rid)[:8],
         mean(scores))
        for rid, scores in round_scores.items()
    ]

    # ---- participant performance ----
    team_of_participant: dict[Any, Team] = {}
    for tm, team in team_members:
        team_of_participant[tm.participant_id] = team

    participant_rows = []
    for p in participants:
        team = team_of_participant.get(p.id)
        team_avg = (
            mean(team_scores[team.id]) if team and team_scores.get(team.id) else None
        )
        participant_rows.append(
            {
                "name": p.name,
                "email": p.email,
                "team": team.name if team else "—",
                "score": team_avg,
            }
        )
    participant_rows.sort(
        key=lambda r: (r["score"] if r["score"] is not None else -1), reverse=True
    )

    # ---- headline stats ----
    stats = {
        "participants": len(participants),
        "teams": len(teams),
        "judges": len(judges),
        "rounds": len(rounds),
        "submissions": len(submissions),
        "evaluations": len(evaluations),
        "anomalies": len(anomalies),
        "average_score": round(mean(all_scores), 1) if all_scores else 0.0,
    }

    # ---- charts ----
    standings_chart = _bar_chart_svg(standings[:10], "Top Teams by Average Score")
    distribution_chart = _bar_chart_svg(
        [(label, float(count)) for label, count in distribution],
        "Score Distribution (evaluations)",
    )
    status_chart = _pie_chart_svg(
        [(label, float(count)) for label, count in status_breakdown],
        "Submission Status",
    )
    round_chart = _bar_chart_svg(per_round, "Average Score per Round")

    # ---- standings table ----
    standings_rows = "".join(
        f"<tr><td style='padding:6px 10px;'>{i + 1}</td>"
        f"<td style='padding:6px 10px;'>{_esc(name)}</td>"
        f"<td style='padding:6px 10px;font-weight:600;color:#e8503a;'>"
        f"{score:.1f}</td></tr>"
        for i, (name, score) in enumerate(standings[:15])
    ) or "<tr><td colspan='3' style='padding:10px;color:#888;'>No scored teams yet.</td></tr>"

    participant_table_parts = []
    for r in participant_rows:
        score_text = f"{r['score']:.1f}" if r["score"] is not None else "—"
        participant_table_parts.append(
            f"<tr><td style='padding:6px 10px;'>{_esc(r['name'])}</td>"
            f"<td style='padding:6px 10px;color:#94a3b8;'>{_esc(r['email'])}</td>"
            f"<td style='padding:6px 10px;'>{_esc(r['team'])}</td>"
            f"<td style='padding:6px 10px;font-weight:600;'>{score_text}</td></tr>"
        )
    participant_table_rows = "".join(participant_table_parts) or (
        "<tr><td colspan='4' style='padding:10px;color:#888;'>No participants.</td></tr>"
    )

    def stat_card(label: str, value: Any) -> str:
        return (
            f"<div style='flex:1;min-width:120px;padding:14px 16px;border:1px "
            f"solid #1f2937;border-radius:12px;background:#0f172a;'>"
            f"<div style='font-size:22px;font-weight:800;color:#f8fafc;'>{value}</div>"
            f"<div style='font-size:12px;color:#94a3b8;'>{label}</div></div>"
        )

    cards = "".join([
        stat_card("Participants", stats["participants"]),
        stat_card("Teams", stats["teams"]),
        stat_card("Judges", stats["judges"]),
        stat_card("Submissions", stats["submissions"]),
        stat_card("Evaluations", stats["evaluations"]),
        stat_card("Avg Score", stats["average_score"]),
        stat_card("Anomalies", stats["anomalies"]),
    ])

    section_style = (
        "margin:24px 0;padding:18px;border:1px solid #1f2937;"
        "border-radius:14px;background:#0b1220;"
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Event Report — {_esc(event.name)}</title></head>
<body style="margin:0;background:#020617;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;">
<div style="max-width:900px;margin:0 auto;padding:28px;">
  <div style="padding:24px;border-radius:16px;background:linear-gradient(135deg,#4338ca,#e8503a);color:#fff;">
    <h1 style="margin:0;font-size:26px;">Event Summary Report</h1>
    <p style="margin:6px 0 0;font-size:15px;opacity:0.9;">{_esc(event.name)} · {_esc(event.type)} · stage: {_esc(getattr(event.stage, 'value', event.stage))}</p>
  </div>

  <div style="display:flex;gap:12px;flex-wrap:wrap;margin:22px 0;">{cards}</div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">🏆 Final Standings</h2>
    {standings_chart}
    <table style="width:100%;border-collapse:collapse;margin-top:14px;font-size:13px;">
      <thead><tr style="text-align:left;color:#94a3b8;border-bottom:1px solid #1f2937;">
        <th style="padding:6px 10px;">#</th><th style="padding:6px 10px;">Team</th><th style="padding:6px 10px;">Avg Score</th>
      </tr></thead>
      <tbody>{standings_rows}</tbody>
    </table>
  </div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">📊 Score Distribution</h2>
    {distribution_chart}
  </div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">🥧 Submission Status</h2>
    {status_chart}
  </div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">📈 Average Score per Round</h2>
    {round_chart}
  </div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">👥 Participant Performance</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="text-align:left;color:#94a3b8;border-bottom:1px solid #1f2937;">
        <th style="padding:6px 10px;">Participant</th><th style="padding:6px 10px;">Email</th>
        <th style="padding:6px 10px;">Team</th><th style="padding:6px 10px;">Team Avg</th>
      </tr></thead>
      <tbody>{participant_table_rows}</tbody>
    </table>
  </div>

  <div style="{section_style}">
    <h2 style="margin:0 0 12px;font-size:17px;">⚠️ Anomaly Detection</h2>
    <p style="font-size:13px;color:#cbd5e1;margin:0;">
      {stats['anomalies']} scoring {'anomaly' if stats['anomalies'] == 1 else 'anomalies'}
      flagged by the IsolationForest ML model across {stats['evaluations']} evaluations.
    </p>
  </div>

  <p style="text-align:center;color:#475569;font-size:12px;margin-top:28px;">
    Generated by EKAM · Team EKAM
  </p>
</div></body></html>"""

    return html, stats


async def generate_event_summary_report_service(
    db: AsyncSession,
    event_id: UUID,
    requested_by: str | None = None,
):
    """Build, store, and email the event summary report to the organizer."""
    data = await _gather_event_data(db, event_id)
    event: Event = data["event"]

    report_html, stats = _build_summary_html(data)

    report = ReportModel(
        event_id=event_id,
        title=f"Event Summary — {event.name}",
        type="event_summary",
        data={"report_html": report_html, "statistics": stats},
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Email the organizer (best-effort; never blocks report creation).
    try:
        from app.models.user import User

        organizer = (
            await db.execute(select(User).where(User.id == event.organizer_id))
        ).scalars().first()

        if organizer and getattr(organizer, "email", None):
            await send_direct_email(
                to=organizer.email,
                subject=f"[EKAM] Event Summary Report — {event.name}",
                body_html=report_html,
                body_text=(
                    f"Your event summary report for {event.name} is ready. "
                    f"Open this email in an HTML-capable client to view the "
                    f"charts, or view it on the EKAM Reports page."
                ),
                attachments={
                    f"event_report_{event.id}.html": report_html.encode("utf-8")
                },
            )
    except Exception as exc:
        print(f"[report_service] organizer email failed: {exc}")

    return report
