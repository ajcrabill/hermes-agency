# Minimal HermesAgency deployment

A 3-profile minimum-viable agency: ChiefOfStaff + KnowledgeBase +
SystemSentinel. The smallest configuration the framework accepts.

This directory is meant for reading + copying — not running directly.
The flow on a fresh machine:

```bash
git clone https://github.com/ajcrabill/hermes-agency ~/HermesAgency
cd ~/HermesAgency
./install.sh

# Replace placeholders in ~/.agency/deployment.yaml or copy this example:
cp docs/examples/minimal-deployment/deployment.yaml ~/.agency/deployment.yaml

# Edit ~/.agency/deployment.yaml — at minimum, set:
#   - deployment.owner, org_name, primary_email
#   - profiles[*].email (only for CoS)
#   - defaults.model / provider / base_url
#   - credentials reference (keychain:NAME or env:VAR)

agency manifest-validate
agency status
```

## What this manifest doesn't include (intentionally)

- **Optional roles.** Analyst Judge, Business Development, and
  Writing Support are commented out of the default. Add them when
  you actually have work in those domains.
- **OAuth/ingress credentials.** The wizard's Tier 2 path captures
  these; the manifest only references them.
- **Custom roles.** Adding a FinanceAgent (or similar) is supported
  via `_framework/roles/<id>/` or `~/.agency/custom-roles/<id>/`
  — see `docs/ROLES.md`.

## Validation

After editing your `~/.agency/deployment.yaml`:

```bash
agency manifest-validate   # required: must report no errors
agency status              # quick health: validates + checks state dirs
agency audit --self        # framework self-audit (independent of deployment)
```

If `manifest-validate` reports errors, fix them before going further.
Warnings are non-blocking but worth reading.
