import sys

IGNORED_MODULES = {"httpx", "httpcore"}
IGNORED_PREFIXES = tuple(f"{mod}." for mod in IGNORED_MODULES)


def should_load_eager(name: str) -> bool:
    return name in IGNORED_MODULES or name.startswith(IGNORED_PREFIXES)


def lazy_import_filter(
    importing_module: str,
    imported_module: str,
    fromlist: tuple[str, ...] | None,
) -> bool:
    """Returns True to allow lazy loading; False forces eager loading."""

    if should_load_eager(imported_module):
        return False

    # from x import y
    if fromlist:
        for name in fromlist:
            if should_load_eager(f"{imported_module}.{name}"):
                return False

    return True


def apply() -> None:
    sys.set_lazy_imports_filter(lazy_import_filter)


def remove() -> None:
    sys.set_lazy_imports_filter(None)
