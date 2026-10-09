#!/usr/bin/env python
"""
Release script for Flaxon.

This script handles the release process including version updates,
changelog generation, and PyPI publishing.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_current_version() -> str:
    """Get the current version from the package."""
    init_file = Path("src/flaxon/version.py")
    content = init_file.read_text()

    match = re.search(r'__version__(?:\s*:\s*str)?\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)

    raise ValueError("Could not find version in version.py")


def update_version(version: str) -> None:
    """Update the authoritative version in version.py."""
    init_file = Path("src/flaxon/version.py")
    content = init_file.read_text()

    content = re.sub(
        r'__version__(?:\s*:\s*str)?\s*=\s*["\']([^"\']+)["\']',
        f'__version__ = "{version}"',
        content,
    )

    init_file.write_text(content)
    print(f"Updated version to {version}")


def update_changelog(version: str) -> None:
    """Update the changelog with the new version."""
    changelog = Path("CHANGELOG.md")
    content = changelog.read_text()

    today = datetime.now().strftime("%Y-%m-%d")

    # Find the unreleased section
    unreleased_pattern = r"^## (?:\[Unreleased\]|Unreleased)\s*\n(.*?)(?=^## |\Z)"
    match = re.search(unreleased_pattern, content, re.DOTALL | re.MULTILINE)

    if match is None:
        raise ValueError("CHANGELOG.md must contain an Unreleased section")
    entry = f"## [Unreleased]\n\n## [{version}] - {today}\n\n{match.group(1)}"
    changelog.write_text(content[:match.start()] + entry + content[match.end():])
    print(f"Updated changelog with version {version}")


def commit_release(version: str) -> None:
    """The release tag must point at the new version and changelog."""
    subprocess.run(["git", "add", "src/flaxon/version.py", "CHANGELOG.md"], check=True)
    subprocess.run(["git", "commit", "-m", f"Release {version}"], check=True)


def create_git_tag(version: str) -> None:
    """Create a git tag for the release."""
    tag = f"v{version}"

    result = subprocess.run(
        ["git", "tag", "-a", tag, "-m", f"Release {version}"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error creating tag: {result.stderr}")
        sys.exit(1)

    print(f"Created tag: {tag}")


def push_git_tag(version: str) -> None:
    """Push the git tag to remote."""
    tag = f"v{version}"

    result = subprocess.run(
        ["git", "push", "origin", tag],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error pushing tag: {result.stderr}")
        sys.exit(1)

    print(f"Pushed tag: {tag}")


def distribution_files() -> list[str]:
    """Resolve artifact paths without requiring shell wildcard expansion."""
    files = sorted(str(path) for path in Path("dist").iterdir()
                   if path.is_file() and (path.name.endswith(".whl") or path.name.endswith(".tar.gz"))) if Path("dist").is_dir() else []
    if not files:
        raise FileNotFoundError("Build wheel and source distributions first")
    return files


def publish_to_pypi() -> None:
    """Publish the package to PyPI."""
    print("Publishing to PyPI...")

    result = subprocess.run(
        [sys.executable, "-m", "twine", "upload", *distribution_files()],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error publishing to PyPI: {result.stderr}")
        sys.exit(1)

    print("Published to PyPI successfully.")


def publish_to_testpypi() -> None:
    """Publish the package to TestPyPI."""
    print("Publishing to TestPyPI...")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository-url",
            "https://test.pypi.org/legacy/",
            *distribution_files(),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error publishing to TestPyPI: {result.stderr}")
        sys.exit(1)

    print("Published to TestPyPI successfully.")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Release Flaxon")
    parser.add_argument(
        "version",
        help="Version to release (e.g., 0.1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    parser.add_argument(
        "--testpypi",
        action="store_true",
        help="Publish to TestPyPI instead of PyPI",
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip creating git tag",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip publishing to PyPI",
    )

    args = parser.parse_args()

    version = args.version
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?", version):
        parser.error("Use a version such as 0.3.0 or 0.3.0rc1")
    current_version = get_current_version()

    print(f"Current version: {current_version}")
    print(f"New version: {version}")
    if version == current_version:
        parser.error("Choose a new release version; do not republish the current version")

    if not args.dry_run:
        confirm = input("Proceed with release? (y/N): ")
        if confirm.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    if args.dry_run:
        print("DRY RUN - No changes will be made")

    if args.dry_run:
        print("Would update the version/changelog, build, validate, tag and publish as selected")
        return

    if not args.no_tag:
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if status.stdout.strip():
            parser.error("Commit or stash working-tree changes before a tagged release")

    # Update version
    if not args.dry_run:
        update_version(version)
        update_changelog(version)

    # Build distributions
    print("Building distributions...")
    subprocess.run([sys.executable, "scripts/build.py", "--clean", "--check"], check=True)

    # Create and push tag
    if not args.dry_run and not args.no_tag:
        commit_release(version)
        create_git_tag(version)
        push_git_tag(version)

    # Publish to PyPI
    if not args.dry_run and not args.no_publish:
        if args.testpypi:
            publish_to_testpypi()
        else:
            publish_to_pypi()

    print(f"\nRelease {version} complete!")


if __name__ == "__main__":
    main()