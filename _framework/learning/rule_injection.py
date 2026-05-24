# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Rule injection — load applicable learning rules into a skill's prompt
at skill-load time.

This is the THIRD link in the seven-step loop. If injection breaks,
the model never sees the corrections it's supposed to apply, and the
owner is re-teaching — recapture detection will catch it, but
injection's job is to prevent that in the first place.

Hermes wires `inject_for_skill()` into its skill-load machinery via
patches to `agent/skill_commands.py::_build_skill_message` and
`tools/skills_tool.py::skill_view`. Those patches live in
`_framework/learning_patches/` and are reapplied after each Hermes
update (the post-update reapply hook pattern — §A.3 of spec).

The resolver:

  1. Pull rules where skill_tags includes the target skill_name
  2. UNION rules where 'general' in skill_tags
  3. UNION rules where role_tags includes the target profile's role
  4. UNION rules where voice_tags overlap the skill's declared voice
  5. Filter out superseded / suspended
  6. Order: is_hard DESC, then last_fired_at DESC NULLS LAST,
            then created_at DESC
  7. Cap at `cap` rules (default 20)

The output is markdown the engine appends to the skill prompt.
"""

from __future__ import annotations

from .learning_db import get_db, decode_json_col


DEFAULT_INJECTION_CAP = 20


def resolve_rules(
    skill_name: str,
    profile: str,
    role: str | None = None,
    voice_tags: list[str] | None = None,
    cap: int = DEFAULT_INJECTION_CAP,
    db_path=None,
) -> list[dict]:
    """Pull the applicable, ordered set of learning rules for a skill load."""
    db = get_db(path=db_path)
    try:
        # We use SQL LIKE to filter on JSON-array columns. JSON columns
        # are stored as compact json (no spaces between elements), so
        # `LIKE '%"skill-name"%'` reliably matches a tagged rule.
        skill_token = f'%"{skill_name}"%'
        general_token = '%"general"%'
        role_token = f'%"{role}"%' if role else None

        params = [skill_token, general_token]
        clauses = [
            "lr.skill_tags LIKE ?",       # condition 1
            "lr.skill_tags LIKE ?",       # condition 2 ('general')
        ]
        if role_token:
            clauses.append("lr.role_tags LIKE ?")
            params.append(role_token)

        # voice overlap: at least one of the skill's voice_tags is in the rule's voice_tags
        voice_clause = []
        if voice_tags:
            for v in voice_tags:
                voice_clause.append("lr.voice_tags LIKE ?")
                params.append(f'%"{v}"%')

        where = " OR ".join(clauses + voice_clause)

        # last_fired_at is computed via subquery; rules never fired sort last
        query = f"""
            SELECT lr.*,
                   (SELECT MAX(f.created_at) FROM firings f WHERE f.rule_id = lr.id) AS last_fired_at
            FROM learning_rules lr
            WHERE lr.status = 'active'
              AND ({where})
            ORDER BY lr.is_hard DESC,
                     COALESCE(lr.id IN (SELECT rule_id FROM firings), 0) DESC,
                     COALESCE((SELECT MAX(created_at) FROM firings WHERE rule_id = lr.id), '') DESC,
                     lr.created_at DESC
            LIMIT ?
        """
        params.append(cap)

        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def inject_for_skill(
    skill_name: str,
    profile: str,
    role: str | None = None,
    voice_tags: list[str] | None = None,
    cap: int = DEFAULT_INJECTION_CAP,
    db_path=None,
) -> str:
    """Return the markdown block to append to the skill's prompt.

    Empty string if there are no applicable rules — caller is free to
    drop the injection section entirely in that case.
    """
    rules = resolve_rules(
        skill_name=skill_name,
        profile=profile,
        role=role,
        voice_tags=voice_tags,
        cap=cap,
        db_path=db_path,
    )
    if not rules:
        return ""

    lines = [
        "## Supervised learning — applicable corrections",
        "",
        f"Pulled at skill-load. Rules apply because skill_tags include `{skill_name}` (or `general`), or role_tags match this agent, or voice_tags overlap.",
        "",
        "Record a firing for any rule you use (see Action surface → firings.record).",
        "",
    ]
    for r in rules:
        skill_tags = decode_json_col(r.get("skill_tags"))
        role_tags = decode_json_col(r.get("role_tags"))
        voice_tags_r = decode_json_col(r.get("voice_tags"))
        marker = "⛔ HARD" if r.get("is_hard") else "•"
        meta_bits = []
        if skill_tags:
            meta_bits.append(f"skill: {', '.join(skill_tags)}")
        if role_tags:
            meta_bits.append(f"role: {', '.join(role_tags)}")
        if voice_tags_r:
            meta_bits.append(f"voice: {', '.join(voice_tags_r)}")
        meta = " · ".join(meta_bits)

        lines.append(f"- {marker} **{r['id']}** — {r['correction']}")
        if meta:
            lines.append(f"  *{meta}*")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_INJECTION_CAP",
    "resolve_rules",
    "inject_for_skill",
]
