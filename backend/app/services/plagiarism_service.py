import os
import re
from typing import Any
from urllib.parse import urlparse

import pdfplumber
import requests
from fastapi import HTTPException, status
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Round
from app.models.report import Report as ReportModel
from app.models.submission import Submission, SubmissionStatus


TEXT_FILE_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".sql",
    ".sh",
}


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _safe_get(url: str, timeout: int = 10) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "EKAM-Plagiarism-Detector/1.0"},
    )
    response.raise_for_status()
    return response.text


def _extract_text_from_pdf(path: str) -> str:
    try:
        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception:
        return ""


def _extract_text_from_local_file(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        return _extract_text_from_pdf(path)

    if extension in TEXT_FILE_EXTENSIONS:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                return file.read()
        except Exception:
            return ""

    return ""


def _extract_text_from_github_blob_or_raw(url: str) -> str:
    """
    Supports:
    - raw.githubusercontent.com/... direct file links
    - github.com/.../blob/... file links
    """
    try:
        if "raw.githubusercontent.com" in url:
            return _safe_get(url)

        if "github.com" in url and "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            return _safe_get(raw_url)
    except Exception:
        return ""

    return ""


def _github_repo_parts(url: str) -> tuple[str, str] | None:
    """
    Extract owner/repo from:
    https://github.com/<owner>/<repo>
    """
    try:
        parsed = urlparse(url)
        if "github.com" not in parsed.netloc:
            return None

        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            return None

        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]

        return owner, repo
    except Exception:
        return None


def _extract_text_from_github_repo(url: str, max_files: int = 12, max_chars: int = 20000) -> str:
    """
    Reads a limited number of text-like files from a public GitHub repo
    using the GitHub API. Keeps it lightweight and safe.
    """
    repo_parts = _github_repo_parts(url)
    if not repo_parts:
        return ""

    owner, repo = repo_parts

    try:
        repo_meta = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            timeout=10,
            headers={"User-Agent": "EKAM-Plagiarism-Detector/1.0"},
        )
        repo_meta.raise_for_status()
        default_branch = repo_meta.json().get("default_branch", "main")

        tree_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            timeout=15,
            headers={"User-Agent": "EKAM-Plagiarism-Detector/1.0"},
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])

        selected_paths = []
        for item in tree:
            if item.get("type") != "blob":
                continue

            path = item.get("path", "")
            ext = os.path.splitext(path)[1].lower()

            if ext in TEXT_FILE_EXTENSIONS and not path.startswith((".github/", "node_modules/", "dist/", "build/")):
                selected_paths.append(path)

            if len(selected_paths) >= max_files:
                break

        text_chunks: list[str] = []
        total_chars = 0

        for path in selected_paths:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
            try:
                content = _safe_get(raw_url, timeout=10)
            except Exception:
                continue

            if not content:
                continue

            remaining = max_chars - total_chars
            if remaining <= 0:
                break

            chunk = f"\n\n# FILE: {path}\n{content[:remaining]}"
            text_chunks.append(chunk)
            total_chars += len(chunk)

            if total_chars >= max_chars:
                break

        return "\n".join(text_chunks)
    except Exception:
        return ""


def _extract_text_from_url(url: str) -> str:
    # GitHub direct file links first
    blob_or_raw = _extract_text_from_github_blob_or_raw(url)
    if blob_or_raw:
        return blob_or_raw

    # GitHub repo links
    if "github.com" in url:
        repo_text = _extract_text_from_github_repo(url)
        if repo_text:
            return repo_text

    # Direct text file URL fallback
    extension = os.path.splitext(urlparse(url).path)[1].lower()
    if extension in TEXT_FILE_EXTENSIONS:
        try:
            return _safe_get(url)
        except Exception:
            return ""

    return ""


def _extract_attachment_text(attachment: str) -> str:
    if not attachment:
        return ""

    if _is_url(attachment):
        return _extract_text_from_url(attachment)

    if os.path.exists(attachment):
        return _extract_text_from_local_file(attachment)

    return ""


def _extract_submission_text(attachments: list[str]) -> str:
    parts: list[str] = []

    for attachment in attachments or []:
        extracted = _extract_attachment_text(attachment)
        if extracted:
            parts.append(extracted)

    text = "\n\n".join(parts)
    return _normalize_text(text)[:50000]


async def detect_plagiarism_service(
    db: AsyncSession,
    event_id: str,
    threshold: float = 0.8,
):
    if threshold <= 0 or threshold > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold must be greater than 0 and less than or equal to 1",
        )

    result = await db.execute(
        select(Submission, Round)
        .join(Round, Submission.round_id == Round.id)
        .where(Round.event_id == event_id)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submissions found for the requested event",
        )

    usable_submissions: list[dict[str, Any]] = []

    for submission, round_obj in rows:
        extracted_text = _extract_submission_text(submission.attachments or [])
        if not extracted_text:
            continue

        usable_submissions.append(
            {
                "submission": submission,
                "round": round_obj,
                "text": extracted_text,
            }
        )

    if len(usable_submissions) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 readable submissions for plagiarism detection",
        )

    corpus = [item["text"] for item in usable_submissions]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarity_matrix = cosine_similarity(tfidf_matrix)

    suspicious_pairs: list[dict[str, Any]] = []
    flagged_submission_ids = set()

    for i in range(len(usable_submissions)):
        for j in range(i + 1, len(usable_submissions)):
            similarity_score = float(similarity_matrix[i][j])

            if similarity_score < threshold:
                continue

            submission_i = usable_submissions[i]["submission"]
            submission_j = usable_submissions[j]["submission"]
            round_i = usable_submissions[i]["round"]
            round_j = usable_submissions[j]["round"]

            suspicious_pairs.append(
                {
                    "submission_1_id": str(submission_i.id),
                    "submission_2_id": str(submission_j.id),
                    "team_1_id": str(submission_i.team_id),
                    "team_2_id": str(submission_j.team_id),
                    "round_1_id": str(round_i.id),
                    "round_2_id": str(round_j.id),
                    "similarity": round(similarity_score, 4),
                    "threshold": threshold,
                    "attachments_1": submission_i.attachments or [],
                    "attachments_2": submission_j.attachments or [],
                }
            )

            flagged_submission_ids.add(submission_i.id)
            flagged_submission_ids.add(submission_j.id)

    for item in usable_submissions:
        submission = item["submission"]
        if submission.id in flagged_submission_ids:
            submission.status = SubmissionStatus.flagged

    report_data = {
        "pairs": suspicious_pairs,
        "summary": {
            "total_submissions_scanned": len(usable_submissions),
            "flagged_pairs": len(suspicious_pairs),
            "flagged_submissions": len(flagged_submission_ids),
            "threshold": threshold,
            "method": "tfidf_cosine_similarity",
        },
    }

    report = ReportModel(
        event_id=event_id,
        title="Plagiarism Detection Report",
        type="plagiarism",
        data=report_data,
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report