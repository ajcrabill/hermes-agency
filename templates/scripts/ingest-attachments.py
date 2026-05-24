#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
ingest-attachments — extract text from .docx / .pdf / .txt
attachments + log to coaching.db::ingested_files.

Mechanical layer: deterministic extraction + sha256 dedup. No
LLM reasoning. The extracted text is fed downstream into
coaching-method or stored for editor skills to consume.

Usage:
  ingest-attachments.py --profile <writing-id> --msg-id <ID> \\
                        --author-email <email>

Depends on:
  - your mail transport for attachment download
  - python-docx (or `docx2txt`) for .docx
  - pdftotext or pdfplumber for .pdf

The framework doesn't bundle these — operators install what they
need.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from _framework.coaching import (
    find_user_by_email, log_ingested_file, list_active_projects,
)
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text(path: Path) -> tuple[str, str]:
    """Return (text, format). Empty text + error format means
    extraction failed."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".txt" or suffix == ".md":
            return path.read_text(encoding="utf-8", errors="replace"), "text"
        if suffix == ".docx":
            try:
                import docx2txt   # type: ignore[import-not-found]
                return docx2txt.process(str(path)) or "", "docx"
            except ImportError:
                return "", "docx-missing-extractor"
        if suffix == ".pdf":
            # Try pdftotext binary first; fall back to pdfplumber
            import shutil, subprocess
            if shutil.which("pdftotext"):
                out = subprocess.run(
                    ["pdftotext", str(path), "-"],
                    capture_output=True, text=True, timeout=60,
                )
                if out.returncode == 0:
                    return out.stdout, "pdf"
            try:
                import pdfplumber   # type: ignore[import-not-found]
                with pdfplumber.open(str(path)) as pdf:
                    return "\n\n".join(p.extract_text() or "" for p in pdf.pages), "pdf"
            except ImportError:
                return "", "pdf-missing-extractor"
        return "", f"unsupported-format:{suffix}"
    except Exception as e:
        return "", f"extract-error:{e}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest manuscript attachments")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--msg-id", required=True)
    parser.add_argument("--author-email", required=True)
    parser.add_argument("--attachments-dir", required=True,
                        help="Directory the mail transport extracted attachments into")
    args = parser.parse_args(argv)

    user = find_user_by_email(args.author_email)
    if not user:
        append_event("ingest_skipped_unknown_author", actor=args.profile,
                     severity="warn", payload={"author_email": args.author_email})
        beat(f"{args.profile}-ingest-attachments")
        return 1

    # Find the author's most-recent active project (operator may
    # extend this to handle multi-project authors via subject parsing)
    projects = [p for p in list_active_projects() if p["user_id"] == user["id"]]
    project_id = projects[0]["id"] if projects else None

    attachments = list(Path(args.attachments_dir).iterdir())
    ingested = 0
    deduped = 0
    failed = []

    for att in attachments:
        if not att.is_file():
            continue
        sha = sha256_file(att)
        text, fmt = extract_text(att)
        if not text and not fmt.startswith("pdf-missing") and not fmt.startswith("docx-missing"):
            failed.append({"file": att.name, "reason": fmt})
            continue

        row_id = log_ingested_file(
            sha256=sha, filename=att.name, chars=len(text),
            project_id=project_id, source_msg_id=args.msg_id,
            extracted_path=str(att.parent / f"{sha}.txt"),
            metadata={"format": fmt},
        )
        if row_id is None:
            deduped += 1
        else:
            # Store extracted text
            extracted_file = att.parent / f"{sha}.txt"
            extracted_file.write_text(text, encoding="utf-8")
            ingested += 1

    severity = "warn" if failed else "info"
    append_event(
        "ingest_attachments_ran",
        actor=args.profile, target=args.msg_id, severity=severity,
        payload={
            "ingested": ingested,
            "deduped": deduped,
            "failed": failed,
        },
    )
    beat(f"{args.profile}-ingest-attachments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
