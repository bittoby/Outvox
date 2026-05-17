from utils.dnc_detector import DNCDetector


def test_detects_explicit_dnc_request():
    detector = DNCDetector()

    is_dnc, reason, confidence = detector.is_dnc_request(
        "Please stop calling me and remove my number."
    )

    assert is_dnc is True
    assert confidence >= 0.9
    assert reason


def test_soft_rejection_does_not_mark_dnc_once():
    detector = DNCDetector()

    is_dnc, reason, confidence = detector.is_dnc_request("No thanks, not right now.")

    assert is_dnc is False
    assert 0 < confidence < 0.7
    assert "Soft rejection" in reason


def test_should_end_call_for_dnc_request():
    should_end, reason = DNCDetector().should_end_call("Do not call me again.")

    assert should_end is True
    assert "DNC request" in reason
