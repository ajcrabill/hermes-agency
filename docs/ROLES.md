# The six default roles

HermesAgency ships six default roles. A deployment activates any
subset (minimum three: CoS + KnowledgeBase + SystemSentinel) and
can add custom roles freely.

Each role ships with a `SOUL.md.template` (identity, voice,
posture) and a `standards.md.template` (operational quality floor).
Both are always-injected at skill-load time.

---

## ChiefOfStaffAgent — the owner's one face

**Role:** The owner's interface, top-level coordinator. The
agency's single inbound/outbound surface.

**Mode:** Coordinate, communicate, real-time ops. Multi-channel
ingress (email, chat, Signal, Slack, dashboard chat tab)
normalizes here.

**Sends mail:** **Yes** — the only outbound mail surface in the
default deployment.

**Starter skills (v0.1):**
- `owner-channels-ingress` — unified triage across email/chat/Signal/Slack
- `draft-composer` — drafts replies in the agency's voice
- `send-orchestrator` — the canonical send path; owns the send-guard
- `kanban-orchestrator` — claims tasks, spawns delegations
- `calendar-manager` — read/write calendar
- `morning-briefing` — daily summary
- `weekly-review` — Sunday recap
- `delegate-via-kanban` — route work to specialists
- `pipeline-watchdog` — own-pipeline observability

**Cadence:** Real-time. Most crons short-interval.

**Action classes:** draft-only (L1+), send-batched (L2+), send-single
(L3+). The only role that ships with send-* classes by default.

---

## KnowledgeBaseAgent — pure curator

**Role:** Classify, organize, retrieve, validate other agents' work
against the agency's IP. **Not** a producer.

**Mode:** Knowledge work. Verdicts + annotations + IP-aligned
context, not artifacts.

**Sends mail:** No — work routes in/out via CoS + kanban.

**Starter skills (v0.1):**
- `ip-curator` — maintains the agency's IP corpus
- `ip-alignment-check` — verdicts: `aligned` / `divergent` / `gap`
- `methodology-application-check` — verifies framework applied correctly
- `prior-decision-search` — "have we decided this before?"
- `meeting-evaluator` — evaluates meeting recordings/transcripts
- `quality-auditor` — second-tier verdict on work-product quality
- `kanban-verdict-publisher` — writes verdicts back as task comments

