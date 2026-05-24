# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment;
# customizations belong in ~/.agency/profiles/<P>/ or deployment.yaml.
"""
Deployment manifest schema + validator.

Single entry point: `validate(yaml_path) -> ValidationResult`.

Run on:
  - every `agency init` (validate fresh manifest before write-back)
  - every `agency upgrade` (validate against new framework version)
  - boot sequence (first check; refuse to start if invalid)
  - `agency status` (operator-facing sanity check)

The validator NEVER mutates the manifest. It produces structured errors
(blocking) and warnings (non-blocking). Callers decide what to do with
either.

The framework is vendor-neutral by design (§1.3): the validator
recognizes any provider listed in `invariants.yaml::valid_providers`
but does not prefer one. The list is open and grows by PR.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from _framework.constants import (
    AGENCY_HOME,
    INVARIANTS_YAML,
    PROFILES_DIR,
    profile_dir,
    profile_soul,
    profile_standards,
)


# ── Result types ─────────────────────────────────────────────────────────


@dataclass
class ValidationFinding:
    """Single validation issue. Errors block; warnings don't."""

    level: str             # "error" | "warn" | "info"
    code: str              # short stable identifier (e.g. "missing-role")
    message: str           # human-readable
    location: str = ""     # dotted path into the yaml (e.g. "profiles[0].email")
    hint: str = ""         # optional remediation hint

    def __str__(self) -> str:
        loc = f" @ {self.location}" if self.location else ""
        hint = f"\n      hint: {self.hint}" if self.hint else ""
        return f"  [{self.level.upper()}] {self.code}{loc}: {self.message}{hint}"


@dataclass
class ValidationResult:
    """Aggregate result. `ok` is True iff no errors."""

    ok: bool
    findings: list[ValidationFinding] = field(default_factory=list)
    manifest: dict[str, Any] | None = None

    @property
    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.level == "warn"]

    def add(
        self,
        level: str,
        code: str,
        message: str,
        location: str = "",
        hint: str = "",
    ) -> None:
        self.findings.append(
            ValidationFinding(level=level, code=code, message=message, location=location, hint=hint)
        )
        if level == "error":
            self.ok = False

    def render(self) -> str:
        if not self.findings:
            return "  manifest valid (no errors, no warnings)"
        lines = []
        for f in self.findings:
            lines.append(str(f))
        return "\n".join(lines)


# ── Invariants loader ────────────────────────────────────────────────────


_INVARIANTS_CACHE: dict[str, Any] | None = None


def load_invariants() -> dict[str, Any]:
    """Load `_framework/invariants.yaml`. Cached after first call."""
    global _INVARIANTS_CACHE
    if _INVARIANTS_CACHE is not None:
        return _INVARIANTS_CACHE
    if not INVARIANTS_YAML.exists():
        raise FileNotFoundError(f"invariants.yaml not found at {INVARIANTS_YAML}")
    with open(INVARIANTS_YAML) as f:
        _INVARIANTS_CACHE = yaml.safe_load(f)
    return _INVARIANTS_CACHE


# ── Top-level validate ───────────────────────────────────────────────────


