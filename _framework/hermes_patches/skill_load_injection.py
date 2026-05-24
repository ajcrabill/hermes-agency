# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Patch: skill_load_injection

Target:  ~/.hermes/hermes-agent/agent/skill_commands.py
Function: _build_skill_message
Effect:   Appends inject_for_skill() output to the assembled prompt
          parts, so every skill-load includes the applicable learning
          rules.

Idempotent — marker check before applying. Safe to run after Hermes
upgrades.

Why this is the central patch: without it, the seven-step learning
loop runs through step 2 (capture, tag) but stops there. Step 3
(inject at skill-load) never reaches the model, so step 4 (apply)
can't happen, step 5 (record firings) finds nothing to record, and
the loop is broken.
"""

from __future__ import annotations

from pathlib import Path

from ._patch_base import HermesPatch, hermes_install_root


class SkillLoadInjectionPatch(HermesPatch):
    id = "skill_load_injection"
    description = (
        "Insert _framework.learning.inject_for_skill() output into "
        "_build_skill_message so captured learning rules reach the model."
    )

    def target_path(self) -> Path | None:
        p = hermes_install_root() / "agent" / "skill_commands.py"
        return p if p.exists() else None

    def is_already_applied(self, file_text: str) -> bool:
        return self.marker in file_text

    def applies_to(self, file_text: str) -> bool:
        # We anchor on `_inject_skill_config(loaded_skill, parts)` —
        # the call that runs right before our insertion point.
        return "_inject_skill_config(loaded_skill, parts)" in file_text

    def apply(self, file_text: str) -> str:
        if self.is_already_applied(file_text):
            return file_text
        if not self.applies_to(file_text):
            raise RuntimeError(
                "skill_load_injection: anchor '_inject_skill_config(loaded_skill, parts)' "
                "not found. Hermes' skill_commands.py may have been refactored — "
                "update the patch."
            )

        anchor = "    _inject_skill_config(loaded_skill, parts)"
        injection_block = f"""    _inject_skill_config(loaded_skill, parts)

    {self.marker} BEGIN
    # HermesAgency: inject applicable supervised-learning rules at
    # skill-load. Reverse-degradation: if the framework isn't
    # importable (e.g. mid-upgrade), the patch becomes a no-op rather
    # than breaking Hermes.
    try:
        from _framework.learning import inject_for_skill as _ha_inject
        _skill_id = (loaded_skill.get("name") or "").strip()
        _profile = loaded_skill.get("profile") or ""
        _role = loaded_skill.get("role") or ""
        _voice_tags = loaded_skill.get("voice_tags") or []
        if _skill_id:
            _rules_md = _ha_inject(
                skill_name=_skill_id,
                profile=_profile,
                role=_role,
                voice_tags=_voice_tags,
            )
            if _rules_md:
                parts.append("")
                parts.append(_rules_md)
    except Exception as _ha_exc:  # pragma: no cover
        # Best-effort: do not break the skill load if injection errors.
        import sys as _sys
        print(f"[hermes-agency] inject_for_skill skipped: {{_ha_exc}}", file=_sys.stderr)
    # HERMES_AGENCY_PATCH:skill_load_injection END
"""
        return file_text.replace(anchor, injection_block, 1)


__all__ = ["SkillLoadInjectionPatch"]
