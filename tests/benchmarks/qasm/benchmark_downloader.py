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
Benchmark file downloader utility.

This module handles downloading benchmark QASM files from the Qiskit repository
and caching them locally to avoid storing large files in version control.
"""

import json
import ssl
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional


class BenchmarkDownloader:
    """Handles downloading and caching of benchmark files."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the downloader."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent
        self.cache_dir.mkdir(exist_ok=True)

        # Load metadata
        with open(self.cache_dir / "benchmark_metadata.json", "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

    def get_file_path(self, filename: str) -> Path:
        """Get the path for a benchmark file, fetching from remote repository if needed."""
        # Check local_files first
        if filename in self.metadata["local_files"]:
            file_path = self.cache_dir / filename
            if not file_path.exists():
                raise RuntimeError(f"Local file {filename} not found in {self.cache_dir}")
            return file_path

        # Check benchmark_files
        if filename in self.metadata["benchmark_files"]:
            file_info = self.metadata["benchmark_files"][filename]
            # Fetch remote files
            return self._fetch_remote_file(filename, file_info)

        raise KeyError(f"Unknown benchmark file: {filename}")

    def _fetch_remote_file(self, filename: str, file_info: Dict) -> Path:
        """Fetch a remote benchmark file and return a temporary file path."""
        url = file_info["url"]

        try:
            # Create SSL context that doesn't verify certificates (for development/CI)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create opener with SSL context and fetch content
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
            urllib.request.install_opener(opener)

            with urllib.request.urlopen(url) as response:
                content = response.read()

            # Create temporary file and write content
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".qasm", prefix=f"benchmark_{filename}_", delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_file_path = Path(temp_file.name)

            return temp_file_path

        except Exception as e:
            # pylint: disable-next=raise-missing-from
            raise RuntimeError(f"Failed to fetch {filename} from {url}: {e}")


def get_benchmark_file(filename: str) -> str:
    """Get the path to a benchmark file, downloading if necessary."""
    downloader = BenchmarkDownloader()
    return str(downloader.get_file_path(filename))
