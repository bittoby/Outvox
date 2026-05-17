from core.media_stream_token import (
    generate_media_stream_token,
    validate_media_stream_token,
)


def test_media_stream_token_round_trip(monkeypatch):
    monkeypatch.setenv("MEDIA_STREAM_TOKEN_SECRET", "test-secret")

    token = generate_media_stream_token(42, "+15551234567", "OUT1")

    assert token
    assert validate_media_stream_token(token, "42", "+15551234567", "OUT1")


def test_media_stream_token_rejects_wrong_lead(monkeypatch):
    monkeypatch.setenv("MEDIA_STREAM_TOKEN_SECRET", "test-secret")

    token = generate_media_stream_token(42, "+15551234567", "OUT1")

    assert not validate_media_stream_token(token, "43", "+15551234567", "OUT1")
