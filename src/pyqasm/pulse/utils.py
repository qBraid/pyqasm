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
Module with utility functions for Pulse visitor

"""
import re

class PulseUtils:
    """Class with utility functions for Pulse visitor"""

    @staticmethod
    def format_calibration_body(result):
        """Format the calibration body"""
        from openpulse.printer import dumps as pulse_dumps # pylint: disable=import-outside-toplevel

        body_str = "".join([pulse_dumps(stmt) for stmt in result])
        body_str = re.sub(r"\n(?![\s])", "\n ", body_str)
        body_str = re.sub(r"\n +$", "\n", body_str)
        lines = body_str.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.strip() != "":
                if not line.startswith(" "):
                    lines[i] = " " + line
                break
        body_str = "".join(lines)
        return body_str
