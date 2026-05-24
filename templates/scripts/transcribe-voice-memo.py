#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
transcribe-voice-memo — STT for author voice memos.

Default backend: faster-whisper (local, no external API). Operators
can swap by changing the BACKEND block.

Stores the transcript next to the audio file. Returns the path so
ingest-attachments.py can pick it up + treat it like a .txt
attachment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _framework.heartbeats import beat
from _framework.sentinel import append_event


SUPPORTED_AUDIO = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".webm"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transcribe voice memo")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--audio-path", required=True)
    parser.add_argument("--model-size", default="base",
                        help="faster-whisper model: tiny / base / small / medium / large")
    parser.add_argument("--min-confidence", type=float, default=0.7)
    args = parser.parse_args(argv)

    audio = Path(args.audio_path).expanduser()
    if not audio.exists():
        append_event("voice_memo_failed", actor=args.profile, severity="warn",
                     payload={"reason": "audio not found", "path": str(audio)})
        beat(f"{args.profile}-transcribe-voice-memo")
        return 1

    if audio.suffix.lower() not in SUPPORTED_AUDIO:
        append_event("voice_memo_skipped", actor=args.profile, severity="info",
                     payload={"reason": "unsupported audio format",
                              "suffix": audio.suffix})
        beat(f"{args.profile}-transcribe-voice-memo")
        return 1

    # ── BACKEND BLOCK ──────────────────────────────────────────────────
    try:
        from faster_whisper import WhisperModel   # type: ignore[import-not-found]
    except ImportError:
        append_event(
            "voice_memo_skipped", actor=args.profile, severity="warn",
            payload={
                "reason": "faster-whisper not installed",
                "remediation": "pip install faster-whisper",
            },
        )
        beat(f"{args.profile}-transcribe-voice-memo")
        return 1

    model = WhisperModel(args.model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(str(audio), beam_size=5)

    transcript_lines = ["[transcribed: faster-whisper " + args.model_size + "]"]
    low_confidence: list[dict] = []
    for seg in segments:
        line = seg.text.strip()
        prob = getattr(seg, "avg_logprob", 0.0)
        # avg_logprob is negative; closer to 0 = more confident.
        # Normalize: confidence ≈ 1 + (avg_logprob / 5) clamped to [0, 1].
        confidence = max(0.0, min(1.0, 1.0 + prob / 5.0))
        marker = ""
        if confidence < args.min_confidence:
            low_confidence.append({"text": line, "confidence": round(confidence, 2)})
            marker = "  [low-confidence]"
        transcript_lines.append(f"{line}{marker}")

    transcript_path = audio.with_suffix(".transcript.txt")
    transcript_path.write_text("\n".join(transcript_lines), encoding="utf-8")

    append_event(
        "voice_memo_transcribed", actor=args.profile, severity="info",
        payload={
            "transcript_path": str(transcript_path),
            "duration_seconds": getattr(info, "duration", None),
            "language": getattr(info, "language", None),
            "low_confidence_segments": low_confidence,
        },
    )
    beat(f"{args.profile}-transcribe-voice-memo")

    print(json.dumps({
        "transcript_path": str(transcript_path),
        "low_confidence_count": len(low_confidence),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
