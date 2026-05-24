# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Guardrails.md loader — for the enforcement layer ONLY.

Per spec §1.1 + v0.22.4-spec aim/brake split, Guardrails.md is NOT
loaded into the always-on prompt context (that's
`_framework.agency_docs`). Instead, it's read by:

  - Sentinel (on_session_start/end) — to know what to flag
  - Send-guard (pre_tool_call for outbound mail) — to flag
    prohibited content before send
  - AnalystJudge / Audit (weekly) — to surface Interim Guardrail
    drift

**Important architectural note: Guardrails themselves are value
statements and are NOT SMART / NOT objectively measurable.** What
is measurable — and what monitoring + audit work focuses on — is
the **Interim Guardrails** that sit underneath each Guardrail.
Interim Guardrails are SMART (starting point + ending point +
starting date + ending date + specific measurement). Per
StrategicPlanning.md §3.4 and the inference rule:

  *If the Interim Guardrails are within parameter, we infer the
  Guardrail is being honored.*

The reverse: when an Interim Guardrail drifts out of parameter,
the Guardrail is at risk. Sentinel / audit work on Interim
Guardrails; the Guardrails themselves are stable value
statements that the Principal owns.

Public API:

  load_guardrails() -> str
      The raw markdown body of Guardrails.md. Empty string if the
      file doesn't exist or can't be read.

  load_guardrails_parsed() -> dict | None
      Best-effort parse of the three-layer structure (Guardrails,
      Interim Guardrails, Initiative refs). None if the file is
      absent or completely unparseable. Callers measuring
      compliance work on the `interim_guardrails` field; the
      `guardrails[].title` and `guardrails[].statement` are
      context, not metrics.
"""

from .loader import load_guardrails, load_guardrails_parsed

__all__ = ["load_guardrails", "load_guardrails_parsed"]
