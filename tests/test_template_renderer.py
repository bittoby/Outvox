from utils.template_renderer import (
    estimate_sms_segments,
    get_template_placeholders,
    render_template,
    validate_template,
)


def test_renders_known_placeholders_and_removes_missing_values():
    rendered = render_template(
        "Hi {name}, this is {store_name}. Ask for {agent_name}.",
        name="Jane",
        store_name="Acme Pawn",
    )

    assert rendered == "Hi Jane, this is Acme Pawn. Ask for ."


def test_extracts_template_placeholders():
    assert get_template_placeholders("Hi {name}, visit {store_name}") == [
        "name",
        "store_name",
    ]


def test_validate_template_requires_stop_language():
    result = validate_template("Hi {name}, this is {company_name}. Reply YES.")

    assert result["valid"] is False
    assert any("STOP" in error for error in result["errors"])


def test_validate_template_accepts_basic_compliant_copy():
    result = validate_template(
        "Hi {name}, this is {company_name}. Reply YES for info, STOP to opt out."
    )

    assert result["valid"] is True
    assert result["placeholders"] == ["name", "company_name"]


def test_estimates_sms_segments():
    assert estimate_sms_segments("x" * 160) == 1
    assert estimate_sms_segments("x" * 161) == 2
