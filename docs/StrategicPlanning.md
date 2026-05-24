# Strategic Planning in HermesAgency

**Version:** 1.0 (2026-05-24)
**Companion to:** [`HERMES_AGENCY_SPEC.md`](./HERMES_AGENCY_SPEC.md) §1.1
**Author:** AJ Crabill — AI Developer for [Good Ancestor](https://www.GoodAncestor.com)

> *Adapted from a public-sector strategic-planning framework AJ has
> taught in school-systems work, with the governance-vs-management
> distinctions stripped out (not relevant in a one-owner business).
> The core three-layer alignment model — and the discipline of
> requiring every layer to be SMART — is preserved.*

---

## 0. Why this exists

A small business has limited resources. Intentional accomplishment
of what the owner is trying to achieve requires a strategic approach
to planning *and* implementation. **HermesAgency exists to be the
operational layer that makes a strategic plan executable** — a team
of agents working in concert toward the outcomes the owner has
declared, with each agent's work traceable back to those outcomes.

The hardest problem in running a small business isn't choosing
strategies. It's knowing whether the strategies you chose are
actually moving the things you care about. Most small businesses
operate at the **input layer** — busy, working hard, completing
tasks — without a structural way to ask "is this work moving the
outcomes I declared?" The strategic-planning model in this document
gives HermesAgency that structural answer.

A strategic plan in HermesAgency is **relentlessly focused on
identifying the aligned outcomes, outputs, and inputs that, when
implemented effectively, will drive improvements in what the
business is trying to accomplish over the next 1–3 years.**

While implementation begins with inputs that produce outputs and
lead to outcomes, **planning occurs in reverse**: it starts with the
end in mind (outcomes), then identifies the aligned data that
signals progress (outputs), and finally selects the aligned
strategies needed to drive that progress (inputs).

---

## 1. The three-layer model

Every well-formed strategic plan in HermesAgency has three layers,
each SMART, each aligned to the layer above:

```
   ┌───────────────────────────────────────────────────────────────┐
   │ Layer 1 — OUTCOMES (Goals)                                    │
   │   What success looks like at the end of the cycle.            │
   │   1-3 SMART statements. 1-3 year horizon. Knowable at         │
   │   end of cycle. Top entries in Goals.md.                      │
   └────────────────────────────┬──────────────────────────────────┘
                                │ aligned to
                                ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ Layer 2 — OUTPUTS (Interim Goals)                             │
   │   The mid-cycle measures that predict outcome accomplishment. │
   │   1-3 SMART Interim Goals per Outcome. 6-12 month horizon.    │
   │   Knowable in the midst of a cycle. Sub-entries in Goals.md.  │
   └────────────────────────────┬──────────────────────────────────┘
                                │ aligned to
                                ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ Layer 3 — INPUTS (Initiatives)                                │
   │   The strategies/activities the agency executes.              │
   │   1-5 SMART Initiatives per Interim Goal. Quarter-to-quarter. │
   │   Knowable at the start of a cycle. Each initiative is a      │
   │   structured set of skills + scripts owned by one profile.    │
   └───────────────────────────────────────────────────────────────┘
```

When implementation runs the other direction (inputs produce
outputs which lead to outcomes), the question the agency continuously
asks is:

> *"Are these inputs moving the needle on the outputs? And are the
> outputs collectively moving the needle on the outcomes?"*

That's where testability comes from. **For the question to be
answerable, every layer has to be SMART** — Specific, Measurable,
Achievable, Relevant, Time-bound. Without SMART at every layer, the
question becomes a vibes check, and a vibes check can be answered
"yes, things feel good" by an organization losing ground.

### 1.1 Outcomes (Goals)

Outcomes are results knowable *at the end* of a cycle. They're the
destination — what the owner says success looks like for the
business in 1-3 years.

A well-formed Outcome in HermesAgency:

- Is a **SMART statement** about a business result, not a process.
  ("Revenue from coaching engagements will increase from $180k in
  January 2025 to $300k by December 2027" — not "Get more clients" or "Work on
  coaching business.")
- **Names a measurable end state** that's challenging enough to
  require behavior change.
- Lasts **1-3 years**. Outcomes don't churn quarterly — if they're
  changing every quarter, they aren't outcomes, they're tactical
  goals miscategorized.
- There are **1-3 of them** (definitely no more than 5). The
  point of the discipline is forced prioritization. A small
  business with seven equal priorities has zero priorities.

Outcomes go at the top of `Goals.md`. Every other layer in the
strategic plan exists in service of these.

### 1.2 Outputs (Interim Goals)

Outputs are measures knowable *in the midst* of a cycle. Without
aligned outputs, the owner won't know whether the strategic plan is
working or not until the outcome cycle ends — at which point it's
too late to pivot.

A well-formed Output (Interim Goal) in HermesAgency:

- Is a **SMART statement** about a leading indicator that predicts
  the Outcome.
- Has a documented **alignment to its parent Outcome** — meaning
  the metric correlates ≥0.6 with outcome accomplishment (or, in
  the absence of historical data, is a defensible leading indicator
  per published research / personal experience / sector knowledge).
- Lasts **6-12 months**. Shorter than Outcomes, longer than
  Initiatives.
- There are **1-3 Interim Goals per Outcome**. Again, forced
  prioritization.

Outputs are also entries in `Goals.md`, nested under the Outcome
they predict.

### 1.3 Inputs (Initiatives = Skills + Scripts)

Inputs are the resources and strategies knowable *at the beginning*
of a cycle — what the agency actually *does*. In HermesAgency
terminology:

- An **agentic Initiative** is a **Skill** — an LLM-driven piece
  of work declared in a `SKILL.md` file, owned by a profile,
  fired on a schedule or in response to triggers.
- A **deterministic Initiative** is a **Script** — a code-driven
  piece of work (`.py` / `.sh`), owned by a profile, run on a
  schedule.

There's no separate "Initiative" object that wraps skills and
scripts. **The Initiative IS the skill or the script.** The
strategic-planning concept just names the role a skill or script
plays *in the strategic plan*: the input layer that produces
the outputs that drive the outcomes.

**What qualifies as a strategic Initiative** (six tests, all must
pass — these are what make a skill or script part of the
strategic plan vs. ad-hoc utility work):

1. **SMART objective** — the skill's / script's purpose
   (declared in its SKILL.md frontmatter or docstring) is SMART.
2. **One owner** — one profile is accountable for the skill /
   script.
3. **Real cadence** — the skill / script fires on a meaningful
   schedule (continuous, daily, weekly) producing actual output —
   not running paper-loops that produce nothing. (The analog of
   the "≥4 hours per week of leadership time" test from the
   source framework: for agents, "leadership time" is scheduled
   firings × meaningful per-firing output.)
4. **Uses real resources** — model tokens, integration credits,
   the owner's review attention. An Initiative that exists in a
   plan but has no resources assigned isn't an Initiative, it's
   a hope.
5. **Current state → future state** — the skill / script
   produces an artifact that changes something in the world.
6. **Owner has authority** — the profile owns the skill / script
   and the firing-cadence configuration.

If a skill or script fails any of these tests, **it's not a
strategic Initiative** — it might still exist as a utility (one-off,
exploratory, debug) but it doesn't belong in the strategic plan's
input layer.

Each strategic skill / script's SKILL.md (or script docstring)
IS the **Playbook page** — see §5. No separate `Initiatives/`
directory is needed; the alignment metadata lives in the skill
or script file itself.

### 1.4 Alignment is math, not opinion

For Output → Outcome alignment, the standard is **correlation
≥0.6** (or, in the absence of historical data, a defensible
leading-indicator argument).

For Input → Output alignment, the standard is **correlation ≥0.5**
(or a defensible argument that the Initiative drives the Interim
Goal).

If there are 100 candidate Initiatives in a small business,
**expect that ~95 of them won't be aligned**. That's not a
business problem; it's a reality-of-organizations problem. The job
of strategic planning is to notice that reality and **take
intentional steps to generate slightly more alignment tomorrow
than we had yesterday** — through Initiative selection, retirement
of misaligned work, and ongoing measurement.

A small-business owner using HermesAgency is essentially in the
position of a one-person school superintendent: choosing which
Initiatives the agency will execute and committing the resources
to make them go. The CoS agent's job is to help the owner *see*
the alignment math, propose Initiatives the owner might not have
considered, and surface drift when an Initiative stops being
aligned.

---

## 2. Guardrails — the parallel structure for non-negotiables

Outcomes describe **what to accomplish**. Guardrails describe
**what not to do while accomplishing it.** They're the owner's
values made structurally enforceable — the lines the owner
refuses to cross even in pursuit of the Outcomes.

A well-formed Guardrail in HermesAgency:

- Is a **prohibition statement** about how the work gets done,
  capturing one of the owner's core values. ("Honesty" → "The
  business will not publish, send, or sign content that
  misrepresents what the owner knows or believes.")
- Lasts as long as the Outcomes.
- Has **1-3 Interim Guardrails per Guardrail**, each SMART, each a
  leading indicator that the Guardrail is being honored.
- Has **1-5 Guardrail-aligned Initiatives per Interim Guardrail**,
  each a SMART set of skills/scripts that produces the honoring
  behavior.

Guardrails are not optional. They're the structural answer to the
question "what stops me from winning the wrong way?" Without them,
a strategically focused business can become a focused machine for
producing outcomes that violate the owner's actual values.

Guardrails live in `Guardrails.md` (parallel to `Goals.md`). As
of v0.22-spec, `Guardrails.md` replaces the older `Values.md` —
the values-as-character-traits framing wasn't structurally
enforceable; values expressed as Guardrails (prohibition
statements + SMART Interim Guardrails) are.

### 2.1 Where Guardrails are loaded — *not* always-on context

This is an important architectural distinction. **`Goals.md` is
part of the always-loaded background context. `Guardrails.md` is
not.** They have different roles in the framework:

| Doc | Role | Where it loads | Cadence |
|---|---|---|---|
| `Goals.md` | **Aim** — what to accomplish | `pre_llm_call` hook (every skill, every turn) | Continuous |
| `Guardrails.md` | **Brake** — what not to do | Sentinel + AnalystJudge + send-guard | Enforcement-time only |

Why the distinction matters: putting `Guardrails.md` in the
always-loaded prompt would bias the agency toward defensive
thinking on every turn (*"how could this go wrong? what
prohibition might this violate?"*). That's not how a good
strategic operator works. A good operator generates work *aimed*
at the Outcomes, then checks the work against the Guardrails. So
HermesAgency:

- Loads **`Goals.md`** at every `pre_llm_call` — the agency
  always knows what it's aiming at.
- Loads **`Guardrails.md`** into the **enforcement layer**:
  - **Sentinel** (spec §5) reads it at `on_session_start` /
    `on_session_end` to know what to flag in its watchdog role.
  - **AnalystJudge** (the audit, spec §7) reads it weekly to
    surface drift — Initiatives crossing lines, Interim
    Guardrails not being honored.
  - **Send-guard** (spec §6.4) reads it at outbound-mail
    `pre_tool_call` time to flag prohibited content before it
    leaves the agency.

In short: **the agency generates work in service of `Goals.md`;
the watchdog layer checks that work against `Guardrails.md`.**
Two different loops, two different cadences, two architecturally
distinct concerns.

Note also: **Sentinel itself is a guardrail in the architectural
sense** — it's the read-only watchdog that catches drift. The
doc is the content; Sentinel is the mechanism.

---

## 3. Quality criteria — what good Outcomes, Guardrails, and Interims look like

This section is mostly for the CoS to use during the `/agency
setup` interview when generating rough-draft `Goals.md` and
`Guardrails.md` documents. The framework is forgiving — Outcomes
and Interim Goals can be refined later — but the rough draft is
much more useful if it follows these construction rules.

### The SMART acronym, precisely

SMART means **Specific, Measurable, Attainable, Results-focused,
and Time-bound.** Each letter has a precise meaning in HermesAgency's
strategic-planning practice:

- **Specific** — the item declares a *narrow focus of action*;
  it's not trying to do everything at once, and it's not trying
  to be all things to all people.
- **Measurable** — the item has a **starting date (month/year)**
  and **ending date (month/year)**, AND a **starting point**
  (the measure's value at the starting date) AND an **ending
  point** (the measure's desired value by the ending date). The
  canonical form is: *"<Subject + measure> will increase (or
  decrease) from <starting point> in <starting month/year> to
  <ending point> by <ending month/year>."*
- **Attainable** — the *ending point* can be accomplished by the
  *ending date* using the currently available resources (**time,
  talent, and treasure**). Ambitious is fine; impossible is a
  hope, not a goal.
- **Results-focused** — the item is tied to the larger **vision
  and/or values of the business**. It's not a free-floating
  metric — it traces upward to something the owner has declared
  matters.
- **Time-bound** — the item has a starting date and an ending
  date (month/year form for both). No "ongoing," no "by next
  year," no fiscal-year shorthand. Specific months.

Why month/year (not "Q1 2027" or "FY2026"): quarters and fiscal
years vary by business; month/year is unambiguous, sortable, and
makes the time-bound dimension testable.

Quick reference: **Outcomes and Interim Goals are SMART;
Guardrails are NOT SMART** (they're prohibition statements about
values, so the Measurable + Attainable + Time-bound letters
don't apply); **Interim Guardrails are SMART** (they're the
measurable mid-cycle proxies that say a Guardrail is being
honored).

### 3.1 Quality criteria for Outcomes (top-level Goals)

An Outcome should:

- **Reflect a business outcome, not inputs or outputs.** "Revenue
  from coaching engagements" is an outcome; "hours spent coaching"
  is an input; "number of prospect calls" is an output. Outcomes
  are results, not activities.
- **Be a Goal, not a Vision.** A Vision is the 10-year aspiration
  ("be the trusted authority for X"). An Outcome is the next 1-3
  year SMART step toward it ("Monthly inbound coaching inquiries
  will increase from 1 in January 2026 to 8 by December 2027").
  If the statement reads as "perfection at scale," it's a Vision;
  pull it back.
- **Be SMART** (all five letters).
- **Have a starting date AND an ending date** in month/year form.
  Not just "by Q4 2027" or "FY2027" — pick the month
  (e.g., "by December 2027").
- **Have a starting point AND an ending point** in measurable
  units. Not "increase" — "increase from W on date Y to Z by
  date W."
- **Span 1-3 years.** Shorter than that is a tactical goal; longer
  is a vision. For the source framework (school systems) the range
  is 3-5 years; small businesses usually need a faster feedback
  loop, so 1-3 years fits better.
- **Be attainable** given the time and resources committed. A
  Goal too aspirational to be funded becomes a hope; pull it back
  until it's challenging-but-doable.
- **Be one of no more than five.** Three or fewer is typical and
  better. The discipline is forced prioritization — five "top
  priorities" means zero priorities.
- **Be informed by listening + data.** The owner should have
  collected feedback from relevant stakeholders (clients, peer
  business owners, a coach, the financial picture) and looked at
  baseline data before naming the Outcome. The CoS surfaces both
  during the interview.
- **Describe a specific subject, not "everyone."** "Coaching
  engagement revenue from existing clients" is specific; "all
  revenue" is generic. Specific subjects are easier to measure
  and easier to move.

Anti-patterns to flag during the interview:

- *"More clients"* — not measurable, not time-bound, no
  starting/ending point.
- *"Be the leading voice in X"* — that's a Vision, not a Goal.
  Ask: "Over the next 18 months, what would tell us we're on
  the way there?"
- *"100% client satisfaction"* — set at perfection; that's a
  Vision-shaped Goal. Pull it back to a measurable next step.
- *"Improve coaching skills"* — that's an input/process, not a
  business outcome.

### 3.2 Quality criteria for Guardrails

A Guardrail should:

- **Reflect a value of the owner, not a want, need, or strategy.**
  "Honesty" is a value; "send better emails" is a strategy.
  Guardrails capture the *values* expressed as enforceable
  prohibitions.
- **Be a prohibition statement.** "The business will NOT do X."
  Phrasing matters: "the business will not pursue clients whose
  work the owner would be embarrassed to publish" is a clean
  Guardrail; "the business should pursue ethical clients" is a
  permission/aspiration, not a prohibition.
- **Avoid tricky double-negative or weak language.** Phrases like
  *"shall not fail to..."* or *"shall not operate without..."*
  invert the prohibition and create implementation ambiguity.
  State the line cleanly.
- **Cover behavior the business might genuinely be tempted to
  cross.** A Guardrail no one would think of violating is dead
  weight. The good Guardrails name the temptations the owner
  knows they have ("would I trade integrity for the big retainer?
  No — write that down").
- **Be one of no more than five.** Three or fewer is typical.
  Same prioritization discipline as Outcomes.
- **NOT be SMART.** Guardrails are prohibition statements about
  values, which aren't measurable. The measurability lives in the
  **Interim Guardrails** that sit underneath each Guardrail (see
  §3.4). The Guardrail itself is qualitative — "we will not X" —
  and stable for 1-3 years.

Anti-patterns to flag during the interview:

- *"We value quality"* — that's a value statement, not a
  Guardrail. Push for: "We will not ship work that hasn't passed
  a quality check."
- *"We will deliver excellent service"* — permission framing,
  not prohibition. Push for: "We will not deliver work that
  doesn't meet the documented service standard."
- *"We will be honest"* — too vague. Push for a specific
  prohibition: "We will not publish, send, or sign content that
  misrepresents what the owner knows."

### 3.3 Quality criteria for Interim Goals (the leading indicators)

Interim Goals are SMART, and they have additional technical and
operational criteria beyond the Outcome's SMART criteria.

**Technical criteria** — what makes an Interim Goal *structurally*
correct:

- **SMART**, with all the same requirements as Outcomes (starting
  point + ending point + starting date + ending date + specific
  measurement + specific subject).
- **A leading indicator, not lagging.** The Interim Goal should
  move *before* the Outcome does. Revenue is a lagging indicator;
  number of qualified prospects in the pipeline is a leading
  indicator that predicts revenue.
- **A mid-cycle output**, not an input. An *input* is a resource
  or strategy knowable at the start of a cycle ("I will send 10
  emails per week"). An *output* is a result knowable during the
  cycle ("10% of recipients book a call"). Interim Goals are
  outputs.
- **A late output**, not an early output. An *early* output
  measures participation ("80% of prospects opened the email").
  A *late* output measures implementation quality ("80% of
  prospects who opened the email scheduled a follow-up call").
  Implementation-quality outputs are more predictive.
- **Has a defensible correlation with the Outcome.** The standard
  is ≥0.6 correlation when historical data exists; for a young
  business, a leading-indicator argument from sector knowledge or
  research is acceptable as a starting point. Revisit when 6-12
  months of data exist.
- **Is one of 1-3 per Outcome.** Three is the textbook target;
  for a one-owner business, 1-2 well-chosen Interim Goals are
  often plenty.

**Operational criteria** — what makes an Interim Goal *usable*:

- **If all the Interim Goals are accomplished, the Outcome is
  likely accomplished.** If the math doesn't add up — you can hit
  every Interim Goal and the Outcome can still miss — your Interim
  Goals are picking the wrong things.
- **The owner has ≥80% authority over what drives the metric.**
  An Interim Goal that depends on external actors the owner can't
  influence (the economy, a partner's behavior, a regulatory
  change) is too fragile. Pick something the agency can move.
- **Data is updatable multiple times per year**, ideally monthly
  or weekly.
- **Data can be monitored within 30-60 days of when it's
  collected.** Latency longer than that defeats the point of an
  Interim Goal (which exists to enable mid-cycle pivots).
- **The data source is reliable.** Highly variable or
  noise-prone metrics make false signals.
- **Considers unintended consequences.** A metric that incentivizes
  the wrong behavior (Goodhart's Law — "when a measure becomes a
  target, it ceases to be a good measure") needs a counterweight
  or a different metric.
- **Has only one data set per metric**, not multiple. Mixing data
  sources creates ambiguity.
- **Is predictive both upward and downward.** If the metric
  improves, the Outcome should also improve; if the metric
  declines, the Outcome should also decline. Asymmetric metrics
  hide problems.
- **Is the data the owner actually uses for decisions.** A metric
  that exists only on the dashboard but never informs a real
  choice is decorative.
- **Has explicit implementation behind it.** Some skill or script
  has to actually be producing the work that moves the metric.
  Interim Goals without resourced Initiatives behind them are
  hopes.

Anti-patterns to flag during the interview:

- *"Number of hours worked on X"* — that's an input, not an
  output.
- *"Number of emails sent"* — that's an early output
  (participation), not a late output (quality).
- *"Revenue"* under a 6-month Interim Goal — revenue is lagging;
  the Interim Goal should be something that *predicts* the
  revenue change before it shows up.

### 3.4 Quality criteria for Interim Guardrails

Interim Guardrails follow the same SMART + technical + operational
criteria as Interim Goals (above), with two differences:

- **Alignment to the Guardrail is a "reasonableness" check, not
  correlation math.** Because the Guardrail itself isn't SMART (it's
  a prohibition statement, not a metric), there's no correlation
  to compute between Interim Guardrail and Guardrail. The right
  question is: *"Would a reasonable third party agree that this
  Interim Guardrail is a defensible interpretation of the
  Guardrail?"* If yes, alignment passes. If a reasonable person
  would say "that's a stretch," either the Interim Guardrail needs
  refinement or the Guardrail needs to be re-stated more clearly.
- **The metric measures *honoring* the prohibition, not avoiding
  it.** "100% of prospects screened against the values-fit screen
  before contracting" is a positive measure of honoring the
  Guardrail. "Zero contracts signed with prospects who failed the
  screen" is also valid but harder to verify (you can't prove the
  absence). When possible, prefer positive measures.

### 3.5 How the CoS uses this section in the setup interview

During the `/agency setup clean` interview, the CoS:

1. Asks the owner for their first-pass Outcomes, Guardrails, and
   ideas about Interim Goals.
2. **Runs each candidate through the criteria above**, flagging
   missing pieces (no end date, no measurement instrument named,
   too aspirational, etc.) and proposing edits in real time.
3. Drafts the `Goals.md` and `Guardrails.md` files with the
   refined versions, plus comments naming any criterion that's
   weak or still unresolved (so the owner can revisit during
   weekly review).
4. Suggests skill/script candidates for the Initiative layer
   based on the owner's existing profile catalog.

The point isn't to make the rough draft perfect — the framework
is iterative and assumes weekly + quarterly revision. The point is
to make the rough draft *good enough* that the strategic plan can
start guiding the agency's behavior from day one.

---

## 4. What makes a skill/script a strategic Initiative

A strategic Initiative is any skill or script:

1. whose **purpose** (declared in SKILL.md frontmatter / script
   docstring) **is SMART**,
2. that is intended to move a business function from a **current
   state to a future state**,
3. that uses **business resources** (model tokens, integration
   credits, the owner's review attention, scheduler slots),
4. that has **one profile** as the owner,
5. and that **fires on a meaningful cadence** producing actual
   output — continuous, daily, weekly — not paper-loops that
   produce nothing.

A **Goal-aligned Initiative** is any strategic skill/script that:

- has a correlation ≥0.5 with an Interim Goal, AND
- is influenceable by the owner profile (the profile has
  authority over ~80% of the configuration that determines
  firing behavior).

A skill/script can exist in HermesAgency *without* being a
strategic Initiative — utility skills (one-off helpers), debug
scripts, experimental work. These don't appear in the strategic
plan. If a skill/script *should* be a strategic Initiative but
isn't (no alignment metadata, no Interim Goal parent), the
audit's `unaligned-skills` rule (§7.5) flags it for review.

---

## 5. The Initiative Playbook page — IS the SKILL.md / script docstring

Steps 1-3 (declare Outcomes, Outputs, Inputs) are **must-haves**
for a strategic plan. Step 4 — writing a Playbook page per
strategic Initiative — is captured in the artifact the skill or
script already needs: its `SKILL.md` (for agentic Initiatives) or
its module-level docstring (for deterministic Initiatives).

The strategic-planning fields go in the existing skill/script
frontmatter and body — no separate `Initiatives/` directory or
duplicate document. The SKILL.md / script docstring captures:

| Field | Frontmatter key (proposed) | What it answers |
|---|---|---|
| Outcome # & title | `outcome: O1` | Which Outcome does this serve? |
| Interim Goal # & title | `interim_goal: G1.1` | Which Interim Goal does this serve? |
| Title | (skill / script name) | Short name. |
| Description | (SKILL.md body / docstring) | One paragraph in plain language. |
| Outcome metric | `outcome_metric: ...` | The SMART lag measure for this skill/script's contribution. *"X will increase from W% on date Y to Z% by date W."* |
| Problem description | (body section) | What problem; what evidence supports that solving it will move the Interim Goal. |
| Solution description | (body section) | What's the proposed approach; what evidence supports it will solve the problem. |
| Owner | `owner_profile: devon` | The one profile accountable. |
| Resource cost | `resource_cost: ...` | Model tokens / week, integration credits / week, owner review hours / week. |
| Interdependent contributors | `depends_on: [...]` | Other skills/scripts/profiles this one needs. |
| Output metrics | `output_metrics: ...` | Mid-cycle indicators of effect. |
| Input metrics | `input_metrics: ...` | Effort measures — firing cadence, trigger counts. *Don't over-instrument*. |
| Status | `status: green` | Standardized color: **blue** (complete), **green** (on track), **yellow** (slipping), **red** (off track), **gray** (not started). |
| Correlation argument | `alignment_argument: ...` | Why this skill/script is predicted to move the Interim Goal (≥0.5 correlation, or a defensible leading-indicator argument). |

The audit (§7.5) checks:

- Every strategic skill/script's frontmatter has `outcome` +
  `interim_goal` + `outcome_metric` + `status`.
- Every active skill/script's status field has been updated
  within the cadence it declares.
- The strategic plan's Goals.md lists every active strategic
  Initiative (no orphans).

This collapses the Playbook page concept into the work that
already needs to happen — every skill/script *already* has a
SKILL.md or docstring. Strategic planning just adds a few
frontmatter fields and structural alignment metadata.

---

## 6. Three nested testability layers

The three-layer strategic-planning model has a matching set of
**three testability layers** — each layer answering a different
question about the plan's health, on a different cadence, via a
different mechanism in HermesAgency.

| Layer | Question it answers | Mechanism | Cadence |
|---|---|---|---|
| **Inputs** | "Are we implementing the strategies?" | The 7-step learning loop (spec §1.1) | Every turn (continuous) |
| **Inputs → Outputs** | "Are we deploying resources wisely?" | Weekly strategic-plan health check + audit alignment rules | Weekly / monthly |
| **Outputs → Outcomes** | "Do we have the right strategies to get the results the owner wants?" | Quarterly strategic review | Quarterly / annual |

The testability **nests**: the input test runs continuously and
feeds the mid-tier test, which runs weekly and feeds the top-tier
test, which runs quarterly. Each higher layer's test only produces
trustworthy data if the layer below it is passing — there's no
point asking "are these resources deployed wisely?" if the strategies
those resources fund aren't actually being implemented.

### 6.1 Input-layer testability — the 7-step learning loop

**The 7-step learning loop is the input-layer testability
mechanism.** Every correction the owner gives, every rule the
agency injects, every firing recorded — together these answer the
most-frequent testability question: *are we implementing the
strategies?*

When a skill that should be running an Initiative isn't producing
the expected drafts/artifacts, or when the agency keeps making the
same kind of mistake on a particular Initiative, the learning loop
surfaces it. The mechanism isn't:

- "are we busy?" (every business is busy)
- "are we producing output?" (output isn't outcome)

The mechanism is: *given the Initiatives we've declared and the
SMART input metrics on each, are the skills actually doing the work
to the standard we've set?* That's a continuous, every-turn test.

Without this layer, an Initiative could be paper-perfect but
implementation-broken — and the higher-level tests (are inputs
moving outputs? are outputs moving outcomes?) would produce
misleading data because the actual implementation never happened.

### 6.2 Mid-tier testability — inputs against interim goals

Once a week (default cadence), the strategic-plan health check
(§7.4) asks the next question: *are the implemented strategies (the
Initiatives we actually ran) moving the Interim Goal metrics they
were supposed to move?*

This is where alignment math has teeth. Each Initiative had a
declared correlation argument (≥0.5 with the Interim Goal); the
weekly check tests it against fresh data. Two failure modes:

- **The Initiative ran but the Interim Goal didn't move** — the
  alignment claim was wrong, or external conditions changed. The
  Initiative needs to be retired, restructured, or replaced.
- **The Initiative didn't run consistently** — the input-layer
  test already caught this; the mid-tier check confirms the gap
  is real and consequential, not just a noisy week.

This is the *"are we deploying resources wisely?"* question. Even
when implementation is solid, the resources may be aimed wrong.

### 6.3 Top-tier testability — interim goals against outcomes

Quarterly (or at a cadence appropriate to the Outcome horizon),
the strategic review runs the highest-level test: *are the Interim
Goals we've been chasing actually predictive of the Outcomes the
business owner wants?*

This is the slowest, most expensive question, and the most
important. A business can implement strategies flawlessly (input
test passes), deploy resources wisely (mid-tier test passes), and
still end the year with the wrong Outcome — because the entire
Interim Goal layer was aimed at the wrong leading indicators.

If multiple Interim Goals have moved and the Outcome hasn't,
**the alignment claim from Interim Goal to Outcome was wrong**.
That's not a failure of execution; it's a failure of the
strategic-planning theory. The fix is at the planning layer:
replace or re-scope the Interim Goals.

### 6.4 Why nested testability is load-bearing

Most "AI assistant" tools operate at the input layer only, without
any structural connection to outputs or outcomes. They make the
work go faster, but provide no answer to "is this work moving the
right metric?" Most strategic-planning tools operate at the outcome
layer only, without any structural connection to the daily work —
the plan sits in a doc somewhere while the work happens in tools
that don't know the plan exists.

HermesAgency closes both gaps by making **every test connect to the
next layer up**:

- The 7-step learning loop's corrections accumulate into rules
  that fire when a skill runs; the skill runs in service of an
  Initiative; the Initiative is the input layer of a specific
  Interim Goal; the Interim Goal is in service of an Outcome.
- The weekly health check doesn't just say "things are green or
  red"; it says *"Initiative X is firing reliably (input test
  passes), but Interim Goal X.Y isn't moving (mid-tier test
  fails) — your alignment claim needs review."*
- The quarterly review doesn't just ask "did we hit the Outcome?";
  it asks *"given the Interim Goal data we collected all year,
  were these the right Interim Goals?"*

The testability isn't a separate dashboard. It's the same data
structure (rules, firings, audit findings, alignment correlations)
read at three different time horizons. The owner can ask any of
the three questions at any time and get a data-grounded answer.

---

## 7. How HermesAgency operationalizes this

### 7.1 `Goals.md` and `Guardrails.md` as three-layer documents

```
Goals.md
├── Outcome 1 (SMART, 1-3yr)
│   ├── Interim Goal 1.1 (SMART, 6-12mo)
│   │   ├── skill: devon/lookalike-prospect-builder  (agentic Initiative)
│   │   └── script: devon/pipeline-watchdog.py       (deterministic Initiative)
│   └── Interim Goal 1.2 (SMART, 6-12mo)
│       └── skill: devon/potential-clients-nudger
├── Outcome 2 (SMART, 1-3yr)
│   └── ...
└── Outcome 3 (SMART, 1-3yr)
    └── ...

Guardrails.md
├── Guardrail 1 (prohibition statement)
│   └── Interim Guardrail 1.1 (SMART)
│       └── skill: cos/values-fit-screen-prepper     (agentic Initiative)
└── Guardrail 2
    └── ...
```

The references at the leaf level point at *existing* skill SKILL.md
files and script files — not at separate "Initiative" docs. The
SKILL.md (or script docstring) carries the alignment metadata in
its frontmatter (`outcome`, `interim_goal`, `outcome_metric`,
`status`, etc.) — see §5.

The structure isn't decorative — it's load-bearing. When an agent
fires a skill, it can ask: *which Initiative is this work in
service of? Which Interim Goal does that Initiative serve? Which
Outcome does that Interim Goal serve?* The chain has to close.
When it doesn't, that's a signal: either the work is misaligned,
or the strategic plan is missing the layer that would make the
work make sense.

### 7.2 Always-loaded context — Goals only, not Guardrails

Per spec §1.1, **`Goals.md` is part of the always-loaded
background** at every skill load, alongside `Personal.md`,
`Work.md`, `Clients.md`, and per-profile `SOUL.md`. The agency
never reasons in a vacuum about *what* to aim at; the layered
strategic structure (Outcomes → Interim Goals → Initiative refs)
is part of the context every turn.

**`Guardrails.md` is deliberately not in the always-loaded
context.** See §2.1 for the architectural reasoning. The short
version: aim belongs in the generation context; brake belongs in
the enforcement layer. The agency generates work aimed at the
Outcomes; Sentinel, AnalystJudge, and the send-guard check that
work against the Guardrails.

This is what makes the strategic plan operationally relevant: it's
not a document the owner writes once and forgets. The aim is a
live context the agency operates inside every minute; the brake is
a live check the watchdog layer runs at session boundaries and at
every outbound send.

### 7.3 Skills and scripts ARE the input layer

Skills are agentic Initiatives. Scripts are deterministic
Initiatives. There's no separate "Initiative" wrapper concept —
the strategic plan's input layer is **literally** the agency's
existing catalog of skills and scripts. The mapping is direct:

- A skill's SKILL.md frontmatter declares the Interim Goal it
  serves (`interim_goal: G1.1`), its outcome metric, its status,
  and its alignment argument.
- A script's module docstring (or sidecar metadata file) declares
  the same.
- The profile's cron schedule (`scheduler.db`) declares the
  rhythm on which each strategic skill/script fires.
- The verifier's per-skill criteria (§6) include "did this firing
  produce the kind of artifact that moves Interim Goal G1.1?"

This is what gives the alignment math something to chew on. A
strategic skill/script that fires regularly but produces nothing
that moves any Interim Goal is, by definition, unaligned — and
the audit flags it for retirement or re-purposing.

Not every skill or script needs to be strategic. A profile can
own utility skills (debug helpers, one-off exploratory work)
that aren't part of the strategic plan. The audit distinguishes:
strategic skills (with alignment metadata) get checked against
the plan; non-strategic skills get checked only against their own
verifier criteria.

### 7.4 Weekly testability cadence

Once a week (default; configurable), the CoS agent runs the
strategic-plan health check:

1. **For each Outcome:** is the relevant lagging indicator moving
   in the right direction at the expected pace? (Often the data
   isn't there yet — that's fine, but the absence is itself a
   signal.)
2. **For each Interim Goal:** is the SMART metric on track? If
   not, what does the data say about why?
3. **For each Initiative:** are the firings happening on cadence?
   Are the artifacts being produced? Has the Initiative been
   delivering the expected outputs?

The check is presented to the owner as a short weekly summary,
not as a dashboard to admire. The goal is: **point at the one or
two things that have drifted, name what's drifted, propose a
pivot.** The strategic plan is a tool for pivoting, not a tool for
self-congratulation.

### 7.5 The audit

HermesAgency's audit subsystem (§7 of the spec) checks for
strategic-plan alignment at every layer:

- **`unaligned-skills`** — skills that declare themselves
  strategic (frontmatter has `interim_goal: ...`) but the named
  Interim Goal doesn't exist in Goals.md, or the alignment
  argument is missing.
- **`unaligned-initiatives`** — strategic skills/scripts without
  a clear Interim Goal parent in Goals.md or Guardrails.md.
- **`unaligned-interim-goals`** — Interim Goals whose alignment
  argument to an Outcome is missing or weak.
- **`stale-skill-status`** — strategic skills/scripts whose
  `status` frontmatter field hasn't been updated within the
  declared cadence.
- **`abandoned-outcome`** — Outcomes that no strategic
  skill/script declares an alignment to.

These don't auto-fix anything. They produce findings the owner can
act on — typically during weekly review.

---

## 8. A worked example (small business)

> *Format only. Real plans require local listening and real data.*

### Outcomes

**Outcome 1 — Coaching practice revenue:**
*Annual revenue from one-on-one coaching engagements will
increase from $180k in January 2025 to $300k by December 2027.*

**Outcome 2 — Authority positioning:**
*Monthly inbound coaching inquiries originating from the owner's
published content will increase from 1 in January 2026 to 8 by
December 2027.*

### Outputs (Interim Goals under Outcome 1)

**Interim Goal 1.1 — Active engagements:**
*The number of active monthly coaching engagements will increase
from 5 in January 2026 to 9 by December 2026.*

**Interim Goal 1.2 — Engagement value:**
*The average revenue per coaching engagement will increase from
$3,000 per month in January 2026 to $3,500 per month by
December 2026.*

### Inputs (skills/scripts under Interim Goal 1.1)

**`devon/existing-client-commonality-analyzer`** *(agentic Initiative)*
- Frontmatter outcome metric: *"The number of 'look-alike'
  prospects identified by analyzing the common traits of existing
  satisfied clients will increase from 0 in February 2026 to 50
  by April 2026."*
- Owner profile: Devon (BD)
- Cadence: weekly firing, owner reviews biweekly
- Status: Green

**`devon/lookalike-prospect-builder`** *(agentic Initiative)*
- Frontmatter outcome metric: *"The number of look-alike prospects
  passed through to the nurture pipeline will increase from 0 in
  February 2026 to 50 per quarter by June 2026."*
- Owner profile: Devon (BD)
- Cadence: weekly firing
- Status: Green

**`devon/pipeline-watchdog.py`** *(deterministic Initiative)*
- Docstring outcome metric: *"The percentage of 'someday-maybe'
  leads receiving a timely nudge within 30 days of their stated
  check-back date will increase from 20% in March 2026 to 90% by
  June 2026, measured monthly."*
- Owner profile: Devon (BD)
- Cadence: daily run, owner reviews weekly digest
- Status: Yellow (nudge rate at 70% in week 6)

**`devon/potential-clients-nudger`** *(agentic Initiative)*
- Companion to pipeline-watchdog.py — drafts the actual nudge
  message in owner's voice.
- Owner profile: Devon (BD)
- Cadence: triggered by pipeline-watchdog
- Status: Green

### Guardrails

**Guardrail 1 — Work the owner is proud of:**
*The owner will not accept coaching engagements with clients whose
work would be a poor fit with the owner's published values.*

**Interim Guardrail 1.1 — Engagement fit screen:**
*The percentage of new coaching engagements that pass the
documented values-fit screen before contracting will increase
from 0% in February 2026 to 100% by March 2026, measured monthly.*

**`cos/values-fit-screen-prepper`** *(agentic Initiative serving
Interim Guardrail 1.1)*
- Frontmatter outcome metric: *"The percentage of new prospect
  conversations that produce a documented values-fit screen draft
  for the owner to review before a contract is offered will
  increase from 0% in February 2026 to 100% by March 2026."*
- Owner profile: CoS (Loriah)
- Cadence: per-prospect (triggered)
- Status: Blue

---

## 9. Common questions

### How often should the strategic plan be updated?

Strategic plans in HermesAgency are **living documents**.
Outcomes generally don't change during the plan's term (1-3
years). Interim Goals can adjust quarterly if the metrics aren't
predictive. Initiatives churn most frequently — start, succeed,
retire, replace — sometimes monthly. **The plan is updated as
circumstances on the ground require**, not on a fixed cadence.

The exception: a quarterly review where the owner deliberately
zooms out and asks "are these still the right Outcomes? The right
Interim Goals?" Even when the answer is "yes," asking the
question is the discipline.

### Does the plan ensure outcomes will improve?

No. **Plans must constantly evolve based on circumstances on the
ground.** A plan provides a starting point but can't be treated as
final. The point is the planning, not the plan.

Or, as one general put it: *"I find plans to be worthless, planning
to be indispensable."*

### How do I know if a skill/script is a strategic Initiative or just utility work?

Run the six tests in §1.3 against the skill or script. If it has
a SMART purpose, a clear owner profile, real resources, a
meaningful cadence, and the right authority — it's a strategic
Initiative and belongs in the plan. If it doesn't, it's either
utility work (legitimate but not strategic) or a hope (an
aspiration without resourcing).

A common failure mode: someone declares a skill is "for marketing"
but it has no SMART purpose, no firing cadence, no metric, no
alignment argument. HermesAgency's audit catches this — strategic
skills/scripts (those declaring an `interim_goal` in frontmatter)
are checked for completeness; if required fields are empty, the
`unaligned-initiatives` rule fires. Skills/scripts that don't
declare an `interim_goal` are treated as utility work and audited
against their own verifier criteria only.

### How do I know if an Interim Goal is aligned to an Outcome?

Alignment is **math, not opinion**. The Interim Goal's SMART
metric should have a moderate-to-strong correlation (≥0.6) with
the Outcome's metric.

In the absence of historical data (common for a young business),
the owner makes a defensible leading-indicator argument: "I
believe, based on sector knowledge / published research / personal
experience, that this Interim Goal predicts the Outcome." That's
acceptable as a starting point. The plan should then be revisited
once 6-12 months of data exist to validate or revise the alignment
claim.

### How do I know if an Initiative is aligned to an Interim Goal?

Same answer, lower bar — correlation ≥0.5 with the Interim Goal.
If 100 candidate Initiatives are evaluated, expect ~95 not to be
aligned. That's normal; it's a reality-of-organizations problem.
The strategic-planning job is to find and resource the few that
are.

### Who decides what's in the strategic plan?

In HermesAgency, the **owner is the final adopter**. The CoS agent
(and other profiles, when relevant) can propose Outcomes, Interim
Goals, and Initiatives based on data from the agency's operations,
sector signals, and the owner's stated priorities. The owner
accepts, edits, or rejects.

The CoS doesn't ship a plan over the owner's head. The owner doesn't
write a plan without the CoS's data-grounded proposals. The
collaboration model is **owner-as-decider + agency-as-proposer**.

### What's the relationship between the strategic plan and the
agency's daily work?

The strategic plan is the **scaffolding the daily work hangs from**.
Every skill firing, every script execution, every drafted email
should be (eventually) traceable to an Initiative → Interim Goal →
Outcome. When that traceability doesn't exist, one of two things
is true:

1. The skill is doing work the strategic plan didn't name as
   important. *Either the work is unimportant (retire it) or the
   plan is incomplete (add an Initiative or Interim Goal for it).*
2. The plan is too granular — work is structurally unmappable.
   *Coarsen the plan; not every email needs an Initiative.*

The judgment call between #1 and #2 is the owner's, surfaced by
the audit.

### What's the relationship between the strategic plan and the
agency's autonomy decisions?

The autonomy ladder (spec §4) graduates skills upward when they
prove they can operate reliably. Strategic-plan alignment is one
input to the autonomy decision: a skill that's well-aligned to an
Initiative *and* well-executing earns autonomy faster than a skill
that's well-executing but doesn't trace to anything. **Alignment is
a graduation gate, not just a process check.**

### What if I'm a solopreneur and "Initiative ownership by a profile"
sounds like overkill?

Fair. For a solo operation, the model still works — most
Initiatives will be owned by the owner (you) with agent profiles
as contributors. The point isn't the org-chart formality; it's the
**discipline of naming who's accountable** for moving a specific
SMART metric. Even a one-person shop needs to know which thing
they're personally moving this week vs. which thing an agent is
moving on its own.

When the agency grows, the Initiative-ownership structure scales
naturally — the same plan accommodates one human + six agents
today and three humans + twenty agents in two years, without a
restructuring.

---

## 10. Where this lives in HermesAgency

| Artifact | File / location |
|---|---|
| Framework doc (this file) | `docs/StrategicPlanning.md` |
| Outcomes + Interim Goals + skill/script refs | `Goals.md` (vault root) |
| Guardrails + Interim Guardrails + skill/script refs | `Guardrails.md` (vault root) |
| Agentic Initiatives (Playbook = SKILL.md) | `~/.hermes/agency-state/profiles/<profile>/skills/<skill>/SKILL.md` |
| Deterministic Initiatives (Playbook = script docstring) | `~/.hermes/agency-state/profiles/<profile>/scripts/<script>.py` |
| Always-loaded context wiring (Goals only) | spec §1.1 |
| Enforcement-layer wiring (Guardrails) | spec §1.7 rows 4, 6, 7 (Sentinel + AnalystJudge + send-guard) |
| Strategic-plan health check | weekly CoS skill (see §7.4 above) |
| Audit rules for strategic alignment | spec §7 / audit rules: `unaligned-skills`, `unaligned-initiatives`, `unaligned-interim-goals`, `stale-skill-status`, `abandoned-outcome` |
| Setup interview (initial plan capture) | `/agency setup` interview, the GOALS step (v0.23+: restructured as three-layer prompts) |

---

## 11. The single-paragraph summary

A HermesAgency strategic plan has three layers, all SMART:
**1-3 Outcomes** at the top (where the business is headed),
**1-3 Interim Goals per Outcome** in the middle (the mid-cycle
metrics that predict outcome accomplishment), and **1-5 Initiatives
per Interim Goal** at the bottom — where **agentic Initiatives are
skills** (LLM-driven, declared in SKILL.md) and **deterministic
Initiatives are scripts** (code-driven). A parallel structure of
**Guardrails → Interim Guardrails → Guardrail-aligned skills/scripts**
captures the non-negotiables. Alignment between layers is math, not
opinion — ≥0.6 correlation between Interim Goal and Outcome, ≥0.5
between Initiative (skill/script) and Interim Goal.

The three layers have **three matching testability layers**, each
on a different cadence:

- **Inputs** — *"Are we implementing the strategies?"* — answered
  continuously by the 7-step learning loop.
- **Inputs → Outputs** — *"Are we deploying resources wisely?"* —
  answered weekly by the strategic-plan health check + audit.
- **Outputs → Outcomes** — *"Do we have the right strategies?"* —
  answered quarterly by the strategic review.

The plan is always part of HermesAgency's operating background
context, so every skill firing happens with awareness of where it
sits in the layered structure. That discipline — structural,
testable at three cadences, never absent from the operating
context — is what makes HermesAgency a strategic operations layer
rather than just another AI assistant.
