"""
Validation models for the two-phase game engine.

ValidationResult represents the outcome of validating an ActionIntent
against the world rules. It indicates whether the action is allowed
and provides context for rejection handling.

See planning/two-phase-game-loop-spec.md Section: Validation & Rejection Handling

Example:
    >>> # Successful validation
    >>> result = ValidationResult(
    ...     valid=True,
    ...     context={"destination": "library"},
    ... )

    >>> # Failed validation
    >>> result = ValidationResult(
    ...     valid=False,
    ...     rejection_code=RejectionCode.EXIT_LOCKED,
    ...     rejection_reason="The basement door is locked.",
    ...     context={"requires_key": "iron_key"},
    ... )
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.event import RejectionCode, RejectionEvent, EventType


class ValidationResult(BaseModel):
    """Result of validating an ActionIntent against world rules.

    Validators return this to indicate whether an action is allowed.
    If not valid, the rejection_code and rejection_reason explain why.

    Attributes:
        valid: Whether the action is allowed
        rejection_code: Code indicating why validation failed (if invalid)
        rejection_reason: Human-readable reason for failure (if invalid)
        context: Additional context (destination, items revealed, etc.)
        hint: Optional hint for the player

    Example:
        >>> # Valid movement
        >>> result = ValidationResult(
        ...     valid=True,
        ...     context={"destination": "library", "first_visit": True},
        ... )

        >>> # Invalid: exit is locked
        >>> result = ValidationResult(
        ...     valid=False,
        ...     rejection_code=RejectionCode.EXIT_LOCKED,
        ...     rejection_reason="The basement door is firmly locked.",
        ...     context={"requires_key": "iron_key"},
        ...     hint="Perhaps there's a key somewhere...",
        ... )
    """

    valid: bool

    # Rejection details (required if valid=False)
    rejection_code: RejectionCode | None = None
    rejection_reason: str | None = None

    # Additional context for execution/narration
    context: dict[str, object] = Field(default_factory=dict)

    # Optional hint for the player
    hint: str | None = None

    @model_validator(mode="after")
    def check_rejection_fields(self) -> "ValidationResult":
        """Ensure rejection fields are present when valid=False."""
        if not self.valid:
            if self.rejection_code is None:
                raise ValueError("rejection_code is required when valid=False")
            if self.rejection_reason is None:
                raise ValueError("rejection_reason is required when valid=False")
        return self

    def to_rejection_event(self, subject: str | None = None) -> RejectionEvent:
        """Convert this ValidationResult to a RejectionEvent.

        Args:
            subject: The primary entity involved in the rejected action

        Returns:
            RejectionEvent suitable for the narrator

        Raises:
            ValueError: If called on a valid result

        Example:
            >>> result = ValidationResult(
            ...     valid=False,
            ...     rejection_code=RejectionCode.EXIT_LOCKED,
            ...     rejection_reason="The door is locked.",
            ... )
            >>> event = result.to_rejection_event(subject="basement_door")
        """
        if self.valid:
            raise ValueError("Cannot create RejectionEvent from valid result")

        # Type narrowing for mypy
        assert self.rejection_code is not None
        assert self.rejection_reason is not None

        return RejectionEvent(
            type=EventType.ACTION_REJECTED,
            rejection_code=self.rejection_code,
            rejection_reason=self.rejection_reason,
            subject=subject,
            context=dict(self.context),
            would_have=self.hint,
        )


# Convenience factory functions


def valid_result(**context: object) -> ValidationResult:
    """Create a successful ValidationResult.

    Args:
        **context: Additional context to include

    Returns:
        ValidationResult with valid=True

    Example:
        >>> result = valid_result(destination="library", first_visit=True)
        >>> assert result.valid
    """
    return ValidationResult(valid=True, context=dict(context))


def invalid_result(
    code: RejectionCode,
    reason: str,
    hint: str | None = None,
    **context: object,
) -> ValidationResult:
    """Create a failed ValidationResult.

    Args:
        code: The rejection code
        reason: Human-readable reason for rejection
        hint: Optional hint for the player
        **context: Additional context to include

    Returns:
        ValidationResult with valid=False

    Example:
        >>> result = invalid_result(
        ...     RejectionCode.EXIT_LOCKED,
        ...     "The door is locked.",
        ...     hint="Check the butler's quarters.",
        ...     requires_key="iron_key",
        ... )
        >>> assert not result.valid
    """
    return ValidationResult(
        valid=False,
        rejection_code=code,
        rejection_reason=reason,
        hint=hint,
        context=dict(context),
    )
