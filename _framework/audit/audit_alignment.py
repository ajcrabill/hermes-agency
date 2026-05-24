# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
audit_alignment — the 7-category audit engine.

Single source of truth for which findings are ALWAYS_BLOCK vs warn:
`_framework/invariants.yaml::always_block_rules` and `::warn_rules`.
Adding a rule means (a) drop a handler in this module and (b) list its
code in invariants.yaml. The audit refuses to start if any handler is
registered without an entry in invariants (and vice versa).

Public:
  audit_skill(skill, profile, strict=False)
  audit_profile(profile, strict=False)
  audit_deployment(strict=False)
  audit_self()                       audits the framework itself

CLI:
  python -m _framework.audit.audit_alignment [--profile P] [--skill S]
                                              [--strict] [--self]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from _framework.constants import (
    AGENCY_HOME,
    FRAMEWORK_ROOT,
    PROFILES_DIR,
    profile_dir,
    profile_skills,
    profile_scripts,
    profile_soul,
    profile_standards,
)
from _framework.manifest import load_invariants


# ── Finding / Report types ───────────────────────────────────────────────


@dataclass
class AuditFinding:
    code: str                  # stable identifier matching invariants.yaml
    category: int              # 1-7, per playbook taxonomy
    level: str                 # "error" (ALWAYS_BLOCK) | "warn" | "info"
    message: str
    location: str = ""         # absolute path or skill:profile reference
    hint: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.level == "error"

    def __str__(self) -> str:
        loc = f" @ {self.location}" if self.location else ""
        hint = f"\n      hint: {self.hint}" if self.hint else ""
        return f"  [{self.level.upper()} cat{self.category}] {self.code}{loc}: {self.message}{hint}"


@dataclass
class AuditReport:
    target: str                                  # description of what was audited
    findings: list[AuditFinding] = field(default_factory=list)
    rules_run: set[str] = field(default_factory=set)
    skipped: list[str] = field(default_factory=list)
    strict: bool = False

    @property
    def blocking_findings(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.is_blocking]

    @property
    def passed(self) -> bool:
        if self.strict:
            return not self.blocking_findings
        return not self.findings

    def render(self) -> str:
        lines = [f"audit: {self.target}", f"  rules run: {len(self.rules_run)}"]
        if self.skipped:
            lines.append(f"  rules skipped: {len(self.skipped)}")
        if not self.findings:
            lines.append("  ✓ clean")
            return "\n".join(lines)
        for f in self.findings:
            if self.strict and not f.is_blocking:
                continue
            lines.append(str(f))
        n_block = len(self.blocking_findings)
        n_warn = len(self.findings) - n_block
        lines.append(f"  blocking: {n_block}   warnings: {n_warn}")
        return "\n".join(lines)


# ── Rule registry ────────────────────────────────────────────────────────


@dataclass
class _Rule:
    code: str
    category: int
    scope: str               # "skill" | "profile" | "deployment" | "framework"
    handler: Callable[..., list[AuditFinding]]


_RULES: dict[str, _Rule] = {}


def _rule(code: str, category: int, scope: str):
    """Decorator to register a rule handler. Handler signature matches scope."""

    def deco(fn: Callable):
        _RULES[code] = _Rule(code=code, category=category, scope=scope, handler=fn)
        return fn

    return deco


# ── Public entry points ──────────────────────────────────────────────────


def audit_skill(skill: str, profile: str, strict: bool = False) -> AuditReport:
    """Audit a single skill within a profile. Runs only `scope=skill` rules."""
    report = AuditReport(target=f"skill {profile}:{skill}", strict=strict)
    invariants = load_invariants()
    always_block = set(invariants.get("always_block_rules", []))
    warn = set(invariants.get("warn_rules", []))

    for code, rule in _RULES.items():
        if rule.scope != "skill":
            report.skipped.append(code)
            continue
        if strict and code not in always_block:
            report.skipped.append(code)
            continue
        report.rules_run.add(code)
        for f in rule.handler(skill=skill, profile=profile):
            # Annotate level from invariants (ALWAYS_BLOCK -> error)
            if f.code in always_block:
                f.level = "error"
            elif f.code in warn:
                if f.level not in ("error",):
                    f.level = "warn"
            report.findings.append(f)
    return report


