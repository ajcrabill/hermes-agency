#!/usr/bin/env bash
# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
#
# autonomy_gate — runtime check before any consequential action.
#
# Usage:
#   autonomy_gate.sh <skill> <action-class> <profile>
#
# Exit 0 if allowed; exit 1 (with stderr explanation) if denied.
# When denied, the gate ALSO files a kanban task tagged tenant=audit
# so the operator sees the refusal.

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "usage: autonomy_gate.sh <skill> <action-class> <profile>" >&2
    exit 2
fi

SKILL="$1"
ACTION="$2"
PROFILE="$3"

# Delegate to the Python implementation so we share validation logic
# with the rest of the framework.
exec python3 -c "
import sys
from _framework.autonomy.autonomy_db import get_skill_level, get_action_class_min_level

skill = '${SKILL}'
action = '${ACTION}'
profile = '${PROFILE}'

try:
    min_level = get_action_class_min_level(action)
except ValueError as e:
    sys.stderr.write(f'unknown action class: {action}\n')
    sys.exit(2)

level = get_skill_level(skill, profile)
if level >= min_level:
    sys.exit(0)

sys.stderr.write(
    f'autonomy gate refused: skill {profile}:{skill} is L{level} '
    f'but action class {action} requires L{min_level}\n'
)
sys.exit(1)
"
