#!/usr/bin/env bash
# HermesAgency bootstrap installer.
#
# Run from the cloned repo root:  ./install.sh
#
# What it does:
#   1. Verifies Python 3.11+ + Hermes engine
#   2. Installs the package (editable install with pip)
#   3. Creates the deployment skeleton at $AGENCY_HOME (default ~/.agency)
#   4. Writes a deployment.yaml from the template (placeholders left in)
#   5. Prints next steps (run `agency init` to fill in the placeholders)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENCY_HOME="${AGENCY_HOME:-$HOME/.agency}"

green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$1"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$1" >&2; }

# ── 1. Preflight ─────────────────────────────────────────────────────────
green "==> HermesAgency installer"
echo "  Repo:         $REPO_ROOT"
echo "  AGENCY_HOME:  $AGENCY_HOME"
echo

# Python
if ! command -v python3 >/dev/null 2>&1; then
    red "python3 not found. Install Python 3.11+ first."
    exit 1
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYMAJOR=$(echo "$PYV" | cut -d. -f1)
PYMINOR=$(echo "$PYV" | cut -d. -f2)
if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; }; then
    red "Python 3.11+ required (found $PYV)."
    exit 1
fi
green "  ✓ Python $PYV"

# Hermes engine — optional but warned
if command -v hermes >/dev/null 2>&1; then
    green "  ✓ Hermes engine on PATH"
else
    yellow "  ! 'hermes' not on PATH — install NousResearch Hermes before running agents."
    yellow "    https://github.com/NousResearch/hermes-agent"
fi

# pip
if ! python3 -m pip --version >/dev/null 2>&1; then
    red "pip not available. Install pip first."
    exit 1
fi
green "  ✓ pip"

# ── 2. Install package ───────────────────────────────────────────────────
green "==> Installing hermes-agency (editable)"
python3 -m pip install --quiet -e "$REPO_ROOT" || {
    red "pip install failed."
    exit 1
}
green "  ✓ Installed"

# ── 3. Deployment skeleton ───────────────────────────────────────────────
green "==> Provisioning deployment at $AGENCY_HOME"

mkdir -p "$AGENCY_HOME"/{profiles,_state,_health/audits,framework-vault}

if [ -f "$AGENCY_HOME/deployment.yaml" ]; then
    yellow "  ! deployment.yaml exists — not overwriting."
else
    cp "$REPO_ROOT/templates/deployment.yaml.template" "$AGENCY_HOME/deployment.yaml"
    green "  ✓ deployment.yaml (with placeholders — run 'agency init' to fill in)"
fi

echo "0.1.0" > "$AGENCY_HOME/framework-version.lock"
green "  ✓ framework-version.lock = 0.1.0"

# Copy shared framework docs into the framework-vault for Sentinel
for doc in DEVELOPMENT_PLAYBOOK.md; do
    if [ -f "$REPO_ROOT/$doc" ] && [ ! -f "$AGENCY_HOME/framework-vault/$doc" ]; then
        cp "$REPO_ROOT/$doc" "$AGENCY_HOME/framework-vault/$doc"
    fi
done
# A deployment-specific MASTER_PLAN.md is created during `agency init`.

# ── 4. Done ──────────────────────────────────────────────────────────────
echo
green "==> Install complete"
echo
echo "Next steps:"
echo "  1. Run the wizard:    agency init                  # tier 1 (5-10 min)"
echo "                        agency init --tier 2         # tier 2 (15-30 min)"
echo "                        agency init --tier 3         # tier 3 (45-60 min deep interview)"
echo "  2. Verify the spine:  agency status"
echo "  3. Open the panel:    https://localhost:9118/control-panel"
echo
echo "Edit $AGENCY_HOME/deployment.yaml directly to evolve the deployment."
