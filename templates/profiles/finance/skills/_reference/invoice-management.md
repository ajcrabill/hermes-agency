---
skill_id: invoice-management
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Invoice management

Prepare invoices out, log invoices in, follow up on overdue. Money
movement (sending invoices, paying vendors) requires {{OWNER_NAME}}
authorization via CoS.

## What this skill does

Four flows:

1. **Prepare outbound invoice** — given a client + line items +
   amount, draft an invoice file (PDF or markdown) + log to
   `invoices_out`. Hand to CoS for send via Gmail. CoS sends; this
   skill marks `sent_at` once confirmation arrives.

2. **Log inbound invoice** — given a vendor email with an invoice
   attachment, extract amount/due-date/vendor-id, log to
   `invoices_in`, propose categorization, schedule payment.
   Triggered by `obligation-extractor` when an invoice arrives.

3. **Follow up on overdue (outbound)** — daily, check
   `overdue_invoices_out()`; for each, draft a reminder for CoS to
   send + file a kanban task with escalating friction (3d, 7d,
   14d, 30d).

4. **Surface upcoming (inbound)** — daily, check unpaid
   `invoices_in` with `due_at` ≤ 7 days; surface to {{OWNER_NAME}}
   for payment authorization.

## Inputs

- (Prepare) `client`, `line_items[]`, `amount_cents`, `due_in_days`
- (Log inbound) `vendor`, `amount_cents`, `due_at`, `attachment_path`
- (Follow up) automatic via cron

## Supervised learning

Rules tagged `invoice-management`, `general`, `role:finance`.
Per-client payment-terms ("Acme nets 60"), per-vendor categorization
calibration.

## Action surface

- (L1 draft-only) — invoice drafts, follow-up drafts
- (L4 structural-change) — log to finance.db

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{FINANCE_DB}}"
      query: "SELECT * FROM invoices_out WHERE id={{INVOICE_ID}}"
      expect_rows: 1
```

## Failure modes

- **Lost confirmation** — operator sent the invoice but the
  confirmation didn't make it back to me. `sent_at` stays null.
  Mitigation: weekly check for invoices with `created_at` >7d
  ago + `sent_at` null.
- **Double-billing** — same invoice prepared twice. Dedup by
  (client, period, amount, description-hash) before draft.
- **Wrong category on inbound** — vendor invoice categorized
  wrong. `expense-categorizer` corrects; learning rule captures.

## Self-check

1. Before drafting an outbound: does the client have outstanding
   unpaid invoices? Surface those first.
2. For inbound: did I propose a category (not leave as
   `uncategorized`)?
3. For overdue follow-up: am I respecting the escalation cadence
   (3d/7d/14d/30d) — not over-nudging?
