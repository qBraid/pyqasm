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
This module is used to test the validation of pyqasm.
"""

from pyqasm import load

from .qasm.benchmark_downloader import get_benchmark_file


class Validate:
    """Test the validation of pyqasm."""

    # Define parameters for asv
    params = [["small (224 lines)", "mid (2335 lines)", "large (17460 lines)"]]
    param_names = ["qasm_file"]
    timeout = 300

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

    def time_validate(self, _):
        """Validate QASM file of specified size."""
        _ = self.pyqasm_obj.validate()
