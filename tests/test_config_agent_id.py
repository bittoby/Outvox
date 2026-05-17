"""Tests for ``AgentConfig.get_formatted_agent_id``.

Agent IDs cross many trust boundaries (frontend display, log lines, database
``agent_id`` columns, webhook URLs). The normalization function is a tiny
piece of glue but, when it drifts, agents appear under multiple identities in
the dashboard. These tests pin its behaviour.
"""

import importlib

import pytest


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("OUT1", "Agent1"),
        ("OUT10", "Agent10"),
        ("1", "Agent1"),
        ("Agent5", "Agent5"),
        ("agent7", "Agent7"),
        ("  out3  ", "Agent3"),
    ],
)
def test_formatted_agent_id_known_shapes(raw, expected, monkeypatch):
    monkeypatch.setenv("AGENT_ID", raw)
    # Re-import config to pick up the new env var (module-level dataclass
    # defaults are evaluated once at import time).
    import config as config_module

    importlib.reload(config_module)
    assert config_module.config.agent.get_formatted_agent_id() == expected
