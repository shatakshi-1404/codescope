import ast
import hashlib
import re

from app.analysis.complexity.python_complexity import measure_function
from app.analysis.types import ClassInfo, FileMetrics, FunctionMetrics, ImportInfo


def _count_loc(source: str) -> int:
    return sum(1 for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("#"))


def _collect(node, prefix, in_class, funcs, classes) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            classes.append(ClassInfo(child.name, child.lineno))
            _collect(child, f"{prefix}{child.name}.", True, funcs, classes)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((f"{prefix}{child.name}", child, in_class))
            _collect(child, f"{prefix}{child.name}.", False, funcs, classes)
        else:
            _collect(child, prefix, in_class, funcs, classes)


def _param_count(func, is_method: bool) -> int:
    a = func.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if is_method and names and names[0] in ("self", "cls"):
        names = names[1:]
    count = len(names) + len(a.kwonlyargs)
    if a.vararg:
        count += 1
    if a.kwarg:
        count += 1
    return count


def _body_hash(func) -> tuple[str | None, int]:
    """Hash of the function body (docstring removed). Equal hash = structurally identical."""
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return None, 0
    module = ast.Module(body=body, type_ignores=[])
    digest = hashlib.sha1(ast.dump(module).encode()).hexdigest()[:16]
    size = sum(1 for n in ast.walk(module) if isinstance(n, ast.stmt))
    return digest, size


def _find_unused_imports(tree: ast.Module, path: str) -> list[ImportInfo]:
    """
    Only module-level imports are checked, and anything ambiguous counts as "used":
    - __init__.py files (re-exports)
    - names appearing in any string (string annotations, __all__)
    """
    if path.endswith("__init__.py"):
        return []

    candidates: list[ImportInfo] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                candidates.append(ImportInfo(a.asname or a.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for a in node.names:
                if a.name != "*":
                    candidates.append(ImportInfo(a.asname or a.name, node.lineno))
    if not candidates:
        return []

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    strings = " ".join(
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    )

    unused = []
    for c in candidates:
        if c.name in used:
            continue
        if re.search(rf"(?<!\w){re.escape(c.name)}(?!\w)", strings):
            continue
        unused.append(c)
    return unused


def parse_python(path: str, source: str) -> tuple[FileMetrics, ast.Module | None]:
    total_lines = len(source.splitlines())
    loc = _count_loc(source)

    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError, RecursionError) as exc:
        metrics = FileMetrics(
            path=path,
            language="python",
            total_lines=total_lines,
            lines_of_code=loc,
            parse_error=f"{type(exc).__name__}: {exc}",
        )
        return metrics, None

    funcs: list = []
    classes: list[ClassInfo] = []
    _collect(tree, "", False, funcs, classes)

    functions: list[FunctionMetrics] = []
    for qualname, node, is_method in funcs:
        c = measure_function(node)
        body_hash, body_size = _body_hash(node)
        end = node.end_lineno or node.lineno
        functions.append(
            FunctionMetrics(
                name=qualname,
                line=node.lineno,
                length=end - node.lineno + 1,
                param_count=_param_count(node, is_method),
                max_nesting=c.max_nesting,
                branch_count=c.branches,
                cyclomatic=c.cyclomatic,
                body_hash=body_hash,
                body_size=body_size,
            )
        )

    metrics = FileMetrics(
        path=path,
        language="python",
        total_lines=total_lines,
        lines_of_code=loc,
        functions=functions,
        classes=classes,
        import_count=sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)),
        unused_imports=_find_unused_imports(tree, path),
    )
    return metrics, tree
