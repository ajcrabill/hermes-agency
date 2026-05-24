---
skill_id: prototype-from-example
profile: __shared__
role: __cross_role__
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Prototype from example

Cross-role shared skill: turn examples + audience + purpose into a
fast first draft, then iterate. The flywheel that makes "time-to-
prototype" the leading indicator of "time-to-final-content."

Used by:
- Writing: newsletter-drafting, workbook-drafting, white-paper
  creation, anything where the first-pass shape isn't obvious
- ChiefOfStaff: draft-composer when the operator says "match this
  thread's voice"
- BusinessDevelopment: opportunistic-outreach when copy-paste-from-
  a-pitch-template won't fit a specific signal
- AnalystJudge: dossier-builder when the format should match a
  prior dossier the operator liked

## What this skill does

Three phases:

### Phase 1 — Ingest

Accept examples from any source:
- HTTP / HTTPS URLs (fetched + tag-stripped)
- Local file paths (.txt, .md, .docx, .pdf — with available
  extractors)
- Raw text (paste-in)
- A kanban task body (already text)

The framework normalizes each source. Errors are flagged
per-source — one bad URL doesn't poison the others.

```python
from _framework.prototyping import ingest_examples
results = ingest_examples([
    "https://example.com/great-newsletter-issue",
    "/path/to/local/draft.docx",
    "Raw text I want to imitate here",
])
```

### Phase 2 — Style derivation

Analyze the examples for:
- Sentence rhythm (avg, median, p90 length distribution)
- Paragraph density
- Register (conversational / analytical / formal / instructional /
  narrative)
- Structural signals (headings, lists, quotes, code blocks)
- Distinctive phrases (recurring 2-4-word patterns)
- Formatting notes (operator-facing observations)

Output: `StyleSignature` object that renders into a markdown block
the LLM uses as drafting context.

```python
from _framework.prototyping import derive_style
sig = derive_style([r.text for r in results if r.text])
print(sig.to_prompt_block())
```

### Phase 3 — Prototype + iterate

Create a prototype row in `prototypes.db`. The LLM drafts the first
version with the style signature + audience + purpose + (optionally)
the raw example texts as context.

Each round of feedback creates a new `prototype_round` row:

```python
from _framework.prototyping import start_prototype, record_iteration

pid = start_prototype(
    name="June newsletter — onboarding feature",
    profile="libra",
    audience="K-12 superintendents",
    purpose="announce the new onboarding workflow + ask for feedback",
    example_sources=["https://example.com/prior-issue", "/path/to/jan-issue.md"],
    style_signature=sig.to_dict(),
    initial_draft=first_draft_text,
)

# Later, after owner feedback:
record_iteration(
    pid,
    draft_text=v2_text,
    feedback="Cut the opening anecdote. Move the ask earlier. Keep the closing.",
    change_summary="Tighter open, ask in para 2, closing intact.",
    feedback_source="owner",
)
```

The diagnostic helper tells the skill when iteration is stuck:

```python
from _framework.prototyping.iteration import convergence_diagnostic
diag = convergence_diagnostic(pid)
if diag["is_likely_stuck"]:
    # Reason might be "5 rounds without shipping" — surface to the
    # operator: "are we converging or do we need a fresh approach?"
    ...
```

## Inputs

- `name` — short description of what we're prototyping
- `audience` — who's reading
- `purpose` — what should the reader do / feel / know after
- `example_sources` — list of URLs / paths / raw-text snippets

## Supervised learning

Rules tagged `prototype-from-example`, `general`. Includes
per-operator preferences ("always check the prior 3 issues before
drafting a newsletter" type rules).

## Action surface

- (L1 draft-only) — produce first draft + style block
- (L4 structural-change) — write to prototypes.db

## Untrusted content

Examples from URLs are external. Each ingested source passes through
the prompt-injection scanner before being fed to the LLM. Defensive
content paraphrases trigger patterns; never quotes verbatim.

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{PROTOTYPES_DB}}"
      query: "SELECT * FROM prototypes WHERE name LIKE '%{{NAME}}%' ORDER BY created_at DESC LIMIT 1"
      expect_min: 1
  - type: file_exists
    args:
      path: "{{DRAFT_PATH}}"   # round 0's draft file
```

## Failure modes

- **Style derivation oversimplifies** — coarse signature misses
  what makes the examples actually distinctive. Mitigation: also
  pass the raw example texts to the LLM as context, not just the
  signature. The signature is a structured hint; the texts are
  the real reference.
- **Genre confusion** — examples are different genres than the
  target. Self-check: ask the operator "are these examples
  representative of what you want this to be?" before drafting.
- **Iteration loop stuck** — round 5+ without shipping. The
  convergence diagnostic surfaces this; the operator decides to
  ship, restart, or invite a different reviewer.

## Self-check

1. Did I ingest every example source the operator provided?
2. Did I derive the style signature, OR pass raw examples to
   the LLM, OR both? (Both is usually right.)
3. Did I create a prototype row + round 0 with the first draft?
4. After feedback: did I record the iteration with a meaningful
   change_summary?
5. After 5+ rounds without shipping: did I run convergence_
   diagnostic and surface its verdict?
