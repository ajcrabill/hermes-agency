#!/usr/bin/env bash
# HermesAgency plugin installer.
#
# HermesAgency is a PLUGIN for NousResearch's Hermes engine. It does
# NOT install Hermes — you install Hermes first via NousResearch's
# official installer, then run this to add the 7 reliability systems
# on top.
#
# The 4-step install roadmap:
#
#   1. curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
#   2. curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash    ← you are here
#   3. agency migrate v7 --from <path-to-v7-home>     (optional, if migrating)
#   4. hermes                                          ← daily use
#
# Three invocation modes for THIS installer:
#
# A) curl | bash (fastest, no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --reset
#
# B) git clone + run from outside the repo:
#   git clone https://github.com/ajcrabill/hermes-agency.git /tmp/ha \
#     && bash /tmp/ha/bootstrap.sh
#
# C) Run from inside an existing clone:
#   bash bootstrap.sh
#
# Flags:
#   --reset         wipe ~/.agency + ~/.agency-venv first (does NOT touch Hermes)
#   --no-init       install but don't run `agency init`
#   --no-patches    install but don't auto-apply hermes-patches
#   --target=<dir>  where to clone HermesAgency (default: ~/HermesAgency)
#   --venv=<dir>    where to make the venv (default: ~/.agency-venv)
#   --ref=<branch>  which HermesAgency ref to install (default: main)
#
# Exit codes:
#   0 — success
#   1 — Hermes not installed (Step 1 not done)
#   2 — install step failed
#   3 — agency init aborted

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────
RESET=false
RUN_INIT=true
APPLY_PATCHES=true
TARGET="${HOME}/HermesAgency"
VENV="${HOME}/.agency-venv"
REF="main"
GIT_URL="https://github.com/ajcrabill/hermes-agency.git"

# ── Parse args ───────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --reset)         RESET=true ;;
        --no-init)       RUN_INIT=false ;;
        --no-patches)    APPLY_PATCHES=false ;;
        --target=*)      TARGET="${arg#*=}" ;;
        --venv=*)        VENV="${arg#*=}" ;;
        --ref=*)         REF="${arg#*=}" ;;
        -h|--help)
            sed -n '2,40p' "$0"
            exit 0
            ;;
        *)
            echo "unknown flag: $arg" >&2
            echo "see: bash $0 --help" >&2
            exit 1
            ;;
    esac
done

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*" >&2; }
header() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }

# Detect whether we're running from inside the repo
INSIDE_REPO=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || SCRIPT_DIR=""
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/pyproject.toml" ]] \
   && grep -q '^name = "hermes-agency"' "$SCRIPT_DIR/pyproject.toml" 2>/dev/null; then
    INSIDE_REPO=true
    TARGET="$SCRIPT_DIR"
fi

# ── Step 0: Verify Hermes is installed (the prerequisite) ───────────────
header "Checking for Hermes engine"

if ! command -v hermes >/dev/null 2>&1; then
    red ""
    red "  ✗ Hermes is not installed."
    red ""
    red "  HermesAgency is a plugin — it requires Hermes (NousResearch's"
    red "  agent engine) to already be installed and on PATH."
    red ""
    red "  Install Hermes first:"
    red ""
    red "      curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
    red ""
    red "  Then reload your shell and re-run this installer:"
    red ""
    red "      source ~/.zshrc  # or ~/.bashrc"
    red "      curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash"
    red ""
    red "  Hermes docs: https://hermes-agent.nousresearch.com/docs/"
    red ""
    exit 1
fi

HERMES_VERSION=$(hermes --version 2>&1 | head -1)
green "  ✓ $HERMES_VERSION ($(command -v hermes))"

# ── Optional reset ───────────────────────────────────────────────────────
if [[ "$RESET" == "true" ]]; then
    header "Wiping prior HermesAgency state"
    echo "  (Hermes itself is NOT touched — only the agency plugin's state)"
    for d in "${HOME}/.agency" "${VENV}"; do
        if [[ -e "$d" || -L "$d" ]]; then
            rm -rf "$d"
            echo "    removed: $d"
        fi
    done
    green "  ✓ wiped"
fi

# ── Preflight ────────────────────────────────────────────────────────────
header "Preflight"

if ! command -v python3 >/dev/null 2>&1; then
    red "  ✗ python3 not on PATH. Install Python 3.11+ first."
    exit 1
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYMAJOR=$(echo "$PYV" | cut -d. -f1)
PYMINOR=$(echo "$PYV" | cut -d. -f2)
if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; }; then
    red "  ✗ Python 3.11+ required (found $PYV)."
    exit 1
fi
green "  ✓ python $PYV"

if ! command -v git >/dev/null 2>&1; then
    red "  ✗ git not on PATH. Install git first."
    exit 1
fi
green "  ✓ git"

