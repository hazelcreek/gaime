"""Unit tests for engine selection API.

Tests cover:
- EngineVersion enum values
- /engines endpoint response structure
- NewGameRequest engine parameter
- Default engine is CLASSIC
"""

import pytest
from fastapi.testclient import TestClient

from app.api.engine import EngineVersion, ENGINE_INFO, DEFAULT_ENGINE
from app.api.game import NewGameRequest, NewGameResponse
from app.main import app


class TestEngineVersion:
    """Tests for EngineVersion enum."""

    def test_classic_engine(self) -> None:
        """CLASSIC is a valid engine version."""
        assert EngineVersion.CLASSIC == "classic"
        assert EngineVersion.CLASSIC.value == "classic"

    def test_two_phase_engine(self) -> None:
        """TWO_PHASE is a valid engine version."""
        assert EngineVersion.TWO_PHASE == "two_phase"
        assert EngineVersion.TWO_PHASE.value == "two_phase"

    def test_engine_is_string_enum(self) -> None:
        """EngineVersion values can be used as strings."""
        # str(Enum) is compatible with JSON serialization
        assert EngineVersion.CLASSIC.value == "classic"
        assert EngineVersion.TWO_PHASE.value == "two_phase"
        # Can compare directly with strings
        assert EngineVersion.CLASSIC == "classic"
        assert EngineVersion.TWO_PHASE == "two_phase"


class TestEngineInfo:
    """Tests for ENGINE_INFO constant."""

    def test_engine_info_structure(self) -> None:
        """ENGINE_INFO has expected structure."""
        assert len(ENGINE_INFO) == 2

        for engine in ENGINE_INFO:
            assert "id" in engine
            assert "name" in engine
            assert "description" in engine

    def test_engine_info_ids(self) -> None:
        """ENGINE_INFO contains both engine IDs."""
        ids = [e["id"] for e in ENGINE_INFO]
        assert "classic" in ids
        assert "two_phase" in ids


class TestDefaultEngine:
    """Tests for DEFAULT_ENGINE constant."""

    def test_default_is_classic(self) -> None:
        """Default engine is CLASSIC."""
        assert DEFAULT_ENGINE == EngineVersion.CLASSIC


class TestNewGameRequest:
    """Tests for NewGameRequest model with engine parameter."""

    def test_default_engine(self) -> None:
        """NewGameRequest defaults to CLASSIC engine."""
        request = NewGameRequest(world_id="test-world")
        assert request.engine == EngineVersion.CLASSIC

    def test_explicit_classic_engine(self) -> None:
        """NewGameRequest accepts explicit CLASSIC engine."""
        request = NewGameRequest(world_id="test-world", engine=EngineVersion.CLASSIC)
        assert request.engine == EngineVersion.CLASSIC

    def test_two_phase_engine(self) -> None:
        """NewGameRequest accepts TWO_PHASE engine."""
        request = NewGameRequest(world_id="test-world", engine=EngineVersion.TWO_PHASE)
        assert request.engine == EngineVersion.TWO_PHASE

    def test_engine_from_string(self) -> None:
        """NewGameRequest accepts engine as string value."""
        request = NewGameRequest(world_id="test-world", engine="two_phase")
        assert request.engine == EngineVersion.TWO_PHASE


class TestEnginesEndpoint:
    """Tests for GET /api/game/engines endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_engines_endpoint_returns_200(self, client: TestClient) -> None:
        """GET /api/game/engines returns 200."""
        response = client.get("/api/game/engines")
        assert response.status_code == 200

    def test_engines_endpoint_structure(self, client: TestClient) -> None:
        """GET /api/game/engines returns expected structure."""
        response = client.get("/api/game/engines")
        data = response.json()

        assert "engines" in data
        assert "default" in data
        assert isinstance(data["engines"], list)
        assert isinstance(data["default"], str)

    def test_engines_endpoint_contains_engines(self, client: TestClient) -> None:
        """GET /api/game/engines returns both engines."""
        response = client.get("/api/game/engines")
        data = response.json()

        engine_ids = [e["id"] for e in data["engines"]]
        assert "classic" in engine_ids
        assert "two_phase" in engine_ids

    def test_engines_endpoint_default_is_classic(self, client: TestClient) -> None:
        """GET /api/game/engines default is classic."""
        response = client.get("/api/game/engines")
        data = response.json()

        assert data["default"] == "classic"

    def test_engine_info_has_required_fields(self, client: TestClient) -> None:
        """Each engine in response has id, name, description."""
        response = client.get("/api/game/engines")
        data = response.json()

        for engine in data["engines"]:
            assert "id" in engine
            assert "name" in engine
            assert "description" in engine

