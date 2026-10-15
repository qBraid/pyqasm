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
Script that drives the qBraid side of the publish-lab-env workflow.

Each subcommand is one workflow step. The qBraid API key and URL come from the
QBRAID_API_KEY and QBRAID_API_URL environment variables, which qbraid-core reads.
Values for later steps are written to $GITHUB_OUTPUT when it is set.

Usage:
    python bin/publish_lab_env.py preflight --name NAME [--group SLUG] [--allow-existing]
    python bin/publish_lab_env.py locate --name NAME
    python bin/publish_lab_env.py upload --env-id ENV_ID
    python bin/publish_lab_env.py publish --slug SLUG [--group SLUG] [--stop-after STEP]

"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Optional

# Order matters: --stop-after X runs every step up to and including X.
PUBLISH_STEPS = ("upload", "request", "approve", "publish")
PAGE_SIZE = 100


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


def preflight(name: str, group: Optional[str], allow_existing: bool) -> None:
    """Check the key, the target group, and that the name is free."""
    # pylint: disable-next=import-outside-toplevel
    from qbraid_core import QbraidSessionV1

    session = QbraidSessionV1()
    session.get_user_auth_metadata()
    print(f"Authenticated against {session.base_url}")

    client = env_client()
    if group:
        data = client.get_environment_group_by_slug(group)
        if not data:
            sys.exit(f"Environment group '{group}' not found.")
        print(f"Group '{group}' found; current latest: {group_latest(data) or 'none'}")

    if name in visible_env_names(client):
        if not allow_existing:
            sys.exit(
                f"An environment named '{name}' already exists on this server. "
                "Re-run with allow_existing to publish another copy."
            )
        print(f"Warning: an environment named '{name}' already exists; continuing.")
    print("Preflight passed.")


def locate(name: str) -> None:
    """Find the local environment built by `qbraid envs create`."""
    # pylint: disable-next=import-outside-toplevel
    from qbraid_core.services.environments.registry import EnvironmentRegistryManager

    found = EnvironmentRegistryManager().find_by_name(name)
    if found is None:
        sys.exit(f"No local environment named '{name}'.")
    env_id, entry = found
    set_output("env_id", env_id)
    set_output("python", str(entry.path / "pyenv" / "bin" / "python"))


def upload(env_id: str) -> None:
    """Upload a local environment by env_id. Returns the new cloud slug."""
    result = asyncio.run(env_client().upload_environment(env_id))
    slug = result.get("slug")
    if not slug:
        sys.exit(f"Upload returned no slug: {result}")
    set_output("slug", slug)


def check_status(client: Any, slug: str, expected: str) -> None:
    """Exit unless the environment's review status matches."""
    status = str(client.get_publish_status(slug)).upper()
    if status != expected:
        sys.exit(f"Expected review status {expected} for '{slug}', got {status}.")
    print(f"Review status: {status}")


def publish(slug: str, group: Optional[str], stop_after: str) -> None:
    """Request, review, approve, then add to the group as its latest."""
    steps = PUBLISH_STEPS[: PUBLISH_STEPS.index(stop_after) + 1]
    if "publish" in steps and not group:
        sys.exit("The publish step needs a group. Set QBRAID_ENV_GROUP, or stop after approve.")
    client = env_client()

    if "request" in steps:
        client.request_publish(slug)
        check_status(client, slug, "REQUESTED")

    if "approve" in steps:
        client.set_publish_pending(slug)
        check_status(client, slug, "PENDING")
        # Approving is what publishes to the catalog: it makes the environment public.
        client.approve_publish(slug)
        check_status(client, slug, "APPROVED")

    if "publish" in steps:
        # One call: addEnvs is applied before latestEnv, which must be a member.
        client.update_environment_group(group, add_envs=[slug], latest_env=slug)
        latest = group_latest(client.get_environment_group_by_slug(group))
        if latest != slug:
            sys.exit(f"Group '{group}' latest is '{latest}', expected '{slug}'.")
        print(f"'{slug}' is now the latest environment in group '{group}'.")

    set_output("published_through", stop_after)


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and run one subcommand."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight")
    pre.add_argument("--name", required=True)
    pre.add_argument("--group")
    pre.add_argument("--allow-existing", action="store_true")

    loc = sub.add_parser("locate")
    loc.add_argument("--name", required=True)

    upl = sub.add_parser("upload")
    upl.add_argument("--env-id", required=True)

    pub = sub.add_parser("publish")
    pub.add_argument("--slug", required=True)
    pub.add_argument("--group")
    pub.add_argument("--stop-after", choices=PUBLISH_STEPS, default="publish")

    args = parser.parse_args(argv)
    if args.command == "preflight":
        preflight(args.name, args.group or None, args.allow_existing)
    elif args.command == "locate":
        locate(args.name)
    elif args.command == "upload":
        upload(args.env_id)
    else:
        publish(args.slug, args.group or None, args.stop_after)


if __name__ == "__main__":
    main()
