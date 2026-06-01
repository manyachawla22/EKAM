# backend/app/team_formation/email_triggers.py

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Optional
from datetime import datetime
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import groq
from groq import Groq

from app.models.email import EmailType
from app.models.event import Event, EventStage
from app.models.participant import Participant
from app.models.user import User
from app.services.email_service import draft_bulk_emails

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ΓöÇΓöÇΓöÇ GEMINI CONTENT DRAFTING ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def draft_email_content(email_type: str, context: dict) -> dict:
	prompt = f"""
You are EKAM, an autonomous event management system.
Draft a professional warm email for the following situation.

Email type: {email_type}
Context: {json.dumps(context, indent=2)}

Return ONLY valid JSON, no markdown, no backticks:
{
	"subject": "...",
	"body_text": "plain text version",
	"body_html": "<p>html version</p>"
}

Rules:
- Use actual names from context, never write [Name] or placeholders
- Be concise and warm
- Sign off as Team EKAM
"""
	response = client.models.generate_content(
		model="gemini-1.5-flash-latest",
		contents=prompt
	)
	raw = response.text.strip()
	try:
		return json.loads(raw)
	except json.JSONDecodeError:
		start = raw.find("{")
		end = raw.rfind("}") + 1
		return json.loads(raw[start:end])


def _clean_groq_html(raw: str) -> str:
	if raw.startswith("```html"):
		raw = raw[7:]
	elif raw.startswith("```"):
		raw = raw[3:]
	if raw.endswith("```"):
		raw = raw[:-3]
	return raw.strip()


def _certificate_label_for_stage(stage_name: str) -> str:
	mapping = {
		"Registration Open": "Registration Confirmed",
		"Registration Closed": "Participant Registered",
		"OA Round": "OA Round Completion",
		"Team Formation": "Team Formation",
		"Submission Round": "Submission Completed",
		"Evaluation Round": "Evaluation Completed",
		"Results Generated": "Results Generated",
		"Event Completed": "Event Completed",
	}
	return mapping.get(stage_name, "Participation")


def generate_certificate_html(
	participant_name: str,
	competition_name: str,
	achievement: str = "Participation",
	date: str = ""
) -> str:
	api_key = os.environ.get("GROQ_API_KEY", "")
	if not api_key:
		raise RuntimeError("GROQ_API_KEY not configured in environment")

	if not date:
		date = datetime.now().strftime("%B %d, %Y")

	client = Groq(api_key=api_key)
	prompt = f"""
You are a professional certificate designer. Generate ONLY valid HTML for a printable certificate.
Recipient: {participant_name}
Competition: {competition_name}
Achievement: {achievement}
Date: {date}

Include a small line describing the stage the participant reached, such as "Stage reached: {achievement}".

The certificate should include:
- the competition name clearly visible
- the recipient name prominently displayed
- the achievement title
- the stage reached description
- an elegant border and typography
- a signature line for the organizer
- inline CSS so the file can be opened by itself

Return ONLY the HTML content and no markdown, no code fences, no surrounding text.
"""

	response = client.chat.completions.create(
		model="mixtral-8x7b-32768",
		messages=[
			{"role": "system", "content": "You are a professional certificate designer. Return only HTML."},
			{"role": "user", "content": prompt},
		],
		temperature=0.25,
		max_tokens=1600,
	)

	raw_html = ""
	if response.choices and response.choices[0].message:
		raw_html = response.choices[0].message.content or ""
	else:
		raw_html = str(response)

	return _clean_groq_html(raw_html)


def send_email_smtp(
	recipient_email: str,
	subject: str,
	body_html: str,
	body_text: str,
	attachments: Optional[Dict[str, bytes]] = None,
) -> bool:
	smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
	smtp_port = int(os.environ.get("SMTP_PORT", "587"))
	smtp_username = os.environ.get("SMTP_USERNAME", "")
	smtp_password = os.environ.get("SMTP_PASSWORD", "")
	sender_email = os.environ.get("SENDER_EMAIL", smtp_username)
	sender_name = os.environ.get("SENDER_NAME", "EKAM")

	if not smtp_username or not smtp_password or not sender_email:
		raise RuntimeError("SMTP credentials are not configured")

	msg = MIMEMultipart("mixed")
	msg["Subject"] = subject
	msg["From"] = f"{sender_name} <{sender_email}>"
	msg["To"] = recipient_email

	alternative = MIMEMultipart("alternative")
	alternative.attach(MIMEText(body_text, "plain"))
	alternative.attach(MIMEText(body_html, "html"))
	msg.attach(alternative)

	if attachments:
		for filename, file_bytes in attachments.items():
			part = MIMEBase("application", "octet-stream")
			part.set_payload(file_bytes)
			encoders.encode_base64(part)
			part.add_header("Content-Disposition", f"attachment; filename={filename}")
			msg.attach(part)

	with smtplib.SMTP(smtp_server, smtp_port) as server:
		server.starttls()
		server.login(smtp_username, smtp_password)
		server.send_message(msg)

	return True


