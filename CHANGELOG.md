# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

## [Unreleased]

### Added
- Initial framework skeleton (Week 1 of v0.1 build per HERMES_AGENCY_V0.1_SPEC.md)
- `_framework/` tree with empty submodules for learning, autonomy, verifier, sentinel, send_guard, audit, scaffolds, kanban_patches, lifecycle, quality, state, ops/init, roles
- `_framework/constants.py` — brand-agnostic path constants
- `_framework/invariants.yaml` — single source of truth for tenants, action classes, ALWAYS_BLOCK audit rules
- `_framework/manifest.py` — `deployment.yaml` schema + validator
- `templates/deployment.yaml.template` — operator-facing manifest template
- `install.sh` — bootstrap script (placeholder)
- `pyproject.toml` — Python packaging
- `README.md` — public-facing pitch + quickstart
- `LICENSE` — MIT

## [0.1.0] — pending

First public release. Acceptance bar: §12.1 of `HERMES_AGENCY_V0.1_SPEC.md`.
