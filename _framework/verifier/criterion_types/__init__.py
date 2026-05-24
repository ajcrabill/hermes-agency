# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Criterion type implementations. Importing this package registers all
ten v0.1 types into the verifier's REGISTRY.

Adding a type: drop a new file in this directory that imports
`register` from `_framework.verifier.verifier` and decorates a handler.
"""

# Import each submodule so its @register(...) decorators run.
from . import (  # noqa: F401
    fs_checks,
    sql_checks,
    kanban_checks,
    learning_checks,
    http_checks,
    shell_checks,
)
