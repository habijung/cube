"""Install or locally diagnose Cube-managed Pi packages without loading extensions."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


NPM_SOURCE = re.compile(r"npm:((?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*)\Z")


def read_manifest(path):
    sources = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        source = line.strip()
        if not source or source.startswith("#"):
            continue
        if not NPM_SOURCE.fullmatch(source) or source in sources:
            raise ValueError(f"Invalid or duplicate package at {path}:{number}")
        sources.append(source)
    if not sources:
        raise ValueError(f"Empty package list: {path}")
    return sources


def read_packages(agent_dir):
    path = agent_dir / "settings.json"
    if not path.exists():
        return []
    settings = json.loads(path.read_text())
    if not isinstance(settings, dict):
        raise ValueError(f"Expected a settings object: {path}")
    packages = settings.get("packages", [])
    if not isinstance(packages, list):
        raise ValueError(f"Expected a packages array: {path}")
    sources = []
    for entry in packages:
        source = entry.get("source") if isinstance(entry, dict) else entry
        if not isinstance(source, str) or not source:
            raise ValueError(f"Invalid package declaration: {path}")
        sources.append(source)
    return sources


def matching_sources(source, configured):
    # A trailing @version is distinct from the @scope at the start of a name.
    return [entry for entry in configured
            if entry == source or entry.startswith(source + "@")]


def installed_version(agent_dir, source):
    name = source[4:]
    path = agent_dir / "npm" / "node_modules" / name / "package.json"
    try:
        package = json.loads(path.read_text())
        version = package.get("version")
        if package.get("name") == name and isinstance(version, str) and version:
            return version
    except (OSError, ValueError, AttributeError):
        pass
    return None


def manage_packages(manifest, check, preflight=False):
    sources = read_manifest(manifest)
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR") or "~/.pi/agent").expanduser().resolve()
    configured = read_packages(agent_dir)
    pi = shutil.which("pi")
    if not pi:
        print("❌ [Pi] CLI not found; install Pi separately. Cube does not install Pi itself.")
        return 1
    pi = str(Path(pi).resolve())
    if not check and os.environ.get("PI_OFFLINE", "").lower() in ("1", "true"):
        print("❌ [Pi] PI_OFFLINE is enabled; latest-package installation requires network access.")
        return 1
    if preflight:
        return 0
    errors = 0
    for source in sources:
        matches = matching_sources(source, configured)
        if len(matches) > 1 or (matches and matches[0] != source):
            print(f"❌ [Pi] {source}: version constraint or duplicate declaration; preserved, skipped.")
            errors += 1
            continue
        version = installed_version(agent_dir, source)
        if check:
            if not matches:
                print(f"❌ [Pi] {source}: not registered in personal settings.")
                errors += 1
            elif not version:
                print(f"❌ [Pi] {source}: managed installation missing or invalid; rerun the Pi installer.")
                errors += 1
            else:
                print(f"✅ [Pi] {source}: installed {version} (local files only).")
            continue
        command = "update" if matches and version else "install"
        print(f"🔧 [Pi] {command}: {source}", flush=True)
        # Pi update <source> also visits project settings. A neutral working
        # directory keeps Cube's operations scoped to the personal environment.
        # Resolve an overridden agent directory before changing cwd as well.
        env = dict(os.environ, PI_CODING_AGENT_DIR=str(agent_dir))
        try:
            with tempfile.TemporaryDirectory(prefix="cube-pi-") as directory:
                result = subprocess.run([pi, command, source], cwd=directory, env=env)
            if result.returncode:
                print(f"❌ [Pi] {source}: {command} failed (exit {result.returncode}).")
                errors += 1
                continue
            configured = read_packages(agent_dir)
            version = installed_version(agent_dir, source)
            if matching_sources(source, configured) != [source] or not version:
                print(f"❌ [Pi] {source}: command succeeded but installation verification failed.")
                errors += 1
                continue
            print(f"✅ [Pi] {source}: installed {version}.")
        except (OSError, ValueError) as error:
            print(f"❌ [Pi] {source}: {error}")
            errors += 1
    if check:
        print("ℹ️  [Pi] Local package state only; latest versions and extension loading are not checked.")
    return int(errors > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        return manage_packages(args.manifest, args.check, args.preflight)
    except (OSError, ValueError) as error:
        print(f"❌ [Pi] Package preflight failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
