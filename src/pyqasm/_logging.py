# # Copyright 2025 qBraid
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

"""
Module defining logging configuration for PyQASM.
This module sets up a logger for the PyQASM library, allowing for

"""
import logging

# Define a custom logger for the module
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))

logger = logging.getLogger("pyqasm")
logger.addHandler(handler)
logger.setLevel(logging.ERROR)

# disable propagation to avoid double logging
# messages to the root logger in case the root logging
# level changes
logger.propagate = False