async def on_certificate_distribution(
	event: Event,
	db: AsyncSession,
	requested_by: str,
	achievement: str = "Participation"
):
	result = await db.execute(
		select(User)
		.join(Participant, User.id == Participant.user_id)
		.where(
			Participant.event_id == event.id,
			Participant.status == "confirmed"
		)
	)
	users = result.scalars().all()
	if not users:
		return

	recipients = []
	sent = 0
	failed = 0

	for user in users:
		if not user.email:
			continue

		certificate_html = generate_certificate_html(
			participant_name=user.name,
			competition_name=event.name,
			achievement=achievement,
			date=datetime.now().strftime("%B %d, %Y")
		)

		subject = f"{event.name} Certificate of {achievement}"
		body_html = f"""
<html>
  <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #111;\">
	<p>Dear {user.name},</p>
	<p>Congratulations on your participation in <strong>{event.name}</strong>!</p>
	<p>Your certificate of <strong>{achievement}</strong> is attached to this email.</p>
	<p>This certificate recognizes the stage reached: <strong>{achievement}</strong>.</p>
	<p>Thank you for being part of the competition.</p>
	<p>Best regards,<br/>Team EKAM</p>
  </body>
</html>
"""
		body_text = (
			f"Dear {user.name},\n\n"
			f"Congratulations on your participation in {event.name}! "
			f"Your certificate of {achievement} is attached to this email.\n\n"
			f"This certificate recognizes the stage reached: {achievement}.\n\n"
			"Thank you for being part of the competition.\n\n"
			"Best regards,\nTeam EKAM"
		)
		attachment_name = f"certificate_{user.name.replace(' ', '_')}.html"

		try:
			send_email_smtp(
				recipient_email=user.email,
				subject=subject,
				body_html=body_html,
				body_text=body_text,
				attachments={attachment_name: certificate_html.encode("utf-8")},
			)
			sent += 1
			recipients.append(user.email)
		except Exception as exc:
			print(f"Certificate email failed for {user.email}: {exc}")
			failed += 1

	if recipients:
		await draft_bulk_emails(
			db=db,
			event_id=str(event.id),
			requested_by=requested_by,
			email_type=EmailType.certificate,
			subject=f"{event.name} Certificate of {achievement}",
			body_html="Certificates sent successfully.",
			body_text="Certificates sent successfully.",
			recipients=recipients,
		)

	print(f"Γ£ô Certificate distribution complete: {sent} sent, {failed} failed")


# ΓöÇΓöÇΓöÇ STAGE TRIGGERS ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

async def on_registration_open(
	event: Event,
	db: AsyncSession,
	requested_by: str
):
	result = await db.execute(
		select(User)
		.join(Participant, User.id == Participant.user_id)
		.where(
			Participant.event_id == event.id,
			Participant.status == "confirmed"
		)
	)
	users = result.scalars().all()
	if not users:
		return

	# draft one email per participant with their name
	# but use bulk for approval gate
	context = {
		"event_name": event.name,
		"event_description": event.description,
		"event_type": event.type,
	}
	content = draft_email_content("welcome", context)

	recipients = [user.email for user in users if user.email]
	await draft_bulk_emails(
		db=db,
		event_id=str(event.id),
		requested_by=requested_by,
		email_type=EmailType.invitation,
		subject=content["subject"],
		body_html=content["body_html"],
		body_text=content["body_text"],
		recipients=recipients
	)
	print(f"Γ£ô Welcome email batch drafted for {len(recipients)} participants")


async def on_teams_formed(
	event: Event,
	teams: list,
	db: AsyncSession,
	requested_by: str
):
	for team in teams:
		teammates_summary = ", ".join(
			f"{m['name']} ({m['institution']})"
			for m in team["members"]
		)
		context = {
			"event_name": event.name,
			"team_name": team["name"],
			"teammates": teammates_summary,
			"rationale": team.get("rationale", ""),
		}
		content = draft_email_content("team_assignment", context)
		recipients = [m["email"] for m in team["members"]]

		await draft_bulk_emails(
			db=db,
			event_id=str(event.id),
			requested_by=requested_by,
			email_type=EmailType.team_assignment,
			subject=content["subject"],
			body_html=content["body_html"],
			body_text=content["body_text"],
			recipients=recipients
		)
		print(f"Γ£ô Team assignment batch drafted for {team['name']}")


