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

# pylint: disable=attribute-defined-outside-init

"""
This module is used to test the pyqasm functions.
"""

import os
from pathlib import Path

from pyqasm import dump, dumps, load, printer

from .qasm.benchmark_downloader import get_benchmark_file


class PyqasmFunctions:
    """Test the pyqasm functions."""

    # Define parameters for asv
    params = [["small (224 lines)", "mid (2335 lines)", "large (17460 lines)"]]
    param_names = ["qasm_file"]
    timeout = 600

    def setup(self, file_size):
        # Extract the original file size name from the parameter value
        if "(224 lines)" in file_size:
            file_size_key = "small"
        elif "(2335 lines)" in file_size:
            file_size_key = "mid"
        elif "(17460 lines)" in file_size:
            file_size_key = "large"
        else:
            file_size_key = file_size

        # Define files for each size category
        self.files = {
            "small": "vqe_uccsd_n4.qasm",  # 224 lines
            "mid": "dnn_n16.qasm",  # 2335 lines
            "large": "qv_N029_12345.qasm",  # 17460 lines
        }

        # Get benchmark file for the specified size
        self.qasm_file = get_benchmark_file(self.files[file_size_key])
        self.pyqasm_obj = load(self.qasm_file)

        # Create output file path for dump operations
        input_path = Path(self.qasm_file)
        self.output_file = str(input_path.parent / f"{file_size_key}_unrolled.qasm")

    def teardown(self, _):
        # Clean up the output file if it was created
        if hasattr(self, "output_file") and os.path.exists(self.output_file):
            try:
                os.remove(self.output_file)
            except OSError:
                pass

    def time_load(self, _):
        """Load QASM file of specified size."""
        _ = load(self.qasm_file)

    def time_dumps(self, _):
        """Serialize QASM object of specified size to string."""
        _ = dumps(self.pyqasm_obj)

    def time_dump(self, _):
        """Dump QASM object of specified size to file."""
        dump(self.pyqasm_obj, self.output_file)

    def time_draw(self, _):
        """Draw QASM object of specified size."""
        _ = printer.mpl_draw(self.pyqasm_obj, idle_wires=True, external_draw=False)
