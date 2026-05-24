# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
scaffold-skill — generate a playbook-compliant SKILL.md.

Reads `templates/SKILL.md.template`, fills placeholders from role +
profile + supplied args, writes the result into
`profiles/<profile>/skills/<name>/SKILL.md`.

Refuses to overwrite an existing skill unless --force.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from _framework import __version__ as FRAMEWORK_VERSION
from _framework.constants import TEMPLATES_DIR, profile_skills
from _framework.manifest import load_invariants


def scaffold_skill(
    name: str,
    profile: str,
    role: str,
    *,
    purpose: str = "",
    elaborated: str = "",
    inputs: list[str] | None = None,
    action_classes: list[str] | None = None,
    min_level: int = 1,
    voice_tags: list[str] | None = None,
    expected_output_path: str = "",
    failure_modes: list[str] | None = None,
    force: bool = False,
) -> Path:
    """Generate a SKILL.md for the named skill. Returns the absolute path."""
    inv = load_invariants()
    role_entry = _role_entry(inv, role)

    if action_classes is None:
        action_classes = role_entry.get("default_action_classes", ["draft-only"]) or ["draft-only"]

    if voice_tags is None:
        voice_tags = []

    target_dir = profile_skills(profile) / name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "SKILL.md"
    if target.exists() and not force:
        raise FileExistsError(f"{target} exists. Pass force=True to overwrite.")

    template_path = TEMPLATES_DIR / "SKILL.md.template"
    template = template_path.read_text(encoding="utf-8")

    inputs = inputs or ["<describe inputs>"]
    failure_modes = failure_modes or ["<name a known failure mode>", "<and another>"]
    title = name.replace("-", " ").title()
    one_sentence = purpose or f"{title} — one-sentence purpose goes here."
    elaborated = elaborated or "Explain what this skill does in 1-2 short paragraphs. Concrete is better than abstract."

    replacements = {
        "{{SKILL_ID}}": name,
        "{{PROFILE_ID}}": profile,
        "{{ROLE_ID}}": role,
        "{{MIN_LEVEL}}": str(min_level),
        "{{ACTION_CLASSES}}": json.dumps(action_classes),
        "{{VOICE_TAGS}}": json.dumps(voice_tags),
        "{{CREATED_AT}}": datetime.now(timezone.utc).isoformat(),
        "{{FRAMEWORK_VERSION}}": FRAMEWORK_VERSION,
        "{{SKILL_TITLE}}": title,
        "{{ONE_SENTENCE_PURPOSE}}": one_sentence,
        "{{ELABORATED_PURPOSE}}": elaborated,
        "{{INPUT_1}}": inputs[0] if inputs else "<input>",
        "{{INPUT_2}}": inputs[1] if len(inputs) > 1 else "<another input or remove>",
        "{{EXPECTED_OUTPUT_PATH}}": expected_output_path or "<absolute path the verifier should check>",
        "{{FAILURE_MODE_1}}": failure_modes[0] if failure_modes else "<failure mode>",
        "{{FAILURE_MODE_2}}": failure_modes[1] if len(failure_modes) > 1 else "<another failure mode>",
    }
    for k, v in replacements.items():
        template = template.replace(k, str(v))

    target.write_text(template, encoding="utf-8")
    return target


def _role_entry(invariants: dict, role: str) -> dict:
    for r in invariants.get("roles", []):
        if r.get("id") == role:
            return r
    return {}


def main() -> int:
    import argparse, sys
    p = argparse.ArgumentParser(description="Generate a playbook-compliant SKILL.md.")
    p.add_argument("--name", required=True, help="Skill name (kebab-case)")
    p.add_argument("--profile", required=True, help="Profile id (e.g. loriah)")
    p.add_argument("--role", required=True, help="Role id (chief-of-staff, knowledge-base, etc.)")
    p.add_argument("--purpose", help="One-sentence purpose")
    p.add_argument("--min-level", type=int, default=1)
    p.add_argument("--action-class", action="append", dest="action_classes",
                   help="Action class (repeatable). Defaults to the role's defaults.")
    p.add_argument("--voice-tag", action="append", dest="voice_tags",
                   help="Voice tag (repeatable).")
    p.add_argument("--force", action="store_true", help="Overwrite existing SKILL.md")
    args = p.parse_args()

    try:
        path = scaffold_skill(
            name=args.name, profile=args.profile, role=args.role,
            purpose=args.purpose or "", action_classes=args.action_classes,
            min_level=args.min_level, voice_tags=args.voice_tags,
            force=args.force,
        )
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["scaffold_skill"]
