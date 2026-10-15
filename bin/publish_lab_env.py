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
Script that drives the publish-lab-env workflow.

Each subcommand is one workflow step. Settings come from environment variables:

    QBRAID_API_KEY, QBRAID_API_URL   read by qbraid-core
    VERSION                          pyqasm version to publish, x.y.z
    GROUP                            environment group slug (needed for the publish step)
    LOGO                             logo provider name (default: qbraid)
    STOP_AFTER                       upload | approve | publish (default: publish)
    ALLOW_EXISTING                   "true" to allow a duplicate environment name
    SET_LATEST                       "false" to add to the group without changing its latest
    SLUG                             resume an uploaded environment instead of building one

Values for later steps are written to $GITHUB_OUTPUT when it is set.

Usage:
    python bin/publish_lab_env.py preflight
    python bin/publish_lab_env.py create
    python bin/publish_lab_env.py upload --env-id ENV_ID
    python bin/publish_lab_env.py publish --slug SLUG
    python bin/publish_lab_env.py summary [--env-id ENV_ID] [--slug SLUG] [--status STATUS]

"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

# Order matters: STOP_AFTER=X runs every step up to and including X.
PUBLISH_STEPS = ("upload", "approve", "publish")
PAGE_SIZE = 100
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SLUG_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
ENV_NAME_PATTERN = re.compile(r"pyqasm ([0-9]+\.[0-9]+\.[0-9]+)")
# Besides pyqasm with every extra it declares on PyPI. Only pyqasm is pinned.
# The venv starts empty, and Lab needs ipykernel in it to start the kernel.
EXTRA_PACKAGES = ["ipykernel", "matplotlib"]


class Settings:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Workflow settings read from environment variables."""

    def __init__(self) -> None:
        self.version = os.getenv("VERSION", "")
        self.group = os.getenv("GROUP") or None
        self.logo = os.getenv("LOGO") or "qbraid"
        self.stop_after = os.getenv("STOP_AFTER") or "publish"
        self.allow_existing = os.getenv("ALLOW_EXISTING", "").lower() == "true"
        self.set_latest = os.getenv("SET_LATEST", "true").lower() != "false"
        self.slug = os.getenv("SLUG") or None
        self.name = f"pyqasm {self.version}"
        self.kernel_name = f"Python 3 [pyqasm {self.version}]"


def set_output(key: str, value: str) -> None:
    """Print a value and write it to $GITHUB_OUTPUT when running in Actions."""
    print(f"{key}={value}")
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as file:
            file.write(f"{key}={value}\n")


def env_client():
    """Return a qBraid environment client authenticated from the environment."""
    # pylint: disable-next=import-outside-toplevel
    from qbraid_core.services.environments import EnvironmentManagerClient

    return EnvironmentManagerClient()


def version_tuple(version: str) -> tuple[int, ...]:
    """Turn an x.y.z version string into a comparable tuple."""
    return tuple(int(part) for part in version.split("."))


def visible_env_names(client: Any) -> set[str]:
    """Return the names of every environment the key can see."""
    names: set[str] = set()
    page = 1
    while True:
        result = client.get_available_environments(page=page, limit=PAGE_SIZE)
        envs = result.get("environments", [])
        names.update(env.get("name", "") for env in envs)
        pagination = result.get("pagination") or {}
        total_pages = pagination.get("totalPages") or pagination.get("pages")
        if not envs or len(envs) < PAGE_SIZE or (total_pages and page >= total_pages):
            return names
        page += 1


def group_latest(group: dict[str, Any]) -> Optional[str]:
    """Return the slug of a group's latest environment."""
    latest = group.get("latestEnv")
    if isinstance(latest, dict):
        return latest.get("slug")
    return latest


def get_group(client: Any, slug: str) -> dict[str, Any]:
    """Fetch a group, exiting with a clear message if the key cannot read it."""
    try:
        return client.get_environment_group_by_slug(slug)
    except Exception as err:  # pylint: disable=broad-exception-caught
        sys.exit(f"Cannot read environment group '{slug}': {err}")


def pypi_metadata(version: str) -> dict[str, Any]:
    """Return PyPI's metadata for a pyqasm release, exiting if it is not there."""
    url = f"https://pypi.org/pypi/pyqasm/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310 - fixed https URL
            return json.load(response)
    except urllib.error.HTTPError as err:
        sys.exit(f"pyqasm {version} is not on PyPI (HTTP {err.code}).")
    except urllib.error.URLError as err:
        sys.exit(f"Could not reach PyPI to check pyqasm {version}: {err.reason}")


