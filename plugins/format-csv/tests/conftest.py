from pathlib import Path
import pytest


@pytest.fixture
def people_csv_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "people.csv").read_bytes()
