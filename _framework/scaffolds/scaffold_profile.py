# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
scaffold-profile — generate a complete profile directory for a role.

Creates:
  profiles/<id>/
    SOUL.md          (from templates/profiles/<role>/SOUL.md.template)
    standards.md     (from templates/profiles/<role>/standards.md.template)
    config.yaml      (minimal stub)
    role.txt         (so audit knows what role this profile fills)
    skills/          (empty — scaffold-skill fills it)
    scripts/         (empty)
    cron/jobs.json   (empty stub)
    logs/            (empty)
    context/<id>/    (vault dir)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from _framework.constants import (
    TEMPLATES_DIR,
    profile_dir,
    profile_soul,
    profile_standards,
    profile_skills,
    profile_scripts,
    profile_cron_jobs,
    profile_logs,
    profile_vault,
    profile_config,
)


def scaffold_profile(
    role: str,
    profile_id: str,
    *,
    substitutions: Mapping[str, str] | None = None,
    force: bool = False,
) -> Path:
    """Create the profile dir + populate SOUL.md and standards.md from
    templates. Substitutions fill `{{KEY}}` placeholders in the
    templates (e.g. {{COS_NAME}}, {{ORG_NAME}}, {{PRINCIPAL_NAME}}).

    v0.23+ uses {{PRINCIPAL_NAME}} as the canonical key; {{OWNER_NAME}}
    is preserved as a backward-compat alias by callers."""

    role_templates = TEMPLATES_DIR / "profiles" / role
    if not role_templates.exists():
        raise FileNotFoundError(
            f"No template for role '{role}' at {role_templates}. "
            f"Available: {sorted(p.name for p in (TEMPLATES_DIR / 'profiles').iterdir() if p.is_dir())}"
        )

    target = profile_dir(profile_id)
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"{target} exists and is non-empty. Pass force=True to overwrite.")

    # Directory tree
    target.mkdir(parents=True, exist_ok=True)
    profile_skills(profile_id).mkdir(parents=True, exist_ok=True)
    profile_scripts(profile_id).mkdir(parents=True, exist_ok=True)
    profile_cron_jobs(profile_id).parent.mkdir(parents=True, exist_ok=True)
    profile_logs(profile_id).mkdir(parents=True, exist_ok=True)
    profile_vault(profile_id).mkdir(parents=True, exist_ok=True)

    subs = dict(substitutions or {})
    subs.setdefault("PROFILE_ID", profile_id)
    subs.setdefault("ROLE_ID", role)

    # SOUL.md
    soul_template = (role_templates / "SOUL.md.template").read_text(encoding="utf-8")
    profile_soul(profile_id).write_text(_substitute(soul_template, subs), encoding="utf-8")

    # standards.md
    stds_template = (role_templates / "standards.md.template").read_text(encoding="utf-8")
    profile_standards(profile_id).write_text(_substitute(stds_template, subs), encoding="utf-8")

    # config.yaml (minimal — cascade is deployment > framework)
    profile_config(profile_id).write_text(
        f"# Profile config for {profile_id} ({role}).\n"
        f"# Overrides defaults from deployment.yaml.\n"
        f"id: {profile_id}\n"
        f"role: {role}\n"
        f"# model: <override>\n"
        f"# provider: <override>\n"
        f"# base_url: <override>\n",
        encoding="utf-8",
    )

    # role.txt — used by audit role-mismatch detector
    (target / "role.txt").write_text(role, encoding="utf-8")

    # cron/jobs.json (empty)
    profile_cron_jobs(profile_id).write_text(json.dumps({"jobs": []}, indent=2), encoding="utf-8")

    return target


def _substitute(text: str, subs: Mapping[str, str]) -> str:
    for key, value in subs.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def main() -> int:
    import argparse, sys
    p = argparse.ArgumentParser(description="Scaffold a complete profile from a role template.")
    p.add_argument("--role", required=True, help="Role id (chief-of-staff, etc.)")
    p.add_argument("--id", dest="profile_id", required=True, help="Profile id (e.g. loriah)")
    p.add_argument("--sub", action="append", default=[], help="Placeholder substitution KEY=VALUE (repeatable)")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    subs = {}
    for raw in args.sub:
        if "=" not in raw:
            print(f"--sub value must be KEY=VALUE, got: {raw}", file=sys.stderr)
            return 2
        k, v = raw.split("=", 1)
        subs[k.strip()] = v.strip()

    try:
        path = scaffold_profile(role=args.role, profile_id=args.profile_id,
                                 substitutions=subs, force=args.force)
    except (FileNotFoundError, FileExistsError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Wrote profile at {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["scaffold_profile"]
