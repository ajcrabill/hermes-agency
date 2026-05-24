# Deployment

How to set up a new HermesAgency deployment from scratch.

## Prerequisites

- Python 3.11+
- git
- Access to an OpenAI-compatible inference endpoint — local
  (Ollama, llama.cpp, MLX, LM Studio) or hosted (any provider
  with a compatible API)
- An email address you control (for the Chief of Staff's outbound
  mailbox)

You do **not** need to install Hermes before HermesAgency. The
wizard's first step is **Branch A** (detect existing Hermes and
layer on top) or **Branch B** (install Hermes for you fresh from
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
then layer on top). Either path lands you in the same place: a
running Hermes engine with HermesAgency provisioned on top of it.

## Install

```bash
git clone https://github.com/ajcrabill/hermes-agency ~/HermesAgency
cd ~/HermesAgency
./install.sh
```

The installer:
1. Verifies Python and pip
2. Editable-installs `hermes-agency` (`agency` CLI now on PATH)
3. Provisions `~/.agency/` with the standard skeleton
4. Writes a placeholder `deployment.yaml` and a version-lock
5. Copies `DEVELOPMENT_PLAYBOOK.md` into `~/.agency/framework-vault/`

You can set a different deployment location:

```bash
AGENCY_HOME=/path/to/agency ./install.sh
```

## Configure

Run the wizard:

```bash
agency init              # Tier 1: 5-10 min, required fields only
agency init --tier 2     # Tier 2: 15-30 min, +OAuth +ingress
agency init --tier 3     # Tier 3: 45-60 min, +exemplar capture
```

Tier 1 is the v0.1 ship target. It asks for:

- Owner handle, organization name, primary email, timezone
- Provider id, model id, base URL, credential reference
- CoS profile id + outbound email
- KnowledgeBase profile id, Sentinel profile id

…and provisions a working deployment with sensible defaults for
everything else.

Tier 2 and Tier 3 are skeletons in v0.1 — they show where each
extension wires in. Full interactive flows ship in v0.2.

## Manifest schema

`~/.agency/deployment.yaml` is the deployment's source of truth.
Edit freely; framework upgrades never overwrite it.

Required top-level keys:

```yaml
deployment:
  owner:             <kebab-case handle>
  org_name:          <display name>
  primary_email:     <your email>
  timezone:          <IANA timezone>
  framework_version: "0.1.0"

profiles:
  - id: <your CoS name>
    role: chief-of-staff
    persona_file: identities/chief-of-staff.md
    email: <CoS outbound address>
    starter_skills: [...]
  - id: <your KB name>
    role: knowledge-base
    ...
  - id: <your Sentinel name>
    role: system-sentinel
    ...

defaults:
  model:    <model id>
  provider: <provider id from invariants.yaml::valid_providers>
  base_url: <OpenAI-compatible endpoint>
  fallback_providers: []

credentials:
  <provider id>: "keychain:<entry>"  # or "env:<VAR>"
```

Required roles: `chief-of-staff`, `knowledge-base`, `system-sentinel`.
Optional roles: `analyst-judge`, `business-development`,
`writing-support`. Custom roles supported (see [`ROLES.md`](ROLES.md)).

## Validate

```bash
agency manifest-validate
agency status -v
```

Errors must be fixed. Warnings are non-blocking but worth reading
— each one names a specific risk the operator may want to address.

## First steps after install

1. **Open SOUL.md and standards.md for CoS.**
   Edit them to fit your actual agency. The defaults are good
   starting points; they're meant to be customized, not used
   verbatim. Each agent's persona + quality floor are always-
   injected — every prompt they run carries these forward.

2. **Capture a first learning rule:**
   ```bash
   agency capture "Lead with craft, not metrics." \
       --skill draft-composer --role chief-of-staff
   ```
   Verify it landed:
   ```bash
   agency learn list
   ```

3. **Run the self-audit:**
   ```bash
   agency audit --self        # framework-only
   agency audit               # whole deployment
   ```
   The framework's audit should be clean. Your deployment audit
   may have warnings on freshly-scaffolded skills — fix or
   document as you build.

4. **Open the control panel:**
   `https://localhost:9118/control-panel` (after starting the
   service — see below).

## Inference provider

HermesAgency is vendor-neutral. The framework speaks OpenAI-
compatible API; the deployment picks the backend:

- **Local:** Ollama, llama.cpp, MLX, LM Studio, vLLM — any of
  these expose OpenAI-compatible endpoints.
- **Hosted:** any provider with OpenAI-compatible API (most do).
- **Mixed:** primary local + hosted fallback, or vice versa.

Set `defaults.provider` to the id from
`invariants.yaml::valid_providers`. The list is open — if your
provider isn't there, PR an addition (the list is a validation
enumeration, not a preference).

Credentials NEVER inline in `deployment.yaml`. Use:
- `keychain:<entry-name>` — macOS Keychain (recommended on Mac)
- `env:<VAR>` — environment variable
- `file:<path>` — file containing the token (chmod 600 strongly)

## What you DON'T do at first

- Don't promote skills past L1 in the first week. Let the gate
  earn promotions on track record.
- Don't fork Hermes. The framework applies patches via the post-
  update reapply hook (see [`PATCHES_TO_HERMES.md`](PATCHES_TO_HERMES.md));
  forking would lose Hermes updates.
- Don't modify files in `_framework/`. Customizations belong in
  `~/.agency/profiles/<id>/` or `deployment.yaml`. The audit's
  `framework-vendor-leak` rule and the file-ownership headers
  will catch deployment content that leaks into the framework.

## Upgrade

```bash
cd ~/HermesAgency
git pull
./install.sh    # idempotent; preserves your deployment
agency upgrade   # (v0.2 — currently a stub)
```

`framework-version.lock` records the version the deployment was
last validated against. The framework refuses to start against an
incompatible schema version.

## Backup

Your deployment data lives in `~/.agency/`. The state databases
(`_state/*.db`) and the operator content (`profiles/`) are what
you need to back up.

A snapshot is just a directory copy:

```bash
tar czf agency-backup-$(date +%Y%m%d).tar.gz -C ~ .agency/
```

The framework itself (`~/HermesAgency/`) is just a checked-out
repo — re-cloneable from GitHub.
