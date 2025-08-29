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

# pylint: disable-all

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
        if filename not in self.metadata["benchmark_files"]:
            raise KeyError(f"Unknown benchmark file: {filename}")

        file_info = self.metadata["benchmark_files"][filename]

        # Check if this is a local-only file
        if file_info.get("local_only", False):
            file_path = self.cache_dir / filename
            if not file_path.exists():
                raise RuntimeError(
                    f"Local file {filename} not found. Please ensure it exists in the repository."
                )
            return file_path

        # For remote files, fetch and return a temporary file
        return self._fetch_remote_file(filename, file_info)

    def _fetch_remote_file(self, filename: str, file_info: Dict) -> Path:
        """Fetch a remote benchmark file and return a temporary file path."""
        url = file_info["url"]

        try:
            # Create SSL context that doesn't verify certificates (for development)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create opener with SSL context and fetch content
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
            urllib.request.install_opener(opener)

            with urllib.request.urlopen(url) as response:
                content = response.read()

            # Create temporary file and write content
            temp_file = tempfile.NamedTemporaryFile(
                mode="wb", suffix=".qasm", prefix=f"benchmark_{filename}_", delete=False
            )
            temp_file.write(content)
            temp_file.close()

            return Path(temp_file.name)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch {filename} from {url}: {e}")


# Global instance for convenience
_downloader = None


def get_benchmark_file(filename: str) -> str:
    """Get the path to a benchmark file, downloading if necessary."""
    global _downloader
    if _downloader is None:
        _downloader = BenchmarkDownloader()
    return str(_downloader.get_file_path(filename))
