import pytest

def test_openpulse_import():
    """Tests that openpulse can be imported."""
    try:
        import openpulse
    except ImportError:
        pytest.fail("Failed to import openpulse. Ensure that pyqasm[pulse] is installed.")