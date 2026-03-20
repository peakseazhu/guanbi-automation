from __future__ import annotations

from pathlib import Path
import tomllib

from pydantic import BaseModel, ConfigDict


class DependencyManifest(BaseModel):
    """Single-source dependency manifest loaded from pyproject.toml."""

    model_config = ConfigDict(frozen=True)

    source_path: Path
    dependencies: tuple[str, ...]


def load_dependency_manifest(path: Path | str) -> DependencyManifest:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dependency manifest not found: {manifest_path}")

    data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    dependencies = tuple(project.get("dependencies", []))

    return DependencyManifest(source_path=manifest_path, dependencies=dependencies)
