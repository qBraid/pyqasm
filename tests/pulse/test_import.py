import pytest

def test_openpulse_import():
    """Tests that openpulse can be imported if pyqasm[pulse] is installed."""
    pytest.importorskip("openpulse")