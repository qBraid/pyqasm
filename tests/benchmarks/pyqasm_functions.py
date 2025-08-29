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

# pylint: disable=no-member,invalid-name,missing-docstring,no-name-in-module
# pylint: disable=attribute-defined-outside-init,unsubscriptable-object

"""
This module is used to test the basic functions of pyqasm.
"""

import os
from pathlib import Path

from pyqasm import dump, dumps, load, printer

from .qasm.benchmark_downloader import get_benchmark_file


class PyqasmFunctions:
    def setup(self):
        # Get benchmark files, downloading if necessary
        self.qasm_file = get_benchmark_file("qft_N100.qasm")

        # Create output file path in the same directory as input file
        input_path = Path(self.qasm_file)
        self.output_file = str(input_path.parent / "qft_N100_unrolled.qasm")

        self.pyqasm_obj = load(self.qasm_file)
        self.mid_qasm_file = get_benchmark_file("pea_3_pi_8.qasm")
        self.mid_pyqasm_obj = load(self.mid_qasm_file)

    def teardown(self):
        # Clean up the output file if it was created
        if hasattr(self, "output_file") and os.path.exists(self.output_file):
            try:
                os.remove(self.output_file)
            except OSError:
                pass

    def time_load(self):
        _ = load(self.qasm_file)

    def time_dumps(self):
        _ = dumps(self.pyqasm_obj)

    def time_dump(self):
        dump(self.pyqasm_obj, self.output_file)

    def time_draw(self):
        _ = printer.mpl_draw(self.mid_pyqasm_obj, idle_wires=True, external_draw=False)
