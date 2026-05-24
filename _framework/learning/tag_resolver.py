# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Tag conventions for the learning subsystem.

Three tag axes:

- `skill_tags`   kebab-case skill names. At least one required.
                 Special value `general` = "applies across all skills."
- `role_tags`    kebab-case role names from invariants.yaml::roles.
                 Used for cross-agent rules (e.g. voice/style rules
                 that apply to anyone speaking for the owner).
- `voice_tags`   free-form persona/voice attributes. Skills declare
                 which voice_tags apply via frontmatter.

`resolve_tags()` validates a tag set against invariants and returns a
normalized form (lowercased, deduped, sorted). It does NOT reject
unknown skill_tags (skills are deployment-extensible) — it only
flags malformed ones (uppercase, spaces, empty strings).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from _framework.manifest import load_invariants


_KEBAB_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


@dataclass
class TagResolution:
    """Normalized + validated tag set with any issues flagged."""

    skill_tags: list[str]
    role_tags: list[str]
    voice_tags: list[str]
    issues: list[str]   # human-readable problems (empty if clean)

    @property
    def is_clean(self) -> bool:
        return not self.issues

    @property
    def all_tags(self) -> set[str]:
        return set(self.skill_tags) | set(self.role_tags) | set(self.voice_tags)


def resolve_tags(
    skill_tags: list[str] | None,
    role_tags: list[str] | None = None,
    voice_tags: list[str] | None = None,
) -> TagResolution:
    """Normalize + validate three-axis tags. Always returns a TagResolution;
    callers check `.is_clean` if they want to refuse on issues."""

    issues: list[str] = []

    skill_norm = _normalize_axis(skill_tags or [], "skill_tag", issues, require_kebab=True)
    if not skill_norm:
        issues.append("skill_tags: at least one required")

    role_norm = _normalize_axis(role_tags or [], "role_tag", issues, require_kebab=True)

    # Validate roles against invariants (warn-level, not blocking — operator
    # may use a role not yet in invariants for a custom deployment).
    if role_norm:
        try:
            inv = load_invariants()
            known = {r["id"] for r in inv.get("roles", [])}
            for r in role_norm:
                if r not in known:
                    issues.append(f"role_tags: '{r}' not in invariants.yaml::roles (custom role?)")
        except Exception:
            pass

    voice_norm = _normalize_axis(voice_tags or [], "voice_tag", issues, require_kebab=True)

    return TagResolution(
        skill_tags=skill_norm,
        role_tags=role_norm,
        voice_tags=voice_norm,
        issues=issues,
    )


def _normalize_axis(
    raw: list[str],
    axis_label: str,
    issues: list[str],
    require_kebab: bool,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        if not isinstance(t, str):
            issues.append(f"{axis_label}: non-string value: {t!r}")
            continue
        norm = t.strip().lower()
        if not norm:
            issues.append(f"{axis_label}: empty tag in input")
            continue
        if require_kebab and not _KEBAB_RE.match(norm):
            issues.append(f"{axis_label}: '{t}' must be kebab-case")
            # still include the lowercased form so we don't lose intent
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return sorted(out)


# ── Resolution: which rules apply to a given skill/profile combination ──

def applicable_to_skill(
    rule_skill_tags: list[str],
    rule_role_tags: list[str],
    rule_voice_tags: list[str],
    target_skill: str,
    target_role: str | None = None,
    target_voice_tags: list[str] | None = None,
) -> bool:
    """
    Does this rule apply to this skill?

    Resolution algorithm (matches spec §3.3):
      1. rule.skill_tags includes target_skill   → applies
      2. 'general' in rule.skill_tags             → applies
      3. rule.role_tags includes target_role     → applies
      4. rule.voice_tags overlap target_voice_tags → applies
    """
    if target_skill in rule_skill_tags:
        return True
    if "general" in rule_skill_tags:
        return True
    if target_role and target_role in rule_role_tags:
        return True
    if target_voice_tags:
        if any(v in rule_voice_tags for v in target_voice_tags):
            return True
    return False


__all__ = [
    "TagResolution",
    "resolve_tags",
    "applicable_to_skill",
]
