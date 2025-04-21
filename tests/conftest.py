# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module for configuring pytest fixtures and logging settings for tests.
"""

import pytest

from src.pyqasm._logging import logger


# Automatically applied to all tests
@pytest.fixture(autouse=True)
def enable_logger_propagation():
    """Temporarily enable logger propagation for tests. This is because
    caplog only captures logs from the root logger"""
    original_propagate = logger.propagate
    logger.propagate = True  # Enable propagation for tests
    yield
    logger.propagate = original_propagate  # Restore original behavior