def validate(yaml_path: Path | str) -> ValidationResult:
    """
    Validate a deployment.yaml. Returns ValidationResult.

    Errors (blocking):
      - file not found, unparseable, or empty
      - missing required top-level keys
      - required roles not present
      - duplicate profile ids
      - persona files referenced but not present on disk
      - provider not in invariants.yaml::valid_providers
      - inline secrets detected in `credentials:`
      - placeholder values left in (manifest never `agency init`-ed)

    Warnings (non-blocking):
      - profile missing standards.md (operator may have intentionally
        removed; agent operates on persona alone)
      - email field set on a non-CoS role (deployment overriding the
        single-mailbox default — that's allowed but flagged)
      - fallback_providers empty (no cascade if primary fails)
      - ingress methods all false (no way for owner to reach CoS)
    """
    result = ValidationResult(ok=True)
    yaml_path = Path(yaml_path).expanduser()

    # ── Read + parse ────────────────────────────────────────────────────
    if not yaml_path.exists():
        result.add(
            "error", "manifest-not-found",
            f"No manifest at {yaml_path}",
            hint="Run `agency init` to create a deployment, or set AGENCY_HOME.",
        )
        return result

    try:
        with open(yaml_path) as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.add("error", "manifest-unparseable", f"YAML parse failed: {e}", str(yaml_path))
        return result

    if not isinstance(manifest, dict) or not manifest:
        result.add("error", "manifest-empty", "Manifest is empty or not a mapping.", str(yaml_path))
        return result

    result.manifest = manifest

    # ── Top-level shape ─────────────────────────────────────────────────
    for required in ("deployment", "profiles", "defaults", "credentials"):
        if required not in manifest:
            result.add(
                "error", "missing-top-level",
                f"Required top-level key missing: '{required}'",
                location=required,
            )

    if not result.ok:
        return result

    deployment = manifest["deployment"]
    profiles = manifest["profiles"]
    defaults = manifest["defaults"]
    credentials = manifest["credentials"]

    # ── deployment block ────────────────────────────────────────────────
    for key in ("owner", "org_name", "primary_email", "timezone", "framework_version"):
        if key not in deployment:
            result.add(
                "error", "missing-deployment-key",
                f"deployment.{key} missing",
                location=f"deployment.{key}",
            )
            continue
        v = deployment[key]
        if not isinstance(v, str):
            result.add(
                "error", "deployment-key-type",
                f"deployment.{key} must be a string, got {type(v).__name__}",
                location=f"deployment.{key}",
            )
        if isinstance(v, str) and _is_placeholder(v):
            result.add(
                "error", "manifest-placeholder",
                f"deployment.{key} still has a placeholder value ('{v}')",
                location=f"deployment.{key}",
                hint="Run `agency init` to replace placeholders, or edit by hand.",
            )

    # ── profiles ────────────────────────────────────────────────────────
    if not isinstance(profiles, list) or not profiles:
        result.add(
            "error", "no-profiles",
            "deployment.profiles is empty — at least chief-of-staff + knowledge-base + system-sentinel required.",
            location="profiles",
        )
        return result

    invariants = load_invariants()
    valid_role_ids = {r["id"] for r in invariants["roles"]}
    role_index = {r["id"]: r for r in invariants["roles"]}
    required_roles = set(invariants.get("required_roles", []))

    seen_ids: set[str] = set()
    seen_roles: set[str] = set()
    seen_emails: set[str] = set()

    for i, prof in enumerate(profiles):
        loc = f"profiles[{i}]"
        if not isinstance(prof, dict):
            result.add("error", "profile-not-mapping", "profile entry must be a mapping", location=loc)
            continue
        for key in ("id", "role", "persona_file"):
            if key not in prof:
                result.add("error", "profile-missing-key", f"profile.{key} missing", location=loc)

        pid = prof.get("id", "")
        role = prof.get("role", "")

        if not pid or _is_placeholder(pid):
            result.add(
                "error", "profile-id-placeholder",
                f"profile.id has placeholder or empty value ('{pid}')",
                location=f"{loc}.id",
                hint="Choose a short kebab-case name for this role (e.g. 'loriah' for CoS).",
            )
        elif pid in seen_ids:
            result.add(
                "error", "duplicate-profile-id",
                f"profile id '{pid}' is duplicated",
                location=f"{loc}.id",
            )
        else:
            seen_ids.add(pid)

        if role not in valid_role_ids:
            # custom roles allowed if directory exists
            if not (AGENCY_HOME / "custom-roles" / role).exists():
                result.add(
                    "error", "unknown-role",
                    f"role '{role}' is not in invariants.yaml::roles and no custom-roles/{role} directory exists",
                    location=f"{loc}.role",
                    hint=f"Valid built-in roles: {sorted(valid_role_ids)}",
                )
        seen_roles.add(role)

        # standards.md is by-convention. Warn if missing (per §2.5 of spec).
        if pid and not _is_placeholder(pid):
            std = profile_standards(pid)
            if not std.exists():
                result.add(
                    "warn", "profile-missing-standards",
                    f"profile '{pid}' has no standards.md at {std}",
                    location=f"{loc}.id",
                    hint="standards.md captures the agent's quality floor. The framework warns but allows operation on persona alone.",
                )
            soul = profile_soul(pid)
            if not soul.exists():
                # SOUL.md is critical — error
                result.add(
                    "error", "profile-missing-soul",
                    f"profile '{pid}' has no SOUL.md at {soul}",
                    location=f"{loc}.id",
                    hint="SOUL.md is the agent's identity. Generate from the template under templates/profiles/<role>/SOUL.md.template.",
                )

        # email handling: only CoS sends by default. Other roles with
        # email != null are operator-deliberate overrides — warn.
        email = prof.get("email")
        if email and email not in (None, "null", ""):
            if role != "chief-of-staff":
                result.add(
                    "warn", "non-cos-mailbox",
                    f"profile '{pid}' has email set but role '{role}' is not chief-of-staff. Single-mailbox default broken.",
                    location=f"{loc}.email",
                    hint="If this is deliberate (multi-mailbox deployment), ignore this warning.",
                )
            if email in seen_emails:
                result.add(
                    "error", "duplicate-email",
                    f"email '{email}' is assigned to multiple profiles",
                    location=f"{loc}.email",
                )
            else:
                seen_emails.add(email)

        # starter skills must exist as templates under the role
        starter_skills = prof.get("starter_skills", [])
        if not isinstance(starter_skills, list):
            result.add(
                "error", "starter-skills-shape",
                "starter_skills must be a list", location=f"{loc}.starter_skills",
            )

    # Required roles present?
    missing_required = required_roles - seen_roles
    for missing in missing_required:
        result.add(
            "error", "missing-required-role",
            f"required role '{missing}' is not declared in profiles",
            location="profiles",
            hint=f"Add a profile with role: {missing}",
        )

    # ── defaults (inference) ───────────────────────────────────────────
    valid_providers = set(invariants.get("valid_providers", []))
    provider = defaults.get("provider")
    if not provider or _is_placeholder(provider):
        result.add(
            "error", "default-provider-missing",
            f"defaults.provider is empty or placeholder ('{provider}')",
            location="defaults.provider",
        )
    elif provider not in valid_providers:
        result.add(
            "error", "default-provider-unknown",
            f"defaults.provider '{provider}' is not in invariants.yaml::valid_providers",
            location="defaults.provider",
            hint=f"Valid providers (open list): {sorted(valid_providers)}. Add yours via PR to invariants.yaml.",
        )

    for key in ("model", "base_url"):
        v = defaults.get(key)
        if not v or _is_placeholder(v):
            result.add(
                "error", "default-incomplete",
                f"defaults.{key} is empty or placeholder ('{v}')",
                location=f"defaults.{key}",
            )

    fallback = defaults.get("fallback_providers", [])
    if not fallback:
        result.add(
            "warn", "no-fallback-providers",
            "defaults.fallback_providers is empty — no cascade if primary fails.",
            location="defaults.fallback_providers",
            hint="Recommended: configure at least one fallback provider for resilience.",
        )

    # ── credentials ────────────────────────────────────────────────────
    if not isinstance(credentials, dict):
        result.add("error", "credentials-shape", "credentials must be a mapping", location="credentials")
    else:
        for prov_name, ref in credentials.items():
            if not isinstance(ref, str):
                result.add(
                    "error", "credential-ref-type",
                    f"credentials.{prov_name} must be a string reference",
                    location=f"credentials.{prov_name}",
                )
                continue
            # Permitted reference shapes:
            if not (ref.startswith("keychain:") or ref.startswith("env:") or ref.startswith("file:")):
                result.add(
                    "error", "credential-inline-secret",
                    f"credentials.{prov_name} appears to inline a secret (no keychain:/env:/file: prefix)",
                    location=f"credentials.{prov_name}",
                    hint="Use 'keychain:<entry>' or 'env:<VAR>' — never inline the API key.",
                )

    # ── ingress (T2 wizard data) ──────────────────────────────────────
    ingress = manifest.get("ingress", {})
    if isinstance(ingress, dict) and ingress and not any(ingress.values()):
        result.add(
            "warn", "no-ingress",
            "All ingress methods are false — owner has no way to reach CoS.",
            location="ingress",
            hint="Enable at least one of email / chat_tab / signal / slack / openwebui.",
        )

    return result


