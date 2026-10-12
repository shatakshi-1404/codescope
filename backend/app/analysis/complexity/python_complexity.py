import ast
from dataclasses import dataclass

_NESTING = tuple(
    getattr(ast, name)
    for name in ("If", "For", "AsyncFor", "While", "Try", "TryStar", "With", "AsyncWith", "Match")
    if hasattr(ast, name)
)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_LOOPS = (ast.For, ast.AsyncFor, ast.While)
_MATCH_CASE = getattr(ast, "match_case", None)


@dataclass(frozen=True)
class FunctionComplexity:
    max_nesting: int
    branches: int
    cyclomatic: int


def measure_function(func: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionComplexity:
    """
    Measures ONE function (nested functions/classes are measured separately).

    - nesting depth : deepest chain of if/for/while/try/with/match blocks
                      (an `elif` does NOT add depth)
    - branches      : if/elif, ternary (x if y else z), match cases
    - cyclomatic    : 1 + decision points
                      (if, loops, except, ternary, and/or, comprehension for/if, match case)
    """
    max_nesting = 0
    branches = 0
    cyclomatic = 1

    def visit(node: ast.AST, depth: int, is_elif: bool = False) -> None:
        nonlocal max_nesting, branches, cyclomatic

        if isinstance(node, _SCOPES):
            return

        if isinstance(node, _NESTING) and not is_elif:
            depth += 1
            max_nesting = max(max_nesting, depth)

        if isinstance(node, ast.If):
            branches += 1
            cyclomatic += 1
        elif isinstance(node, _LOOPS) or isinstance(node, ast.ExceptHandler):
            cyclomatic += 1
        elif isinstance(node, ast.IfExp):
            branches += 1
            cyclomatic += 1
        elif isinstance(node, ast.BoolOp):
            cyclomatic += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            cyclomatic += 1 + len(node.ifs)
        elif _MATCH_CASE is not None and isinstance(node, _MATCH_CASE):
            branches += 1
            cyclomatic += 1

        for name, value in ast.iter_fields(node):
            # `elif` is an If nested in the parent's orelse: keep the same depth.
            if (
                isinstance(node, ast.If)
                and name == "orelse"
                and len(value) == 1
                and isinstance(value[0], ast.If)
            ):
                visit(value[0], depth, is_elif=True)
                continue
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST):
                    visit(child, depth)

    for stmt in func.body:
        visit(stmt, 0)

    return FunctionComplexity(max_nesting, branches, cyclomatic)
