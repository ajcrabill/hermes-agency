# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
scaffold-script — generate a playbook-compliant cron script.

Drops a `<name>.py` into `profiles/<profile>/scripts/` with the
required shebang, error handling, and event emission already in
place. Audit rules `script-no-shebang`, `script-no-error-handling`,
and `script-secrets-inline` pass on the generated file by construction.
"""

from __future__ import annotations

from pathlib import Path

from _framework.constants import TEMPLATES_DIR, profile_scripts


def scaffold_script(
    name: str,
    profile: str,
    *,
    purpose: str = "",
    cadence: str = "ad-hoc",
    inputs_read: str = "<inputs>",
    outputs_written: str = "<outputs>",
    events_emitted: str = "<event kinds>",
    force: bool = False,
) -> Path:
    target_dir = profile_scripts(profile)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.py"
    if target.exists() and not force:
        raise FileExistsError(f"{target} exists. Pass force=True to overwrite.")

    template_path = TEMPLATES_DIR / "SCRIPT.py.template"
    template = template_path.read_text(encoding="utf-8")
    header_comment = f"FRAMEWORK-GENERATED via scaffold-script for profile {profile}. Customize freely."

    replacements = {
        "{{HEADER_COMMENT}}": header_comment,
        "{{SCRIPT_NAME}}": name,
        "{{ONE_SENTENCE_PURPOSE}}": purpose or f"{name}: one-sentence purpose goes here.",
        "{{CRON_CADENCE}}": cadence,
        "{{PROFILE_ID}}": profile,
        "{{INPUTS_READ}}": inputs_read,
        "{{OUTPUTS_WRITTEN}}": outputs_written,
        "{{EVENTS_EMITTED}}": events_emitted,
    }
    for k, v in replacements.items():
        template = template.replace(k, str(v))

    target.write_text(template, encoding="utf-8")
    target.chmod(0o755)
    return target


def main() -> int:
    import argparse, sys
    p = argparse.ArgumentParser(description="Generate a playbook-compliant cron script.")
    p.add_argument("--name", required=True, help="Script name (no .py)")
    p.add_argument("--profile", required=True, help="Profile id")
    p.add_argument("--purpose", help="One-sentence purpose")
    p.add_argument("--cadence", default="ad-hoc", help="Cron cadence (e.g. 'every 5m')")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    try:
        path = scaffold_script(
            name=args.name, profile=args.profile,
            purpose=args.purpose or "", cadence=args.cadence, force=args.force,
        )
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["scaffold_script"]