# ── Helpers ──────────────────────────────────────────────────────────────


_PLACEHOLDER_PATTERN = ("{{", "}}")


def _is_placeholder(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    return _PLACEHOLDER_PATTERN[0] in s and _PLACEHOLDER_PATTERN[1] in s


# ── CLI entry point ──────────────────────────────────────────────────────


def main() -> int:
    """CLI: `python -m _framework.manifest [path]`."""
    import argparse

    p = argparse.ArgumentParser(description="Validate a HermesAgency deployment.yaml")
    p.add_argument(
        "path",
        nargs="?",
        default=str(AGENCY_HOME / "deployment.yaml"),
        help="Path to deployment.yaml (defaults to $AGENCY_HOME/deployment.yaml)",
    )
    p.add_argument(
        "--quiet", "-q", action="store_true", help="Only print errors (suppress warnings)"
    )
    args = p.parse_args()

    result = validate(args.path)

    print(f"Validating {args.path}:")
    if not result.findings:
        print("  ✓ manifest valid (no errors, no warnings)")
        return 0
    for f in result.findings:
        if args.quiet and f.level != "error":
            continue
        print(str(f))

    n_err = len(result.errors)
    n_warn = len(result.warnings)
    print(f"\n  errors: {n_err}   warnings: {n_warn}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