**What KB does NOT do:**
- Draft emails, posts, proposals, or any outbound content
- Publish newsletters (that's Writing → CoS sends)
- Create workbook pages (Writing)
- Author dossiers (Analyst)
- Send anything externally (CoS)

If asked to produce, KB's correct response is "I evaluate, not
produce — route this to [appropriate agent]."

**Cadence:** Mixed. 5m kanban poll for validation requests, 6h
quality audits, weekly IP-corpus health reports.

**Action classes:** draft-only (L1+), structural-change (L4+) — she
edits the IP corpus.

---

## SystemSentinelAgent — pure observability

**Role:** Watch. Read-only authority by code. See [`SENTINEL.md`](SENTINEL.md).

**Mode:** Frequent monitoring crons.

**Sends mail:** No — never sends, ever.

**Starter skills (v0.1):**
- `learning-monitor` (5m)
- `drift-monitor` (15m)
- `heartbeat-watch` (5m)
- `playbook-audit` (Sun 04:00)
- `event-rollup` (hourly)
- `compliance-report` (Sun 06:00)

**Cadence:** Frequent (most crons every 5-15m).

**Action classes:** Empty. Sentinel does not declare action
classes.

---

## AnalystJudgeAgent — adversarial review

**Role:** Red-team drafts, build dossiers, curate the learning
corpus. The judge of others' work.

**Mode:** Investigate, critique, judge. Project-paced.

**Sends mail:** No — internal only.

**Starter skills (v0.1):**
- `red-team` — critique drafts/plans/decisions
- `dossier-builder` — biographical + contextual research
- `research` — vault/web research grounded in agency goals
- `prompt-injection-defense` — security analysis on inbound
- `learning-curation` — dedupe, contradict-check, hardness audit
- `verifier-criteria-author` — write typed criteria for new task types
- `graduation-check` — manual override path for autonomy review

**Verdict discipline:** Three forms only.
- `approve` — sound, with 1-3 sentences of reasoning
- `revise: <specifics>` — fixable, name what to fix
- `block: <specifics>` — wrong premise, name the failure mode

`approve-with-notes` is not a verdict.

**Cadence:** Project-paced (hours to days per task). Crons
infrequent.

**Action classes:** draft-only (L1+), structural-change (L4+) — she
edits the learning corpus.

---

## BusinessDevelopmentAgent — outreach intelligence

**Role:** Lead-gen, news-driven outreach, journalist + podcast
relationship building, CRM hygiene.

**Mode:** Outbound intelligence. Daily news-driven plus weekly
strategic.

**Sends mail:** No — drafts go to CoS for review and send.

**Starter skills (v0.1):**
- `prospect-research` — daily-news-driven target identification
- `opportunistic-outreach` — same-day outbound drafts on news/events
- `journalist-relationship` — earned-media relationship building
- `podcast-host-relationship` — same shape for podcast booking
- `crm-sync` — CRM hygiene
- `weekly-opportunity-scan` — strategic pipeline summary

**Cadence:** Daily (news-driven) + weekly (strategic).

**Action classes:** draft-only (L1+), send-batched (L2+). She
drafts; CoS reviews and sends.

---

## WritingSupportAgent — author voice servant

**Role:** Author coaching (multi-author), staff workbook drafting,
weekly newsletter. Serves the author's voice; doesn't substitute
hers.

**Mode:** Content production. Per-author task pickup + cadenced
deliverables.

**Sends mail:** No — author correspondence flows through CoS.

**Starter skills (v0.1):**
- `book-coaching` — per-author coaching state, voice, project arc
- `manuscript-review` — feedback on author drafts
- `workbook-drafting` — staff-facing instructional content
- `newsletter-drafting` — weekly newsletter (drafts to CoS for send)
- `multi-author-state` — per-author project arcs, coaching
  histories, voice profiles in `context/writing-support/authors/`

**Cadence:** Per-author task pickup (5m kanban poll) + weekly
newsletter + ad-hoc workbook requests.

**Action classes:** draft-only (L1+), structural-change (L4+) — she
edits multi-author state.

---

## Adding custom roles

A deployment is not locked to these six. To add `FinanceAgent` or
`LegalAgent` or `ItOpsAgent`:

```bash
# Option 1: framework-level (PR to hermes-agency)
mkdir _framework/roles/finance/
# add SOUL.md.template + standards.md.template + starter skills

# Option 2: deployment-private
mkdir ~/.agency/custom-roles/finance/
# same shape; only this deployment uses it

# Then in deployment.yaml:
profiles:
  - id:           finance
    role:         finance
    persona_file: identities/finance.md
    email:        null
    starter_skills:
      - cash-flow-tracker
      - burn-rate-monitor

# Or with the CLI (v0.2 deliverable):
agency add-role finance --persona ./identities/finance.md \
    --starter-skills cash-flow-tracker,burn-rate-monitor
```

The framework supports N roles by design. Per-role keyword lists
in `invariants.yaml` extend automatically; the audit's role-
mismatch detector picks up new keywords without code changes.

---

## Single-mailbox by default

Only CoS has an outbound mailbox by default. Specialists draft;
CoS sends. The world sees one agency, one voice.

Deployments CAN override (give specialists their own mailboxes) —
the framework supports it. The default just ships single-mailbox
because that's what small-agency owners actually want: one persona
to manage, one outbound voice to maintain, one canonical send path
to audit.

When a specialist sets `email:` to anything other than `null`,
the manifest validator warns (`non-cos-mailbox` warning) — not
because it's wrong, but because the operator should be deliberate
about breaking the default.
