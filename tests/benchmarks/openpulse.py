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
This module is used to test the openpulse of pyqasm.
"""

from pyqasm import load

from .qasm.benchmark_downloader import get_benchmark_file


class Openpulse:
    """Test the pyqasm openpulse functionality."""

    def setup(self):
        # Get benchmark file, downloading if necessary
        # pylint: disable-next=attribute-defined-outside-init
        self.qasm_file = get_benchmark_file("neutral_atom_gate.qasm")

    def time_openpulse(self):
        _ = load(self.qasm_file).unroll()
