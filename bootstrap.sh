#!/usr/bin/env bash
# HermesAgency one-command bootstrapper.
#
# What this does, end-to-end:
#   1. (optional --reset) wipe ~/.agency, ~/.agency-venv, ~/.hermes
#   2. Clone HermesAgency (if not run from a checkout)
#   3. Create the agency venv at ~/.agency-venv
#   4. pip install -e the framework with [dev,google,embed,ingest] extras
#   5. Run `agency init` — wizard's Branch A/B step asks about Hermes
#      first (detect or install), then continues into T1 setup.
#
# Three invocation modes, same result:
#
# A) curl | bash (fastest, no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --reset
#
# B) git clone + run from outside the repo:
#   git clone https://github.com/ajcrabill/hermes-agency.git /tmp/ha \
#     && bash /tmp/ha/bootstrap.sh --reset
#
# C) Run from inside an existing clone:
#   bash bootstrap.sh                    # fresh install
#   bash bootstrap.sh --reset            # wipe first, then install
#
# Flags:
#   --reset             Wipe ~/.agency, ~/.agency-venv, ~/.hermes first
#   --reset-deep        Also wipe ~/HermesAgency, ~/.local/bin/hermes,
#                       and any v7 snapshots — full clean slate
#   --no-init           Stop before running `agency init` (just install)
#   --target=<dir>      Where to clone the repo (default: ~/HermesAgency)
#   --venv=<dir>        Where to make the venv (default: ~/.agency-venv)
#   --hermes-home=<dir> Where Hermes' HERMES_HOME will live (default: ~/.hermes)
#   --ref=<branch>      Which HermesAgency ref to install (default: main)
#   --skip-deps         Skip pip dependency installation (you have it)
#
# Exit codes:
#   0 — success
#   1 — preflight failed (python, git, etc.)
#   2 — install step failed
#   3 — agency init aborted by user

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────
RESET=false
RESET_DEEP=false
RUN_INIT=true
TARGET="${HOME}/HermesAgency"
VENV="${HOME}/.agency-venv"
HERMES_HOME_TARGET="${HOME}/.hermes"
REF="main"
SKIP_DEPS=false
GIT_URL="https://github.com/ajcrabill/hermes-agency.git"

# ── Parse args ───────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --reset)         RESET=true ;;
        --reset-deep)    RESET=true; RESET_DEEP=true ;;
        --no-init)       RUN_INIT=false ;;
        --target=*)      TARGET="${arg#*=}" ;;
        --venv=*)        VENV="${arg#*=}" ;;
        --hermes-home=*) HERMES_HOME_TARGET="${arg#*=}" ;;
        --ref=*)         REF="${arg#*=}" ;;
        --skip-deps)     SKIP_DEPS=true ;;
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

# ── Step 1: Reset (if requested) ─────────────────────────────────────────
if [[ "$RESET" == "true" ]]; then
    header "Wiping prior install"

    # Always-wiped on --reset
    for d in "${HOME}/.agency" "${HOME}/.agency-venv" "${HOME}/.hermes" \
             "${HOME}/.hermes-v7-snapshot" "${HOME}/.hermes-engine-venv"; do
        if [[ -e "$d" || -L "$d" ]]; then
            rm -rf "$d"
            echo "  removed: $d"
        fi
    done

    # Also wiped on --reset-deep
    if [[ "$RESET_DEEP" == "true" ]]; then
        for d in "${HOME}/HermesAgency" "${HOME}/.local/bin/hermes" \
                 "${HOME}/agency-staging"; do
            if [[ -e "$d" || -L "$d" ]]; then
                rm -rf "$d"
                echo "  removed: $d"
            fi
        done
        # If we wiped the repo we're running from, abort — can't continue
        if [[ "$INSIDE_REPO" == "true" && ! -f "$SCRIPT_DIR/pyproject.toml" ]]; then
            red "  --reset-deep wiped the repo we're running from — re-run via:"
            red "    git clone $GIT_URL /tmp/ha-bootstrap && \\"
            red "      bash /tmp/ha-bootstrap/bootstrap.sh"
            exit 0
        fi
    fi
    green "  ✓ wiped"
fi

# ── Step 2: Preflight ────────────────────────────────────────────────────
header "Preflight"

