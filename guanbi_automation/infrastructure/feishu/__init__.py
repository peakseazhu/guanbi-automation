from .target_planner import (
    ResolvedPublishTarget,
    chunk_publish_rows,
    resolve_append_rows,
    resolve_replace_range,
    resolve_replace_sheet,
)

__all__ = [
    "ResolvedPublishTarget",
    "chunk_publish_rows",
    "resolve_append_rows",
    "resolve_replace_range",
    "resolve_replace_sheet",
    "write_publish_target",
]


def __getattr__(name: str):
    if name == "write_publish_target":
        from .publish_writer import write_publish_target

        return write_publish_target
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
