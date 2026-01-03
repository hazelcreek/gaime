"""Unit tests for validation models.

Tests cover:
- ValidationResult creation and constraints
- Factory functions for creating results
- Conversion to RejectionEvent
"""

import pytest
from pydantic import ValidationError

from app.engine.two_phase.models.event import EventType, RejectionCode
from app.engine.two_phase.models.validation import (
    ValidationResult,
    invalid_result,
    valid_result,
)


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result(self) -> None:
        """ValidationResult can indicate success."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.rejection_code is None
        assert result.rejection_reason is None
        assert result.context == {}
        assert result.hint is None

    def test_valid_with_context(self) -> None:
        """Valid result can include context."""
        result = ValidationResult(
            valid=True,
            context={"destination": "library", "first_visit": True},
        )

        assert result.valid is True
        assert result.context["destination"] == "library"
        assert result.context["first_visit"] is True

    def test_invalid_result(self) -> None:
        """ValidationResult can indicate failure with details."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
        )

        assert result.valid is False
        assert result.rejection_code == RejectionCode.EXIT_LOCKED
        assert result.rejection_reason == "The door is locked."

    def test_invalid_with_hint(self) -> None:
        """Invalid result can include a hint."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
            hint="Perhaps there's a key in the bedroom.",
        )

        assert result.hint == "Perhaps there's a key in the bedroom."

    def test_invalid_requires_code(self) -> None:
        """Invalid result must have rejection_code."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult(
                valid=False,
                rejection_reason="The door is locked.",
                # Missing: rejection_code
            )

        assert "rejection_code is required" in str(exc_info.value)

    def test_invalid_requires_reason(self) -> None:
        """Invalid result must have rejection_reason."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult(
                valid=False,
                rejection_code=RejectionCode.EXIT_LOCKED,
                # Missing: rejection_reason
            )

        assert "rejection_reason is required" in str(exc_info.value)


class TestToRejectionEvent:
    """Tests for ValidationResult.to_rejection_event()."""

    def test_converts_to_event(self) -> None:
        """Invalid result can be converted to RejectionEvent."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The basement door is locked.",
        )

        event = result.to_rejection_event()

        assert event.type == EventType.ACTION_REJECTED
        assert event.rejection_code == RejectionCode.EXIT_LOCKED
        assert event.rejection_reason == "The basement door is locked."

    def test_includes_subject(self) -> None:
        """Conversion can include subject entity."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
        )

        event = result.to_rejection_event(subject="basement_door")

        assert event.subject == "basement_door"

    def test_preserves_context(self) -> None:
        """Conversion preserves context dict."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
            context={"requires_key": "iron_key"},
        )

        event = result.to_rejection_event()

        assert event.context["requires_key"] == "iron_key"

    def test_hint_becomes_would_have(self) -> None:
        """Hint is used as would_have in the event."""
        result = ValidationResult(
            valid=False,
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
            hint="Access the basement",
        )

        event = result.to_rejection_event()

        assert event.would_have == "Access the basement"

    def test_valid_result_raises(self) -> None:
        """Cannot convert valid result to RejectionEvent."""
        result = ValidationResult(valid=True)

        with pytest.raises(ValueError) as exc_info:
            result.to_rejection_event()

        assert "valid result" in str(exc_info.value)


class TestFactoryFunctions:
    """Tests for validation factory functions."""

    def test_valid_result_factory(self) -> None:
        """valid_result() creates a successful validation."""
        result = valid_result()

        assert result.valid is True

    def test_valid_result_with_context(self) -> None:
        """valid_result() accepts context kwargs."""
        result = valid_result(destination="library", first_visit=True)

        assert result.valid is True
        assert result.context["destination"] == "library"
        assert result.context["first_visit"] is True

    def test_invalid_result_factory(self) -> None:
        """invalid_result() creates a failed validation."""
        result = invalid_result(
            RejectionCode.NO_EXIT,
            "There's no way to go north.",
        )

        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT
        assert result.rejection_reason == "There's no way to go north."

    def test_invalid_result_with_hint(self) -> None:
        """invalid_result() accepts optional hint."""
        result = invalid_result(
            RejectionCode.EXIT_LOCKED,
            "The door is locked.",
            hint="Check the bedroom for a key.",
        )

        assert result.hint == "Check the bedroom for a key."

    def test_invalid_result_with_context(self) -> None:
        """invalid_result() accepts context kwargs."""
        result = invalid_result(
            RejectionCode.EXIT_LOCKED,
            "The door is locked.",
            requires_key="iron_key",
        )

        assert result.context["requires_key"] == "iron_key"
