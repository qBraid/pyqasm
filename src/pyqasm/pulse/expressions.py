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
Module mapping supported OpenPulse expressions to lower level gate operations.
This module is used to map the OpenPulse expressions to the lower level gate operations.
It is used to validate the OpenPulse expressions and to generate the OpenPulse code.

"""

OPENPULSE_FRAME_FUNCTION_MAP = [
    "set_phase",
    "shift_phase",
    "set_frequency",
    "shift_frequency",
]

OPENPULSE_WAVEFORM_FUNCTION_MAP = [
    "gaussian",
    "sech",
    "gaussian_square",
    "drag",
    "constant",
    "sine",
    "mix",
    "sum",
    "phase_shift",
    "scale",
    "capture_v3",
]

OPENPULSE_CAPTURE_FUNCTION_MAP = [
    "capture_v1",
    "capture_v2",
    "capture_v3",
    "capture_v4",
]
