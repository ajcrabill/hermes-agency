# Contributing to HermesAgency

HermesAgency is MIT-licensed. Contributions welcome — the framework
gets better as more deployments stress it.

## Quick-start for contributors

```bash
git clone https://github.com/ajcrabill/hermes-agency
cd hermes-agency
pip install -e ".[dev,embed]"
pytest                        # run the test suite
agency audit --self           # framework self-audit must be clean
```

## What good contributions look like

### Bug reports
- A minimal reproduction (a failing test is gold)
- The framework version (`agency -V`)
- Self-audit output (`agency audit --self`)
- Relevant logs from `events.db` (`agency events --kind <kind>`)

### New skills
- Land under `templates/profiles/<role>/skills/_reference/`
- Must pass the audit (frontmatter / supervised-learning wire /
  verifier criteria / failure modes / self-check)
- Real, opinionated content. Stubs that say "TODO" don't help anyone.

### New framework subsystems
- Live under `_framework/<name>/`
- Schema in a dedicated `<name>_db.py` if persistence is needed
- Module `__init__.py` exports the public API; everything else
  internal
- A `tests/seams/test_<name>.py` covers the public surface
- Framework self-audit must remain clean (`framework-vendor-leak`
  is the most common gotcha — see §1.3 of the spec)

### Integrations
- Lazy-imported runtime client (the framework boots without the
  integration's optional deps installed)
- Profile-local credentials under `profiles/<id>/credentials/`
- `setup_interactive()` helper for the OAuth flow (or its
  equivalent)
- Same shape as `_framework/integrations/google_drive.py` —
  use it as the template

### New roles
- Self-contained extension (per spec §2.4)
- `templates/profiles/<role>/SOUL.md.template` +
  `standards.md.template`
- Role declared in `_framework/invariants.yaml::roles` with keyword
  list
- N reference skills under `templates/profiles/<role>/skills/_reference/`
- Tests for any subsystem the role depends on
- No framework-internal modifications beyond `invariants.yaml`

## Coding conventions

- Python 3.11+. Use type hints. `from __future__ import annotations`
  at the top of every framework file.
- Each `_framework/*/` module has a header: `# FRAMEWORK — owned by
  HermesAgency. Do not modify in a deployment;` (the audit catches
  files in `_framework/` that lack this).
- Cents-as-integers for money. Tokens-as-integers for cost. Avoid
  floating-point for any cumulative value.
- All paths derive from `_framework.constants`. Hardcoded paths
  are an audit finding.
- Tests live in `tests/seams/` (one of the five system seams),
  `tests/audit/`, or `tests/e2e/`. Use `@pytest.mark.seam` /
  `@pytest.mark.audit` / `@pytest.mark.smoke`.

## Vendor-neutrality

The framework names no model or provider in `_framework/` source.
Vendor identity lives in `deployment.yaml`. If you need to reference
a vendor in a docstring, doc, or test, that's fine — those are in
the skip-list. If the audit flags `framework-vendor-leak`, refactor
to use a generic placeholder (e.g. `<your-provider-id>` instead of
naming a specific vendor).

## Testing

- All new code needs tests. The suite runs in <2 seconds — no
  excuse to skip.
- Tests use the `tmp_agency` fixture for isolation. Never touch the
  real `$AGENCY_HOME`.
- Mock external services in tests (stub `_api_call`, pass a
  fake `fetcher`, etc.). The suite must run without network access.

## Commit + PR style

- Branch off `main`. Squash-merge when ready.
- Commit messages: imperative mood. First line under 72 chars.
  Body explains the why, not the what.
- Co-Authored-By trailer is welcome (humans + AI both contribute
  here).
- Open a PR with: what changed, why, test plan, any audit
  implications.

## Releases

- Semver. `patch` for fixes, `minor` for features, `major` for
  breaking changes (manifest schema, on-disk layout, public API).
- CHANGELOG.md gets a new section before each tag.
- `agency audit --self` must pass before tagging.
- `agency -V` reports the version; bump in three places (`_framework/__init__.py`,
  `pyproject.toml`, CHANGELOG.md).

## Reporting security issues

Don't open public issues for security findings. Email
aj@ajcrabill.com with the details. We'll respond within 72h.

## Code of conduct

Be the kind of contributor you'd want to receive a PR from.
Disagreements about technical direction are welcome; personal
attacks aren't.
