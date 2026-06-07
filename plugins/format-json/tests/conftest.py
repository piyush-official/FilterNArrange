from pathlib import Path
import pytest

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def people_json() -> bytes: return (FIX / "people.json").read_bytes()

@pytest.fixture
def nested_json() -> bytes: return (FIX / "nested.json").read_bytes()