# ── Clone HermesAgency (if not run from a checkout) ─────────────────────
if [[ "$INSIDE_REPO" == "true" ]]; then
    header "Using existing HermesAgency checkout"
    echo "  $TARGET"
else
    header "Fetching HermesAgency"
    if [[ -d "$TARGET" ]]; then
        if [[ -d "$TARGET/.git" ]]; then
            echo "  $TARGET already cloned — fetching latest..."
            git -C "$TARGET" fetch --quiet origin
            git -C "$TARGET" checkout --quiet "$REF"
            git -C "$TARGET" pull --ff-only --quiet || true
        else
            red "  ✗ $TARGET exists but isn't a git repo. Pick a different --target or remove it."
            exit 2
        fi
    else
        git clone --quiet --branch "$REF" "$GIT_URL" "$TARGET" 2>/dev/null || {
            git clone --quiet "$GIT_URL" "$TARGET"
            git -C "$TARGET" checkout --quiet "$REF" 2>/dev/null || true
        }
    fi
    green "  ✓ $TARGET (ref: $REF)"
fi

# ── Set up venv + pip install plugin ─────────────────────────────────────
header "Installing HermesAgency plugin"

if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
    green "  ✓ created venv at $VENV"
else
    green "  ✓ venv already at $VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -e "${TARGET}[dev,google,embed,ingest]" || {
    red "  ✗ pip install failed"
    exit 2
}
AGENCY_VERSION=$(agency --version 2>&1 | head -1)
green "  ✓ $AGENCY_VERSION installed"

# ── Run agency init (deployment skeleton) ───────────────────────────────
if [[ "$RUN_INIT" == "true" ]]; then
    header "Configuring deployment"
    if [[ -f "${HOME}/.agency/deployment.yaml" ]]; then
        yellow "  ! deployment.yaml exists — skipping init wizard"
        yellow "    (use 'agency reset' + re-run if you want a fresh deployment)"
    else
        echo "  Running agency init — this creates ~/.agency/ with your profiles"
        echo "  + deployment.yaml. Provider config (which LLM to use) is stored"
        echo "  in your Hermes config (see 'hermes model' / 'hermes setup')."
        echo
        agency init || {
            rc=$?
            if [[ $rc -eq 3 ]]; then
                yellow "  ! agency init aborted (user quit)"
                yellow "    Re-run when ready:  source $VENV/bin/activate && agency init"
                exit 3
            fi
            red "  ✗ agency init failed (exit $rc)"
            exit 2
        }
    fi
fi

# ── Register the Hermes plugin ──────────────────────────────────────────
# v0.17+ uses Hermes' documented plugin API instead of text-anchor patches.
# We drop a symlink at ~/.hermes/plugins/hermes-agency/ pointing at our
# plugin package; Hermes discovers it on next launch.
if [[ "$APPLY_PATCHES" == "true" ]]; then
    header "Registering plugin with Hermes"

    PLUGIN_DIR="${HOME}/.hermes/plugins"
    PLUGIN_LINK="${PLUGIN_DIR}/hermes-agency"
    PLUGIN_SRC="${TARGET}/hermes_agency_plugin"

    mkdir -p "$PLUGIN_DIR"

    if [[ -L "$PLUGIN_LINK" ]]; then
        existing=$(readlink "$PLUGIN_LINK")
        if [[ "$existing" == "$PLUGIN_SRC" ]]; then
            green "  ✓ plugin already registered at $PLUGIN_LINK"
        else
            yellow "  ! replacing stale symlink ($existing → $PLUGIN_SRC)"
            rm "$PLUGIN_LINK"
            ln -s "$PLUGIN_SRC" "$PLUGIN_LINK"
            green "  ✓ registered: $PLUGIN_LINK → $PLUGIN_SRC"
        fi
    elif [[ -e "$PLUGIN_LINK" ]]; then
        yellow "  ! $PLUGIN_LINK exists but isn't a symlink — skipping"
        yellow "    (remove it manually if you want this installer to manage it)"
    else
        ln -s "$PLUGIN_SRC" "$PLUGIN_LINK"
        green "  ✓ registered: $PLUGIN_LINK → $PLUGIN_SRC"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────
header "Done"
echo
echo "  Activate the venv in future shells:"
echo "      source $VENV/bin/activate"
echo "  Or add to your shell init:"
echo "      echo 'source $VENV/bin/activate' >> ~/.zshrc"
echo
echo "  Migrate v7 data (if you have a prior install):"
echo "      agency migrate v7 apply --from <path-to-v7-home>"
echo
green "  Use Hermes — it's now enriched by HermesAgency's plugin hooks:"
green "      hermes"
echo
echo "  Inside Hermes you can use /agency slash commands:"
echo "      /agency status      see deployment health"
echo "      /agency systems     see which of the 7 are wired"
echo "      /agency capture \"...\"  capture a learning correction"
echo "      /agency help        show all subcommands"
echo