def pyqasm_requirement(version: str) -> str:
    """Return the pinned pyqasm requirement with every extra the release declares."""
    extras = sorted(pypi_metadata(version)["info"].get("provides_extra") or [])
    return f"pyqasm[{','.join(extras)}]=={version}" if extras else f"pyqasm=={version}"


def check_settings(settings: Settings) -> None:
    """Check the settings that need no qBraid call."""
    if not os.getenv("QBRAID_API_KEY") or not os.getenv("QBRAID_API_URL"):
        sys.exit("Set secret QBRAID_API_KEY and variable QBRAID_API_URL on the GitHub Environment.")
    if not VERSION_PATTERN.fullmatch(settings.version):
        sys.exit(f"version must look like x.y.z, got '{settings.version}'.")
    if settings.slug and not SLUG_PATTERN.fullmatch(settings.slug):
        sys.exit(f"slug may hold only letters, digits, '_' and '-', got '{settings.slug}'.")
    if settings.stop_after not in PUBLISH_STEPS:
        sys.exit(f"STOP_AFTER must be one of {', '.join(PUBLISH_STEPS)}.")
    if settings.stop_after == "publish" and not settings.group:
        sys.exit("The publish step needs a group. Set QBRAID_ENV_GROUP, or stop after approve.")
    print(f"Will install {pyqasm_requirement(settings.version)} and {', '.join(EXTRA_PACKAGES)}.")


def preflight(settings: Settings) -> None:
    """Check the inputs, the key, the logo, the group, and that the name is free."""
    check_settings(settings)

    # pylint: disable-next=import-outside-toplevel
    from qbraid_core import QbraidSessionV1

    session = QbraidSessionV1()
    session.get_user_auth_metadata()
    print(f"Authenticated against {session.base_url}")

    client = env_client()
    if settings.group:
        data = get_group(client, settings.group)
        print(f"Group '{settings.group}' found; current latest: {group_latest(data) or 'none'}")

    if settings.slug:
        # Resuming: the environment already exists, so only check that it is readable.
        env = client.get_environment_by_slug(settings.slug)
        if env.get("name") != settings.name:
            sys.exit(f"Slug '{settings.slug}' is '{env.get('name')}', not '{settings.name}'.")
        print(f"Resuming '{settings.slug}' ({settings.name}).")
        return

    # `qbraid envs create` only warns on an unknown logo, and the logo cannot change later.
    try:
        client.resolve_logos(settings.logo)
    except Exception as err:  # pylint: disable=broad-exception-caught
        sys.exit(f"Logo '{settings.logo}' did not resolve: {err}")

    if settings.name in visible_env_names(client):
        if not settings.allow_existing:
            sys.exit(
                f"An environment named '{settings.name}' already exists on this server. "
                "Resume it with its slug, or re-run with allow_existing to publish another copy."
            )
        print(f"Warning: an environment named '{settings.name}' already exists; continuing.")
    print("Preflight passed.")


def create(settings: Settings) -> None:
    """Create the environment with the qBraid CLI, then install pyqasm into it."""
    # pylint: disable=import-outside-toplevel
    from qbraid_core.services.environments import pip_install
    from qbraid_core.services.environments.registry import EnvironmentRegistryManager

    # pylint: enable=import-outside-toplevel

    subprocess.run(
        [
            "qbraid",
            "envs",
            "create",
            "--name",
            settings.name,
            "--description",
            f"pyqasm {settings.version}: parse, validate and unroll OpenQASM 2 and 3 programs.",
            "--kernel-name",
            settings.kernel_name,
            "--logo",
            settings.logo,
            "--tags",
            f"pyqasm,openqasm,qasm3,py{sys.version_info.major}{sys.version_info.minor}",
            "--yes",
        ],
        check=True,
    )

    found = EnvironmentRegistryManager().find_by_name(settings.name)
    if found is None:
        sys.exit(f"No local environment named '{settings.name}' after create.")
    env_id, entry = found

    packages = [pyqasm_requirement(settings.version), *EXTRA_PACKAGES]
    print(f"Installing {', '.join(packages)} into {env_id}")
    result = pip_install(env_id, packages)
    if not result.get("success"):
        print(result.get("output", ""))
        sys.exit("pip failed inside the environment.")

    set_output("env_id", env_id)
    set_output("python", str(entry.path / "pyenv" / "bin" / "python"))


