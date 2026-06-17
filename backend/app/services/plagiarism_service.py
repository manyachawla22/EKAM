import io
import re
from uuid import UUID

import pdfplumber
from fastapi import HTTPException, UploadFile, status
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report as ReportModel


_EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception:
        return ""


async def manual_plagiarism_check_service(
    db: AsyncSession,
    event_id: UUID,
    file_1: UploadFile,
    file_2: UploadFile,
    threshold: float = 0.75,
):
    if threshold <= 0 or threshold > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold must be greater than 0 and less than or equal to 1",
        )

    if not file_1.filename or not file_2.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both files are required",
        )

    if not file_1.filename.lower().endswith(".pdf") or not file_2.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for manual plagiarism check",
        )

    file_1_bytes = await file_1.read()
    file_2_bytes = await file_2.read()

    text_1 = _normalize_text(_extract_text_from_pdf_bytes(file_1_bytes))[:50000]
    text_2 = _normalize_text(_extract_text_from_pdf_bytes(file_2_bytes))[:50000]

    if not text_1 or not text_2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract readable text from both PDFs",
        )

    embeddings = _EMBED_MODEL.encode(
        [text_1, text_2],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
    suspicious = similarity >= threshold

    report_data = {
        "file_1_name": file_1.filename,
        "file_2_name": file_2.filename,
        "similarity": round(similarity, 4),
        "threshold": threshold,
        "suspicious": suspicious,
        "method": "semantic_embeddings_cosine_similarity",
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "text_1_preview": text_1[:500],
        "text_2_preview": text_2[:500],
    }

    report = ReportModel(
        event_id=event_id,
        title=f"Manual Plagiarism Check — {file_1.filename} vs {file_2.filename}",
        type="manual_plagiarism",
        data=report_data,
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report