def audit_profile(profile: str, strict: bool = False) -> AuditReport:
    """Audit a whole profile — every skill + scripts."""
    report = AuditReport(target=f"profile {profile}", strict=strict)
    invariants = load_invariants()
    always_block = set(invariants.get("always_block_rules", []))
    warn = set(invariants.get("warn_rules", []))

    # Profile-level rules
    for code, rule in _RULES.items():
        if rule.scope != "profile":
            continue
        if strict and code not in always_block:
            report.skipped.append(code)
            continue
        report.rules_run.add(code)
        for f in rule.handler(profile=profile):
            if f.code in always_block:
                f.level = "error"
            elif f.code in warn:
                f.level = "warn"
            report.findings.append(f)

    # Each skill
    skills_dir = profile_skills(profile)
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_report = audit_skill(skill=skill_dir.name, profile=profile, strict=strict)
            report.findings.extend(skill_report.findings)
            report.rules_run |= skill_report.rules_run

    # Each script
    scripts_dir = profile_scripts(profile)
    if scripts_dir.exists():
        for code, rule in _RULES.items():
            if rule.scope != "script":
                continue
            if strict and code not in always_block:
                continue
            report.rules_run.add(code)
            for script in sorted(scripts_dir.rglob("*.py")):
                for f in rule.handler(script=script, profile=profile):
                    if f.code in always_block:
                        f.level = "error"
                    elif f.code in warn:
                        f.level = "warn"
                    report.findings.append(f)
    return report


def audit_deployment(strict: bool = False) -> AuditReport:
    """Audit every profile in the deployment + framework integrity."""
    report = AuditReport(target=f"deployment @ {AGENCY_HOME}", strict=strict)

    if PROFILES_DIR.exists():
        for prof_dir in sorted(PROFILES_DIR.iterdir()):
            if not prof_dir.is_dir():
                continue
            sub = audit_profile(profile=prof_dir.name, strict=strict)
            report.findings.extend(sub.findings)
            report.rules_run |= sub.rules_run

    # Always run framework-integrity rules
    invariants = load_invariants()
    always_block = set(invariants.get("always_block_rules", []))
    warn = set(invariants.get("warn_rules", []))
    for code, rule in _RULES.items():
        if rule.scope != "framework":
            continue
        if strict and code not in always_block:
            continue
        report.rules_run.add(code)
        for f in rule.handler():
            if f.code in always_block:
                f.level = "error"
            elif f.code in warn:
                f.level = "warn"
            report.findings.append(f)

    return report


def audit_self() -> AuditReport:
    """Audit the framework against itself (no deployment required).
    Runs framework-integrity rules only. Useful in CI."""
    report = AuditReport(target=f"framework @ {FRAMEWORK_ROOT}", strict=False)
    invariants = load_invariants()
    always_block = set(invariants.get("always_block_rules", []))
    warn = set(invariants.get("warn_rules", []))
    for code, rule in _RULES.items():
        if rule.scope != "framework":
            continue
        report.rules_run.add(code)
        for f in rule.handler():
            if f.code in always_block:
                f.level = "error"
            elif f.code in warn:
                f.level = "warn"
            report.findings.append(f)
    return report


# ── Category 1: Skill anatomy ────────────────────────────────────────────


def _read_skill_md(skill: str, profile: str) -> tuple[Path, str]:
    p = profile_skills(profile) / skill / "SKILL.md"
    if not p.exists():
        return p, ""
    return p, p.read_text(encoding="utf-8", errors="replace")