async def on_submission_stage(
	event: Event,
	db: AsyncSession,
	requested_by: str
):
	result = await db.execute(
		select(User)
		.join(Participant, User.id == Participant.user_id)
		.where(
			Participant.event_id == event.id,
			Participant.status == "confirmed"
		)
	)
	users = result.scalars().all()
	if not users:
		return

	context = {
		"event_name": event.name,
		"stage": "submission",
		"message": "The submission phase has now begun. Please submit your project before the deadline."
	}
	content = draft_email_content("stage_update", context)
	recipients = [user.email for user in users if user.email]

	await draft_bulk_emails(
		db=db,
		event_id=str(event.id),
		requested_by=requested_by,
		email_type=EmailType.stage_update,
		subject=content["subject"],
		body_html=content["body_html"],
		body_text=content["body_text"],
		recipients=recipients
	)
	print(f"Γ£ô Submission stage email batch drafted")


async def on_evaluation_stage(
	event: Event,
	judge_assignments: list,
	db: AsyncSession,
	requested_by: str
):
	for assignment in judge_assignments:
		context = {
			"judge_name": assignment["judge_name"],
			"event_name": event.name,
			"assigned_teams": assignment["teams"],
			"magic_link": assignment["magic_link"],
			"deadline": assignment.get("deadline", "TBD"),
		}
		content = draft_email_content("judge_notification", context)

		await draft_bulk_emails(
			db=db,
			event_id=str(event.id),
			requested_by=requested_by,
			email_type=EmailType.magic_link,
			subject=content["subject"],
			body_html=content["body_html"],
			body_text=content["body_text"],
			recipients=[assignment["judge_email"]]
		)
		print(f"Γ£ô Judge magic link drafted for {assignment['judge_email']}")


async def on_results_approved(
	event: Event,
	results: list,
	db: AsyncSession,
	requested_by: str
):
	context = {
		"event_name": event.name,
		"message": "Results have been announced. Check your score and feedback below."
	}
	content = draft_email_content("result", context)
	recipients = [p["email"] for p in results]

	await draft_bulk_emails(
		db=db,
		event_id=str(event.id),
		requested_by=requested_by,
		email_type=EmailType.result,
		subject=content["subject"],
		body_html=content["body_html"],
		body_text=content["body_text"],
		recipients=recipients
	)
	print(f"Γ£ô Results email batch drafted for {len(recipients)} participants")


async def on_progression(
	event: Event,
	qualifying_teams: list,
	db: AsyncSession,
	requested_by: str
):
	all_recipients = []
	for team in qualifying_teams:
		all_recipients.extend([m["email"] for m in team["members"]])

	context = {
		"event_name": event.name,
		"message": "Congratulations! Your team has qualified for the next round."
	}
	content = draft_email_content("progression", context)

	await draft_bulk_emails(
		db=db,
		event_id=str(event.id),
		requested_by=requested_by,
		email_type=EmailType.progression,
		subject=content["subject"],
		body_html=content["body_html"],
		body_text=content["body_text"],
		recipients=all_recipients
	)
	print(f"Γ£ô Progression email batch drafted for {len(all_recipients)} participants")


async def trigger_stage_emails(
	event: Event,
	new_stage: EventStage,
	db: AsyncSession,
	requested_by: str,
	extra_data: dict = {}
):
	"""
	Call this whenever event.stage changes.

	Usage:
	await trigger_stage_emails(
		event=event,
		new_stage=EventStage.team_formation,
		db=db,
		requested_by=str(current_user.id),
		extra_data={"teams": result_teams}
	)
	"""
	print(f"\n≡ƒôº Triggering emails for stage: {new_stage}")

	if new_stage == EventStage.registration_open:
		await on_registration_open(event, db, requested_by)

	elif new_stage == EventStage.team_formation:
		teams = extra_data.get("teams", [])
		if teams:
			await on_teams_formed(event, teams, db, requested_by)

	elif new_stage == EventStage.submission_round:
		await on_submission_stage(event, db, requested_by)

	elif new_stage == EventStage.evaluation_round:
		judge_assignments = extra_data.get("judge_assignments", [])
		if judge_assignments:
			await on_evaluation_stage(event, judge_assignments, db, requested_by)

	elif new_stage == EventStage.results_generated:
		achievement = _certificate_label_for_stage(new_stage.value)
		await on_certificate_distribution(event, db, requested_by, achievement)

	elif new_stage == EventStage.completed:
		results = extra_data.get("results", [])
		qualifying = extra_data.get("qualifying_teams", [])
		if results:
			await on_results_approved(event, results, db, requested_by)
		if qualifying:
			await on_progression(event, qualifying, db, requested_by)
		if extra_data.get("send_certificates"):
			achievement = extra_data.get("certificate_achievement", _certificate_label_for_stage(new_stage.value))
			await on_certificate_distribution(event, db, requested_by, achievement)

	print(f"Γ£ô All email drafts created for stage: {new_stage}\n")
