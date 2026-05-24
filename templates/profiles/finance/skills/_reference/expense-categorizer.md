---
skill_id: expense-categorizer
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Expense categorizer

Routes each expense to its category. The agency's chart of accounts
is operator-defined (no defaults — every agency's chart differs);
this skill applies it consistently.

## What this skill does

For each `expenses` row with `category = 'uncategorized'`:

1. Look at vendor + description + amount + date
2. Match against learning rules (which vendor → which category)
3. Match against historical pattern (this vendor was last
   categorized as X)
4. If high-confidence: write category directly
5. If low-confidence: surface to {{OWNER_NAME}} for one-click
   classification (which becomes a learning rule for next time)

## Inputs

- `expense_id` or batch of uncategorized expenses

## Supervised learning

Rules tagged `expense-categorizer`, `general`, `role:finance`. Each
classification {{OWNER_NAME}} makes becomes a rule the next match
applies automatically.

## Action surface

- (L1 draft-only) — propose categorization
- (L4 structural-change) — apply category to expense row

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{FINANCE_DB}}"
      query: "SELECT COUNT(*) AS n FROM expenses WHERE category='uncategorized'"
      expect_max: 5   # batch should bring uncategorized count below threshold
```

## Failure modes

- **Vendor name drift** — same vendor different name strings
  ("Stripe Inc" vs "stripe.com"). Normalize before matching.
- **Reclassification cascade** — operator reclassifies a vendor;
  prior expenses don't update. On rule update: propose
  retroactive reclassification of N most-recent matching expenses.

## Self-check

1. For each high-confidence categorization: cited the matching
   rule or historical pattern?
2. For each low-confidence: surfaced rather than guessed?
3. After operator classification: captured the learning rule?
