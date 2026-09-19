"""Canonical, case-sensitive action vocabulary."""

RECOGNIZED_ACTIONS = frozenset({
    "read", "lookup", "send", "create", "update", "delete", "remove", "destroy", "export",
})
DESTRUCTIVE_ACTIONS = frozenset({"delete", "remove", "destroy"})