def upload(env_id: str) -> None:
    """Upload a local environment by env_id and output its new cloud slug."""
    result = asyncio.run(env_client().upload_environment(env_id))
    slug = result.get("slug")
    if not slug:
        sys.exit(f"Upload returned no slug: {result}")
    set_output("slug", slug)


def review_status(client: Any, slug: str) -> str:
    """Return an environment's review status in upper case."""
    return str(client.get_publish_status(slug)).upper()


def should_set_latest(client: Any, settings: Settings, current: Optional[str], slug: str) -> bool:
    """Decide whether this environment becomes the group's latest."""
    if not settings.set_latest:
        print("set_latest is off; leaving the group's latest unchanged.")
        return False
    if current in (None, slug):
        return True
    match = ENV_NAME_PATTERN.fullmatch(client.get_environment_by_slug(current).get("name", ""))
    if match and version_tuple(match.group(1)) >= version_tuple(settings.version):
        print(f"Group latest '{current}' is pyqasm {match.group(1)}, not older; leaving it.")
        return False
    return True


def publish(settings: Settings, slug: str) -> None:
    """Approve, then add to the group as its latest. Skips steps already done."""
    steps = PUBLISH_STEPS[: PUBLISH_STEPS.index(settings.stop_after) + 1]
    group = settings.group
    if "publish" in steps and not group:
        sys.exit("The publish step needs a group. Set QBRAID_ENV_GROUP, or stop after approve.")
    client = env_client()

    if "approve" in steps:
        status = review_status(client, slug)
        if status == "APPROVED":
            print(f"'{slug}' is already approved.")
        else:
            # Approve works from any status. Skipping the publish request avoids the
            # per-plan publish quota and the email that a request sends every admin.
            # Approving is what publishes to the catalog: it makes the environment public.
            client.approve_publish(slug)
            status = review_status(client, slug)
            if status != "APPROVED":
                sys.exit(f"Expected review status APPROVED for '{slug}', got {status}.")
            print(f"Approved '{slug}'.")

    if "publish" in steps:
        data = get_group(client, group)
        current = group_latest(data)
        set_latest = should_set_latest(client, settings, current, slug)
        add_envs = [] if slug in (data.get("environments") or []) else [slug]
        if add_envs or (set_latest and current != slug):
            # One call: addEnvs is applied before latestEnv, which must be a member.
            client.update_environment_group(
                group, add_envs=add_envs or None, latest_env=slug if set_latest else None
            )
        data = get_group(client, group)
        if slug not in (data.get("environments") or []):
            sys.exit(f"'{slug}' is not in group '{group}' after the update.")
        if set_latest and group_latest(data) != slug:
            sys.exit(f"Group '{group}' latest is '{group_latest(data)}', expected '{slug}'.")
        print(f"'{slug}' is in group '{group}'; latest: {group_latest(data)}.")

    set_output("published_through", settings.stop_after)


def summary(settings: Settings, env_id: str, slug: str, status: str) -> None:
    """Write the run's results to the job summary."""
    rows = [
        ("Name", settings.name),
        ("Kernel display name", settings.kernel_name),
        ("Local env_id", env_id or "not created"),
        ("Slug", slug or "not uploaded"),
        ("Group", settings.group or "none"),
        ("Requested last step", settings.stop_after),
        ("Job status", status),
    ]
    lines = [f"### pyqasm {settings.version} Lab environment", "", "| | |", "|---|---|"]
    lines += [f"| {key} | {value} |" for key, value in rows]
    if status != "success" and slug:
        lines += ["", f"Resume with `slug={slug}` once the cause is fixed."]
    text = "\n".join(lines) + "\n"
    print(text)
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as file:
            file.write(text)


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and run one subcommand."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("create")
    sub.add_parser("upload").add_argument("--env-id", required=True)
    sub.add_parser("publish").add_argument("--slug", required=True)
    summ = sub.add_parser("summary")
    summ.add_argument("--env-id", default="")
    summ.add_argument("--slug", default="")
    summ.add_argument("--status", default="")

    args = parser.parse_args(argv)
    settings = Settings()
    if args.command == "preflight":
        preflight(settings)
    elif args.command == "create":
        create(settings)
    elif args.command == "upload":
        upload(args.env_id)
    elif args.command == "publish":
        publish(settings, args.slug)
    else:
        summary(settings, args.env_id, args.slug, args.status)


if __name__ == "__main__":
    main()
