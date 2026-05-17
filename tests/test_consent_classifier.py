"""Unit tests for the SMS consent classifier.

These cover the compliance-critical YES / STOP / OTHER decision boundary.
Adding cases here is one of the safest ways to catch regressions before they
ship — get this wrong and you violate TCPA opt-out handling.
"""

import pytest

from services.consent_classifier import classify_reply


@pytest.mark.parametrize(
    "body",
    [
        "YES",
        "yes please",
        "Yeah call me",
        "sounds good",
        "Confirmed",
        "OK call me back",
        "absolutely interested",
    ],
)
def test_yes_replies(body):
    assert classify_reply(body) == "YES"


@pytest.mark.parametrize(
    "body",
    [
        "STOP",
        "stop calling me",
        "Please remove me from your list",
        "unsubscribe",
        "do not call",
        "leave me alone",
        "no thanks",
        "Not interested",
        "opt-out",
    ],
)
def test_stop_replies(body):
    assert classify_reply(body) == "STOP"


@pytest.mark.parametrize(
    "body",
    [
        "who is this?",
        "What company are you with",
        "I'll think about it",
        "hello",
        "",
        None,
        12345,
    ],
)
def test_other_replies(body):
    assert classify_reply(body) == "OTHER"


def test_stop_wins_over_yes_when_both_present():
    # If the same message contains both "stop" and "yes" we MUST treat it as
    # STOP — opt-out compliance takes priority over consent capture.
    assert classify_reply("yes but stop calling") == "STOP"


def test_punctuation_does_not_affect_classification():
    assert classify_reply("Yes!!!") == "YES"
    assert classify_reply("STOP.") == "STOP"
