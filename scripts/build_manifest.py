"""Prepare the SHA-256 manifest for the standalone MethodsX companion."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL_FILES = {"README.md", ".env.example", ".gitignore", "requirements.txt"}
DIRECTORIES = {"analysis", "contracts", "diagrams", "scripts", "study", "supplementary"}
EXCLUDED = {".git", ".venv", "__pycache__", "runtime", ".DS_Store"}
INTERNAL_FILES = {
    "agents.md",
    "agents.override.md",
    "claude.md",
    "skill.md",
    "copilot-instructions.md",
}
INTERNAL_DIRECTORIES = {".agents", ".codex", ".claude", "agent_workflow"}


def digest(path):
    """Hash a file without loading the entire file into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def files():
    """Select the reproducible sources, final data and scientific evidence."""
    selected = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in EXCLUDED for part in relative.parts):
            continue
        if path.name.casefold() in INTERNAL_FILES or any(
            part.casefold() in INTERNAL_DIRECTORIES for part in relative.parts
        ):
            raise ValueError(f"Internal instructions must not be published: {relative}")
        if path.is_symlink():
            raise ValueError(f"Symlinks are not deliverable evidence: {relative}")
        if path.name == "MANIFEST.sha256.json":
            continue
        include = (
            path.name in TOP_LEVEL_FILES
            if len(relative.parts) == 1
            else relative.parts[0] in DIRECTORIES
        )
        if not include:
            continue
        if relative.parts[0] == "diagrams" and path.suffix.lower() not in {
            ".drawio",
            ".png",
        }:
            raise ValueError(f"Diagrams must be draw.io or PNG: {relative}")
        if relative.parts[0] == "analysis" and path.suffix.lower() not in {
            ".png",
            ".csv",
            ".json",
        }:
            raise ValueError(f"Plots must be PNG: {relative}")
        if path.name == ".env" or path.suffix in {
            ".sqlite3",
            ".sqlite",
            ".db",
            ".pyc",
            ".zip",
        }:
            raise ValueError(f"Private/generated file in release selection: {relative}")
        if path.stat().st_size >= 100 * 1024 * 1024:
            raise ValueError(f"File exceeds GitHub's regular-file limit: {relative}")
        selected.append(path)
    return sorted(selected)


def main():
    selected = files()
    manifest = {path.relative_to(ROOT).as_posix(): digest(path) for path in selected}
    output = ROOT / "MANIFEST.sha256.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": str(output), "files": len(manifest) + 1}, indent=2))


if __name__ == "__main__":
    main()