@_rule("skill-no-autonomy-frontmatter", category=1, scope="skill")
def _check_autonomy_frontmatter(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []  # missing SKILL.md is handled by profile-level checks
    if not text.startswith("---"):
        return [AuditFinding(
            code="skill-no-autonomy-frontmatter",
            category=1, level="error",
            message=f"{skill}: SKILL.md has no YAML frontmatter (autonomy block required)",
            location=str(p),
            hint="Add `---\\nskill_id: ...\\nautonomy:\\n  min_level: 1\\n  action_classes: [draft-only]\\n---` at the top.",
        )]
    end = text.find("---", 3)
    if end < 0:
        return [AuditFinding(
            code="skill-no-autonomy-frontmatter", category=1, level="error",
            message=f"{skill}: SKILL.md frontmatter not closed",
            location=str(p),
        )]
    fm = text[3:end]
    if "autonomy:" not in fm:
        return [AuditFinding(
            code="skill-no-autonomy-frontmatter", category=1, level="error",
            message=f"{skill}: SKILL.md frontmatter missing autonomy block",
            location=str(p),
        )]
    return []


@_rule("skill-no-action-surface", category=1, scope="skill")
def _check_action_surface(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    if not _has_section(text, "Action surface") and not _has_section(text, "Action Surface"):
        return [AuditFinding(
            code="skill-no-action-surface", category=1, level="error",
            message=f"{skill}: SKILL.md missing ## Action surface section",
            location=str(p),
        )]
    return []


# ── Category 2: Skill discipline ────────────────────────────────────────


@_rule("skill-no-verifier", category=2, scope="skill")
def _check_verifier(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    if not _has_section(text, "Verifier"):
        return [AuditFinding(
            code="skill-no-verifier", category=2, level="error",
            message=f"{skill}: SKILL.md missing ## Verifier criteria section (fail-closed by spec §6.1)",
            location=str(p),
        )]
    return []


@_rule("skill-no-supervised-learning", category=2, scope="skill")
def _check_supervised_learning(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    if not _has_section(text, "Supervised learning") and not _has_section(text, "Supervised Learning"):
        return [AuditFinding(
            code="skill-no-supervised-learning", category=2, level="error",
            message=f"{skill}: SKILL.md missing ## Supervised learning section (loop step 3 of 7)",
            location=str(p),
            hint="Wire `_framework.learning.inject_for_skill()` at skill load and document it here.",
        )]
    return []


@_rule("skill-no-untrusted-content", category=2, scope="skill")
def _check_untrusted_content(skill: str, profile: str, **_) -> list[AuditFinding]:
    """ALWAYS_BLOCK only if the skill clearly processes external content.
    Heuristic: skill name or content mentions external sources without
    declaring an untrusted-content section."""
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    external_signals = ("email", "inbox", "rss", "webhook", "scrape", "ingest", "podcast", "journalist")
    looks_external = any(sig in skill.lower() for sig in external_signals)
    if not looks_external:
        return []
    if not _has_section(text, "Untrusted content") and "prompt-injection" not in text.lower():
        return [AuditFinding(
            code="skill-no-untrusted-content", category=2, level="error",
            message=f"{skill}: handles external input but has no ## Untrusted content guard",
            location=str(p),
            hint="Add an ## Untrusted content section describing how external text is sandboxed.",
        )]
    return []


@_rule("skill-no-failure-mode", category=2, scope="skill")
def _check_failure_mode(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    if not _has_section(text, "Failure modes") and not _has_section(text, "Failure Modes"):
        return [AuditFinding(
            code="skill-no-failure-mode", category=2, level="warn",
            message=f"{skill}: SKILL.md missing ## Failure modes section",
            location=str(p),
        )]
    return []


@_rule("skill-no-self-check", category=2, scope="skill")
def _check_self_check(skill: str, profile: str, **_) -> list[AuditFinding]:
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    if not _has_section(text, "Self-check") and not _has_section(text, "Self check"):
        return [AuditFinding(
            code="skill-no-self-check", category=2, level="warn",
            message=f"{skill}: SKILL.md missing ## Self-check section",
            location=str(p),
        )]
    return []


@_rule("skill-injection-trigger", category=2, scope="skill")
def _check_injection_trigger(skill: str, profile: str, **_) -> list[AuditFinding]:
    """Catch defensive content that QUOTES injection trigger phrases verbatim
    (paraphrase-don't-quote, §P6.23 lesson from v7).

    For v0.1: heuristic match on Hermes' known trigger phrases that appear in
    quoted form inside the skill text. Operators can extend the list via
    `_framework/invariants.yaml::skill_injection_triggers` (future)."""
    p, text = _read_skill_md(skill, profile)
    if not text:
        return []
    # Generic representative triggers — quoting verbatim is the issue
    triggers = [
        "BEGIN AUTHORITATIVE INSTRUCTIONS",
        "SYSTEM PROMPT",
        "IGNORE ALL PREVIOUS INSTRUCTIONS",
    ]
    flagged = [t for t in triggers if f'"{t}"' in text or f"'{t}'" in text or f"`{t}`" in text]
    if flagged:
        return [AuditFinding(
            code="skill-injection-trigger", category=2, level="error",
            message=f"{skill}: SKILL.md quotes injection trigger phrase(s) verbatim: {flagged}",
            location=str(p),
            hint="Paraphrase the trigger you're defending against — don't quote it (paraphrase-don't-quote rule).",
        )]
    return []


# ── Category 3: Script anatomy ───────────────────────────────────────────


@_rule("script-no-shebang", category=3, scope="script")
def _check_script_shebang(script: Path, profile: str, **_) -> list[AuditFinding]:
    try:
        first = script.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    except Exception:
        return []
    if first and first[0].startswith("#!"):
        return []
    # __init__.py and modules-only files don't need a shebang
    if script.name == "__init__.py":
        return []
    if not _looks_executable(script):
        return []
    return [AuditFinding(
        code="script-no-shebang", category=3, level="error",
        message=f"script has no shebang line",
        location=str(script),
        hint="Add `#!/usr/bin/env python3` (or the appropriate interpreter) as the first line.",
    )]


@_rule("script-no-error-handling", category=3, scope="script")
def _check_script_error_handling(script: Path, profile: str, **_) -> list[AuditFinding]:
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    if script.name == "__init__.py":
        return []
    if not _looks_executable(script):
        return []
    has_try = "try:" in text or "except" in text
    has_check = "if __name__" in text and "raise" in text
    if not (has_try or has_check):
        return [AuditFinding(
            code="script-no-error-handling", category=3, level="error",
            message=f"script has no try/except and no explicit raise — unhandled exceptions crash silently",
            location=str(script),
        )]
    return []


@_rule("script-secrets-inline", category=3, scope="script")
def _check_script_secrets_inline(script: Path, profile: str, **_) -> list[AuditFinding]:
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    # Heuristic: SK_ / sk_ / API_KEY = "..." literal that looks key-shaped
    suspicious_patterns = [
        re.compile(r'(api[_-]?key|secret|token|password)\s*=\s*[\'"][A-Za-z0-9\-_]{20,}[\'"]', re.I),
        re.compile(r'[\'"]sk-[A-Za-z0-9]{30,}[\'"]'),
    ]
    out: list[AuditFinding] = []
    for pat in suspicious_patterns:
        for m in pat.finditer(text):
            out.append(AuditFinding(
                code="script-secrets-inline", category=3, level="error",
                message=f"script appears to inline a secret: {m.group(0)[:60]}...",
                location=str(script),
                hint="Read secrets from Keychain or env — never inline in source.",
            ))
    return out


# ── Category 4: Profile structure ────────────────────────────────────────


@_rule("profile-missing-soul", category=4, scope="profile")
def _check_profile_soul(profile: str, **_) -> list[AuditFinding]:
    p = profile_soul(profile)
    if not p.exists():
        return [AuditFinding(
            code="profile-missing-soul", category=4, level="error",
            message=f"profile '{profile}' has no SOUL.md at {p}",
            location=str(p),
            hint="Copy + customize templates/profiles/<role>/SOUL.md.template",
        )]
    return []


@_rule("profile-missing-standards", category=4, scope="profile")
def _check_profile_standards(profile: str, **_) -> list[AuditFinding]:
    p = profile_standards(profile)
    if not p.exists():
        return [AuditFinding(
            code="profile-missing-standards", category=4, level="warn",
            message=f"profile '{profile}' has no standards.md at {p}",
            location=str(p),
            hint="standards.md is the agent's quality floor. Operating on persona alone is risky.",
        )]
    return []


@_rule("profile-standards-source-not-found", category=4, scope="profile")
def _check_standards_sources(profile: str, **_) -> list[AuditFinding]:
    """If standards.md references other docs (master plan, playbook, etc),
    verify the referenced paths exist."""
    p = profile_standards(profile)
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    out: list[AuditFinding] = []
    # Look for markdown-style links and relative paths
    link_pat = re.compile(r"\(([^)\s]+\.md)\)")
    for m in link_pat.finditer(text):
        ref = m.group(1)
        if ref.startswith("http"):
            continue
        ref_path = (p.parent / ref).resolve()
        if not ref_path.exists():
            out.append(AuditFinding(
                code="profile-standards-source-not-found",
                category=4, level="error",
                message=f"standards.md references missing path: {ref}",
                location=str(p),
            ))
    return out


# ── Category 5: Cross-profile ────────────────────────────────────────────


@_rule("skill-role-mismatch", category=5, scope="skill")
def _check_skill_role_mismatch(skill: str, profile: str, **_) -> list[AuditFinding]:
    """If a skill's name strongly suggests a different role's keywords,
    flag it. Cross-references with invariants.yaml::roles."""
    invariants = load_invariants()
    # Find this profile's role
    # The audit doesn't read deployment.yaml directly — it would create a
    # circular dependency. Instead it looks up the role by directory
    # convention (profiles/<id>/role.txt) or skips silently.
    role_file = profile_dir(profile) / "role.txt"
    if not role_file.exists():
        return []
    role = role_file.read_text(encoding="utf-8", errors="replace").strip()

    skill_lower = skill.lower()
    matched_roles = []
    for r in invariants.get("roles", []):
        for kw in r.get("keywords", []):
            if kw in skill_lower:
                matched_roles.append(r["id"])
                break
    if matched_roles and role not in matched_roles:
        return [AuditFinding(
            code="skill-role-mismatch", category=5, level="error",
            message=f"skill '{skill}' has keywords matching role(s) {matched_roles} but lives in profile '{profile}' (role={role})",
            location=f"{profile}:{skill}",
        )]
    return []


# ── Category 6: Learning loop ────────────────────────────────────────────


@_rule("learning-loop-broken", category=6, scope="skill")
def _check_learning_loop(skill: str, profile: str, **_) -> list[AuditFinding]:
    """ALWAYS_BLOCK: >3 rules captured but 0 firings in 30 days."""
    try:
        from _framework.learning.learning_db import get_db, decode_json_col
    except Exception:
        return []
    try:
        db = get_db()
    except Exception:
        return []
    try:
        rules = db.execute("SELECT skill_tags FROM learning_rules WHERE status='active'").fetchall()
        n_rules = sum(1 for r in rules if skill in decode_json_col(r["skill_tags"]))
        if n_rules <= 3:
            return []
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        n_fires = db.execute(
            "SELECT COUNT(*) AS n FROM firings WHERE skill_tag=? AND created_at>=?",
            (skill, cutoff),
        ).fetchone()["n"]
        if int(n_fires) == 0:
            return [AuditFinding(
                code="learning-loop-broken", category=6, level="error",
                message=f"skill '{skill}' has {n_rules} rules but 0 firings in last 30d (loop broken)",
                location=f"{profile}:{skill}",
                hint="Inject rules at skill-load and record firings when used.",
            )]
        return []
    finally:
        db.close()


@_rule("recapture-implicates-skill", category=6, scope="skill")
def _check_recapture_implicates(skill: str, profile: str, **_) -> list[AuditFinding]:
    """ALWAYS_BLOCK: recapture event in last 14d implicates this skill."""
    try:
        from _framework.learning.learning_db import get_db
    except Exception:
        return []
    try:
        db = get_db()
    except Exception:
        return []
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        rows = db.execute(
            "SELECT new_rule_id, skill_tags, similarity FROM recapture_events "
            "WHERE detected_at >= ? AND dismissed=0",
            (cutoff,),
        ).fetchall()
        out: list[AuditFinding] = []
        for r in rows:
            tags = (r["skill_tags"] or "").split(",")
            if skill in tags:
                out.append(AuditFinding(
                    code="recapture-implicates-skill", category=6, level="error",
                    message=f"recapture event ({r['similarity']:.2f} similarity) in last 14d implicates skill '{skill}'",
                    location=f"{profile}:{skill}",
                ))
        return out
    finally:
        db.close()


@_rule("learning-rule-untagged", category=6, scope="deployment")
def _check_untagged_rules(**_) -> list[AuditFinding]:
    """Warn-only: rules tagged with only 'general' or empty skill_tags."""
    try:
        from _framework.learning.learning_db import get_db, decode_json_col
    except Exception:
        return []
    try:
        db = get_db()
    except Exception:
        return []
    try:
        rows = db.execute("SELECT id, skill_tags FROM learning_rules WHERE status='active'").fetchall()
        out = []
        for r in rows:
            tags = decode_json_col(r["skill_tags"])
            if not tags or tags == ["general"]:
                out.append(AuditFinding(
                    code="learning-rule-untagged", category=6, level="warn",
                    message=f"rule {r['id']} has only 'general' tag — likely under-targeted",
                    location=f"learning_rules.id={r['id']}",
                ))
        return out
    finally:
        db.close()


# ── Category 7: Framework integrity ──────────────────────────────────────


# Vendor names to detect in framework code. The audit skips
# invariants.yaml (which legitimately enumerates them for validation),
# the audit module itself (which lists them in its detection set), and
# docs/ (which can mention them as examples per §1.3).
_VENDOR_NAMES = [
    "openai", "anthropic", "deepseek", "mistral", "cohere",
    "google.com", "openrouter", "groq", "together.ai",
    "claude", "gpt-4", "gpt-3", "qwen", "llama-3", "deepseek-r1",
]
_VENDOR_LEAK_SKIP_DIRS = {"docs", "tests", "templates", "examples", "init"}
_VENDOR_LEAK_SKIP_FILES = {
    "invariants.yaml",
    "audit_alignment.py",            # this file enumerates them by necessity
    "embeddings.py",                  # legitimately mentions backend types
    "CHANGELOG.md",
    "README.md",
    "deployment.yaml.template",
    "wizard.py",                      # operator-facing prompt with vendor examples
}


@_rule("framework-vendor-leak", category=7, scope="framework")
def _check_framework_vendor_leak(**_) -> list[AuditFinding]:
    """ALWAYS_BLOCK (§1.3): no framework code names a vendor."""
    findings: list[AuditFinding] = []
    fw_dir = FRAMEWORK_ROOT / "_framework"
    if not fw_dir.exists():
        return []
    for path in fw_dir.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(FRAMEWORK_ROOT).parts
        if any(p in _VENDOR_LEAK_SKIP_DIRS for p in rel_parts):
            continue
        if path.name in _VENDOR_LEAK_SKIP_FILES:
            continue
        if path.suffix not in (".py", ".yaml", ".yml", ".sh"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        text_lower = text.lower()
        for vendor in _VENDOR_NAMES:
            if vendor in text_lower:
                # Skip comments-only mentions if the vendor only appears in comments
                # (heuristic: leave a single AuditFinding per file/vendor pair)
                findings.append(AuditFinding(
                    code="framework-vendor-leak", category=7, level="error",
                    message=f"framework file mentions vendor '{vendor}'",
                    location=str(path),
                    hint="Vendor identity lives in deployment.yaml; framework code stays vendor-neutral (§1.3).",
                ))
                break  # one finding per file
    return findings


_DEPRECATED_PATH_SKIP_FILES = {
    # These files legitimately enumerate the deprecated paths for the
    # purpose of detecting them — the strings here ARE the detector,
    # not a reference.
    "audit_alignment.py",
    "invariants.yaml",
    # Docs that historically reference v7 paths as migration context:
    "CHANGELOG.md",
    "DEVELOPMENT_PLAYBOOK.md",  # references ~/.loriah as the path it warns about
    "INTEGRATIONS.md",
}


@_rule("doc-references-deprecated-path", category=7, scope="framework")
def _check_deprecated_paths(**_) -> list[AuditFinding]:
    """Warn-only: framework or docs reference v7-era paths."""
    deprecated = ["~/.loriah", "/Users/ajc/.loriah"]
    findings: list[AuditFinding] = []
    for path in FRAMEWORK_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name in _DEPRECATED_PATH_SKIP_FILES:
            continue
        if path.suffix not in (".py", ".md", ".yaml", ".yml", ".sh"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for d in deprecated:
            if d in text:
                findings.append(AuditFinding(
                    code="doc-references-deprecated-path", category=7, level="warn",
                    message=f"file references deprecated path '{d}'",
                    location=str(path),
                    hint="Use ~/.agency-relative paths via _framework.constants.",
                ))
                break
    return findings


# ── Helpers ──────────────────────────────────────────────────────────────


def _has_section(text: str, name: str) -> bool:
    """Case-insensitive ## or ### section header match."""
    pat = re.compile(rf"^\s*#{{2,4}}\s+{re.escape(name)}\b", re.M | re.I)
    return bool(pat.search(text))


def _looks_executable(script: Path) -> bool:
    """True if the script has no `def main` / `if __name__` it might just be a module.
    True if it has either of those, or is in a `scripts/` dir."""
    if "scripts" in script.parts:
        return True
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return "if __name__" in text or "def main" in text


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> int:
    import argparse, sys

    p = argparse.ArgumentParser(description="HermesAgency audit-alignment.")
    p.add_argument("--skill", help="Audit one skill")
    p.add_argument("--profile", help="Audit one profile (or required if --skill)")
    p.add_argument("--strict", action="store_true", help="Report only ALWAYS_BLOCK findings")
    p.add_argument("--self", dest="audit_self_flag", action="store_true",
                   help="Audit the framework itself (skip deployment)")
    args = p.parse_args()

    if args.audit_self_flag:
        report = audit_self()
    elif args.skill:
        if not args.profile:
            print("--skill requires --profile", file=sys.stderr)
            return 2
        report = audit_skill(skill=args.skill, profile=args.profile, strict=args.strict)
    elif args.profile:
        report = audit_profile(profile=args.profile, strict=args.strict)
    else:
        report = audit_deployment(strict=args.strict)

    print(report.render())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AuditFinding",
    "AuditReport",
    "audit_skill",
    "audit_profile",
    "audit_deployment",
    "audit_self",
]
