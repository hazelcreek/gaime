"""
Mock LLM client for deterministic testing.

This module provides a MockLLMClient that returns predetermined
responses based on prompt patterns, enabling testing of the full
two-phase flow without actual LLM calls.

Example:
    >>> mock = MockLLMClient({
    ...     "examine": '{"narrative": "You see a key."}',
    ...     "take": '{"narrative": "You pick up the key."}',
    ... })
    >>> response = await mock.complete("examine the key")
    >>> assert "You see a key" in response
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMCall:
    """Record of a single LLM call for test verification.

    Attributes:
        prompt: The prompt sent to the LLM
        response: The response returned
        matched_pattern: The pattern that matched (or "default")
    """

    prompt: str
    response: str
    matched_pattern: str


class MockLLMClient:
    """Mock LLM client for deterministic testing.

    Matches prompt contents against registered patterns and returns
    predetermined responses. Records all calls for test assertions.

    Attributes:
        responses: Dict mapping pattern strings to response strings
        call_history: List of all calls made to this mock

    Example:
        >>> mock = MockLLMClient({
        ...     "move north": '{"narrative": "You go north."}',
        ...     "examine": '{"narrative": "You look closely."}',
        ...     "default": '{"narrative": "Nothing happens."}',
        ... })
        >>>
        >>> # Patterns are matched against prompt content
        >>> result = await mock.complete("Player wants to move north")
        >>> assert "go north" in result
        >>>
        >>> # Check call history
        >>> assert len(mock.call_history) == 1
        >>> assert mock.call_history[0].matched_pattern == "move north"
    """

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        """Initialize with optional response mappings.

        Args:
            responses: Dict mapping pattern strings to response strings.
                       Patterns are matched with 'in' operator (substring).
                       Include a "default" key for fallback responses.
        """
        self.responses: dict[str, str] = responses or {}
        self.call_history: list[LLMCall] = []

    async def complete(self, prompt: str) -> str:
        """Simulate an LLM completion call.

        Matches the prompt against registered patterns (in order of
        registration) and returns the first matching response.

        Args:
            prompt: The prompt to "send" to the LLM

        Returns:
            The predetermined response for the matching pattern,
            or the default response, or an empty JSON object.
        """
        response, pattern = self._find_response(prompt)

        self.call_history.append(
            LLMCall(
                prompt=prompt,
                response=response,
                matched_pattern=pattern,
            )
        )

        return response

    def _find_response(self, prompt: str) -> tuple[str, str]:
        """Find the response for a prompt.

        Args:
            prompt: The prompt to match

        Returns:
            Tuple of (response, matched_pattern)
        """
        prompt_lower = prompt.lower()

        # Check each pattern (except default) in order
        for pattern, response in self.responses.items():
            if pattern == "default":
                continue
            if pattern.lower() in prompt_lower:
                return response, pattern

        # Fall back to default
        if "default" in self.responses:
            return self.responses["default"], "default"

        # Ultimate fallback
        return "{}", "none"

    def add_response(self, pattern: str, response: str) -> None:
        """Add or update a response pattern.

        Args:
            pattern: The pattern to match in prompts
            response: The response to return when matched
        """
        self.responses[pattern] = response

    def set_responses(self, responses: dict[str, str]) -> None:
        """Replace all response patterns.

        Args:
            responses: New response mappings
        """
        self.responses = responses
        self.call_history.clear()

    def clear_history(self) -> None:
        """Clear the call history."""
        self.call_history.clear()

    def get_last_call(self) -> LLMCall | None:
        """Get the most recent call, if any."""
        return self.call_history[-1] if self.call_history else None

    def assert_called(self, times: int | None = None) -> None:
        """Assert the mock was called.

        Args:
            times: If provided, assert exactly this many calls

        Raises:
            AssertionError: If assertion fails
        """
        if times is not None:
            assert (
                len(self.call_history) == times
            ), f"Expected {times} calls, got {len(self.call_history)}"
        else:
            assert len(self.call_history) > 0, "Expected at least one call"

    def assert_pattern_matched(self, pattern: str) -> None:
        """Assert a specific pattern was matched.

        Args:
            pattern: The pattern that should have been matched

        Raises:
            AssertionError: If pattern was never matched
        """
        matched = [c.matched_pattern for c in self.call_history]
        assert (
            pattern in matched
        ), f"Pattern '{pattern}' not matched. Matched patterns: {matched}"


@dataclass
class MockInteractorResponse:
    """Structured response for mocking the Interactor AI.

    Provides a convenient way to create mock responses in the format
    expected by the Interactor AI parser.
    """

    type: str = "action_intent"
    action_type: str = "examine"
    target_id: str = "unknown"
    verb: str = "examine"
    confidence: float = 1.0
    reasoning: str = "Test mock response"

    # Optional fields
    instrument_id: str | None = None
    topic_id: str | None = None
    recipient_id: str | None = None

    def to_json(self) -> str:
        """Convert to JSON string for mock responses."""
        data: dict[str, Any] = {
            "type": self.type,
            "action_type": self.action_type,
            "target_id": self.target_id,
            "verb": self.verb,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

        if self.instrument_id:
            data["instrument_id"] = self.instrument_id
        if self.topic_id:
            data["topic_id"] = self.topic_id
        if self.recipient_id:
            data["recipient_id"] = self.recipient_id

        return json.dumps(data)


@dataclass
class MockNarratorResponse:
    """Structured response for mocking the Narrator AI.

    Provides a convenient way to create mock narrative responses.
    """

    narrative: str = "A test narrative."

    def to_json(self) -> str:
        """Convert to JSON string for mock responses."""
        return json.dumps({"narrative": self.narrative})


# Convenience factory functions


def create_mock_for_movement() -> MockLLMClient:
    """Create a mock configured for movement testing."""
    return MockLLMClient(
        {
            "north": MockInteractorResponse(
                action_type="move",
                target_id="north",
                verb="go",
            ).to_json(),
            "south": MockInteractorResponse(
                action_type="move",
                target_id="south",
                verb="go",
            ).to_json(),
            "default": MockInteractorResponse().to_json(),
        }
    )


def create_mock_for_examine() -> MockLLMClient:
    """Create a mock configured for examine testing."""
    return MockLLMClient(
        {
            "examine": MockInteractorResponse(
                action_type="examine",
                target_id="item",
                verb="examine",
            ).to_json(),
            "look at": MockInteractorResponse(
                action_type="examine",
                target_id="item",
                verb="look at",
            ).to_json(),
            "default": MockInteractorResponse().to_json(),
        }
    )