# Python 3.11+
if ! command -v python3 >/dev/null 2>&1; then
    red "  ✗ python3 not on PATH. Install Python 3.11+ first."
    red "    macOS:  xcode-select --install  (or brew install python@3.11)"
    red "    Linux:  apt/dnf install python3.11"
    exit 1
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYMAJOR=$(echo "$PYV" | cut -d. -f1)
PYMINOR=$(echo "$PYV" | cut -d. -f2)
if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; }; then
    red "  ✗ Python 3.11+ required (found $PYV)."
    exit 1
fi
green "  ✓ python $PYV ($(command -v python3))"

# git
if ! command -v git >/dev/null 2>&1; then
    red "  ✗ git not on PATH. Install git first."
    red "    macOS:  xcode-select --install"
    exit 1
fi
green "  ✓ git ($(command -v git))"

# ── Step 3: Clone (if needed) ────────────────────────────────────────────
if [[ "$INSIDE_REPO" == "true" ]]; then
    header "Using existing repo checkout"
    echo "  $TARGET"
else
    header "Cloning HermesAgency"
    if [[ -d "$TARGET" ]]; then
        if [[ -d "$TARGET/.git" ]]; then
            echo "  $TARGET already a git repo — fetching latest..."
            git -C "$TARGET" fetch --quiet origin || {
                red "  ✗ git fetch failed"; exit 2;
            }
            git -C "$TARGET" checkout --quiet "$REF" || {
                red "  ✗ git checkout $REF failed"; exit 2;
            }
            git -C "$TARGET" pull --ff-only --quiet || true
        else
            red "  ✗ $TARGET exists but isn't a git repo. Remove or pick a different --target."
            exit 2
        fi
    else
        git clone --quiet --branch "$REF" "$GIT_URL" "$TARGET" 2>&1 || {
            # If branch wasn't valid (e.g. a commit), retry without --branch
            git clone --quiet "$GIT_URL" "$TARGET" 2>&1 || {
                red "  ✗ git clone failed. Check network + repo access."
                red "    URL: $GIT_URL"
                red "    If the repo is private, configure SSH or a PAT first."
                exit 2
            }
            git -C "$TARGET" checkout --quiet "$REF" 2>&1 || true
        }
    fi
    green "  ✓ $TARGET (ref: $REF)"
fi

# ── Step 4: venv ─────────────────────────────────────────────────────────
header "Setting up venv"
if [[ -d "$VENV" ]]; then
    yellow "  ! $VENV already exists — reusing"
else
    python3 -m venv "$VENV"
    green "  ✓ created $VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
green "  ✓ activated"

# ── Step 5: pip install ──────────────────────────────────────────────────
if [[ "$SKIP_DEPS" == "true" ]]; then
    header "Skipping pip install (--skip-deps)"
else
    header "Installing HermesAgency + dependencies"
    pip install --quiet --upgrade pip setuptools wheel
    pip install --quiet -e "${TARGET}[dev,google,embed,ingest]" || {
        red "  ✗ pip install failed"
        exit 2
    }
    green "  ✓ installed (editable)"
    AGENCY_VERSION=$(agency --version 2>&1 | head -1)
    green "  ✓ $AGENCY_VERSION"
fi

# ── Step 6: run agency init (Branch A/B + T1) ────────────────────────────
if [[ "$RUN_INIT" == "true" ]]; then
    header "Running agency init"
    echo "  The wizard's first step (Branch A/B) handles Hermes:"
    echo "  - If Hermes is already installed somewhere, it'll detect it."
    echo "  - Otherwise it'll offer to install Hermes for you."
    echo
    echo "  After Hermes is set up, the wizard walks through the rest"
    echo "  of the deployment setup (owner, provider, profiles, etc.)."
    echo
    agency init || {
        rc=$?
        if [[ $rc -eq 3 ]]; then
            yellow "  ! agency init aborted (user chose to quit)"
            yellow "    Re-run when ready:  source $VENV/bin/activate && agency init"
            exit 3
        fi
        red "  ✗ agency init failed (exit $rc)"
        exit 2
    }
else
    header "Skipping agency init (--no-init)"
    echo "  When ready, run:"
    echo "    source $VENV/bin/activate"
    echo "    agency init"
fi

# ── Done ─────────────────────────────────────────────────────────────────
header "Done"
echo
echo "  Activate the agency venv in future shells with:"
echo "      source $VENV/bin/activate"
echo
echo "  Or add to your shell init (~/.zshrc):"
echo "      alias agency-on='source $VENV/bin/activate'"
echo
echo "  Useful commands:"
echo "      agency status         summary + Hermes detection"
echo "      agency next           actionable next steps for your state"
echo "      agency audit          run the audit suite"
echo "      agency panel          read-only control panel"
echo
