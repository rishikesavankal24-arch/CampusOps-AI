"""Knowledge Base ingestion, chunking, deduplication, and vector storage service."""

import hashlib
import logging
import re
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge_base import KBCategory, KnowledgeBase
from app.schemas.knowledge import KnowledgeIngestResponse
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text for deduplication."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def split_text_into_chunks(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[str]:
    """Split text into semantically cohesive overlapping chunks.
    
    Prefers paragraph and sentence boundaries before hard slicing.
    """
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    # Split by double newlines (paragraphs) first
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If paragraph itself exceeds chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {sent}".strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    # If overlapping is needed and chunks > 1, add context from previous chunk
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped_chunks: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-chunk_overlap:]
            # Avoid duplicating partial words cleanly
            overlapped_chunks.append(f"...{prev_tail}\n{chunks[i]}")
        return overlapped_chunks

    return chunks


async def ingest_document(
    db: AsyncSession,
    title: str,
    content: str,
    category: KBCategory,
    source: str | None = None,
) -> KnowledgeIngestResponse:
    """Ingest a text/markdown document into pgvector with deduplication."""
    clean_title = title.strip()
    clean_source = source.strip() if source else clean_title

    chunks = split_text_into_chunks(
        content,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    if not chunks:
        raise ValueError("Document contains no readable text content to ingest")

    ingested_count = 0
    skipped_count = 0
    total_chunks = len(chunks)

    for idx, chunk_text in enumerate(chunks):
        c_hash = compute_content_hash(chunk_text)

        # Check whether an identical chunk is already indexed in the knowledge base
        stmt = select(KnowledgeBase.id).where(
            KnowledgeBase.extra_metadata["content_hash"].as_string() == c_hash,
            KnowledgeBase.is_active.is_(True),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            skipped_count += 1
            continue

        # Generate 768-dim embedding using Gemini
        embedding = await gemini_client.get_embedding(chunk_text)

        kb_entry = KnowledgeBase(
            title=f"{clean_title} [Part {idx + 1}/{total_chunks}]" if total_chunks > 1 else clean_title,
            content=chunk_text,
            category=category,
            embedding=embedding,
            extra_metadata={
                "source": clean_source,
                "document_title": clean_title,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "content_hash": c_hash,
                "char_length": len(chunk_text),
            },
            is_active=True,
        )
        db.add(kb_entry)
        ingested_count += 1

    await db.commit()

    return KnowledgeIngestResponse(
        document_title=clean_title,
        category=category.value,
        chunks_ingested=ingested_count,
        chunks_skipped=skipped_count,
        message=f"Successfully processed {total_chunks} chunks: {ingested_count} indexed, {skipped_count} skipped (deduplicated).",
    )


# Realistic sample campus IT documents for local testing
SAMPLE_CAMPUS_IT_DOCUMENTS = [
    {
        "title": "Campus Wi-Fi (eduroam & CampusOps-Secure) Setup Guide",
        "category": KBCategory.RUNBOOK,
        "source": "campus_wifi_guide_sample.md",
        "content": """# Campus Wireless Network Configuration Guide [Sample Test Document]

## 1. Available Wireless SSIDs
The campus IT department broadcasts two primary encrypted wireless networks across academic buildings, libraries, and residence halls:
- **eduroam**: Recommended for all registered students, faculty, and visiting researchers. Provides seamless roaming across worldwide participating academic institutions.
- **CampusOps-Secure**: Dedicated high-speed campus internal network for institutional devices and lab workstations.
- **Campus-Guest**: Open web captive portal for public campus visitors (bandwidth capped at 5 Mbps, expires after 12 hours).

## 2. Authentication Credentials for Students & Staff
To connect your laptop, smartphone, or tablet to `eduroam` or `CampusOps-Secure`:
- **Username**: Your full institutional email address (e.g., `studentID@campus.edu` or `username@faculty.campus.edu`). Do NOT use just your username without the domain.
- **Password**: Your central campus Single Sign-On (SSO) account password.
- **Security Type**: WPA2-Enterprise or WPA3-Enterprise (802.1X).
- **EAP Method**: PEAP (Protected EAP).
- **Phase 2 Inner Authentication**: MSCHAPv2.
- **CA Certificate**: Select "Use system certificates" and enter domain `campus.edu`.

## 3. Troubleshooting Connection Failures
- **Issue: 'Authentication Failed' or IP Configuration Loop**:
  1. Open Wi-Fi settings and select "Forget Network" for eduroam.
  2. Verify your campus portal password has not expired (passwords expire every 180 days).
  3. Disable private MAC address / randomized MAC address for the campus Wi-Fi network to avoid MAC filtering timeouts.
- **Signal Drops in Old Science Wing**: Access points in Science Wing Block B are scheduled for 802.11ax hardware upgrade. Please use Library Central or Engineering Hall for uninterrupted high-bandwidth connectivity.""",
    },
    {
        "title": "Campus Lab Printing & PaperCut Quota Policy",
        "category": KBCategory.POLICY,
        "source": "campus_printing_policy_sample.md",
        "content": """# Campus Printing Services & PaperCut Quota Policy [Sample Test Document]

## 1. Student Printing Quotas
At the start of every academic semester (Fall and Spring), every enrolled student is credited with an institutional printing quota of **500 free monochrome pages** (or equivalent \$25.00 printing credit).
- Standard Black & White prints: 1 page credit (\$0.05 per sheet).
- Duplex (Double-sided) prints: 1.5 page credits (\$0.075 per sheet, saving 25%).
- Color printing: 5 page credits (\$0.25 per sheet, available only in Central Library Lab 2 and Student Media Center).

## 2. Web Print Submission Instructions
Students can print wirelessly from personal laptops without installing print drivers:
1. Connect to the campus network (`eduroam` or campus VPN).
2. Open your browser and navigate to the PaperCut Web Print portal: `https://print.campus.edu`.
3. Log in with your institutional student credentials.
4. Click **Web Print** > **Submit a Job**.
5. Select `Campus-FollowMe-BW` for standard black & white jobs.
6. Upload your PDF, DOCX, or PPTX file and click **Upload & Complete**.
7. Walk to any multi-function printer on campus within 4 hours, tap your Student ID card on the card reader, and release your print job.

## 3. Printer Physical Locations
- **Central Library Ground Floor**: 4 high-capacity monochrome copiers and 1 color station.
- **Engineering Hall 3rd Floor Lab**: 2 monochrome laser printers.
- **Graduate Study Commons**: 1 silent laser printer.
- **Student Center Atrium**: 2 self-service kiosks.""",
    },
    {
        "title": "Campus Portal & Single Sign-On Password Policy",
        "category": KBCategory.POLICY,
        "source": "account_security_policy_sample.md",
        "content": """# Institutional Identity & Password Security Policy [Sample Test Document]

## 1. Password Complexity Rules
All student and employee accounts accessing the CampusOps AI Portal, Learning Management System (LMS), and email must adhere to strict security parameters:
- Minimum length: **8 characters** (12+ characters strongly recommended).
- Must contain at least one uppercase letter (A-Z) and one lowercase letter (a-z).
- Must contain at least one numeral (0-9) or allowable special symbol (`!@#$%^&*()`).
- Cannot reuse any of your last 5 previous passwords.
- Passwords must be refreshed every 180 days.

## 2. Account Lockout Protection
To safeguard university infrastructure from automated credential stuffing and brute-force attacks:
- Accounts are automatically locked for **30 minutes** after **5 consecutive incorrect password attempts**.
- Lockouts clear automatically after 30 minutes, or can be unlocked immediately by contacting the IT Helpdesk.

## 3. Password Reset Procedure
- Self-service password reset is handled exclusively through authenticated institutional MFA.
- If you have lost access to your secondary MFA device, you must present your physical Student or Faculty ID card in person at the **IT Service Desk located in Central Library Ground Floor (Mon-Fri 08:00 - 18:00)**.
- For security reasons, IT Support staff will never ask for your password via email, phone, or direct message.""",
    },
    {
        "title": "Campus Virtual Private Network (VPN) Remote Access Runbook",
        "category": KBCategory.RUNBOOK,
        "source": "campus_vpn_runbook_sample.md",
        "content": """# Campus Remote Access VPN Runbook [Sample Test Document]

## 1. Purpose & Eligibility
The Campus Virtual Private Network (VPN) allows authorized students, faculty, and researchers to securely access restricted campus resources from off-campus locations:
- Licensed academic research databases and IEEE / ACM digital libraries.
- Departmental Linux compute clusters and research GPU nodes.
- Internal administrative portals and student file shares (`smb://files.campus.edu`).

## 2. Client Setup & Connection Instructions
1. Download the official campus VPN client installer from `https://vpn.campus.edu`.
2. Supported platforms: Windows 11/10, macOS (12+), Ubuntu LTS (22.04+), iOS, and Android.
3. Server Gateway Address: `vpn-gateway.campus.edu`.
4. Authentication Protocol: Enter your campus institutional email and SSO password.
5. Multi-Factor Authentication (MFA): Approve the notification sent to your registered authenticator mobile app.

## 3. Bandwidth Policies & Restrictions
- The VPN uses split-tunneling by default. Only traffic destined for university subnets (`10.0.0.0/8` and `172.16.0.0/12`) is routed over the campus tunnel.
- General consumer internet browsing, streaming video services (Netflix, YouTube), and peer-to-peer torrents are not routed through the VPN.""",
    },
]


async def seed_sample_it_knowledge(db: AsyncSession) -> list[KnowledgeIngestResponse]:
    """Seed sample campus IT documents into the database for demonstration and testing."""
    results: list[KnowledgeIngestResponse] = []
    for doc in SAMPLE_CAMPUS_IT_DOCUMENTS:
        res = await ingest_document(
            db=db,
            title=doc["title"],
            content=doc["content"],
            category=doc["category"],
            source=doc["source"],
        )
        results.append(res)
    return results

