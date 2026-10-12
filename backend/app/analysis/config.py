from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    """Every quality rule reads its limit from here. Override per analysis."""

    max_function_length: int = 50      # lines
    max_parameters: int = 5
    max_nesting_depth: int = 4
    max_branches: int = 10
    max_cyclomatic: int = 15
    max_file_lines: int = 500
    min_duplicate_size: int = 6        # smallest function body checked for duplication


@dataclass(frozen=True)
class EngineLimits:
    """Guard rails so a huge or hostile repository cannot exhaust the server."""

    max_files: int = 2000
    max_file_bytes: int = 1_000_000
    ignored_dirs: frozenset[str] = frozenset(
        {
            "node_modules", "venv", ".venv", "env", "__pycache__", "dist",
            "build", "site-packages", "vendor", "coverage", "target",
        }
    )


DEFAULT_THRESHOLDS = Thresholds()
DEFAULT_LIMITS = EngineLimits()
