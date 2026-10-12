import re

_CONTROL_HEADER = re.compile(r"^\s*(?:else\s+if|if|for|while|switch|catch|try|do|else|finally)\b")
_IF = re.compile(r"\bif\b")
_CASE = re.compile(r"\bcase\b")
_LOOP = re.compile(r"\b(?:for|while)\b")
_CATCH = re.compile(r"\bcatch\b")
_LOGICAL = re.compile(r"&&|\|\||\?\?")
_TERNARY = re.compile(r"(?<!\?)\?(?![.?:])")


def measure_js_body(body: str) -> tuple[int, int, int]:
    """
    Heuristic metrics for a function body that has already been sanitized
    (comments and string contents blanked). Returns (max_nesting, branches, cyclomatic).

    Nesting counts only braces opened by control statements (if/for/while/...),
    so nested callbacks do not inflate it.
    """
    stack: list[bool] = []
    depth = 0
    max_depth = 0
    paren = 0
    header_start = 0

    for i, ch in enumerate(body):
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(0, paren - 1)
        elif ch == "{":
            is_control = bool(_CONTROL_HEADER.match(body[header_start:i]))
            stack.append(is_control)
            if is_control:
                depth += 1
                max_depth = max(max_depth, depth)
            header_start = i + 1
        elif ch == "}":
            if stack and stack.pop():
                depth -= 1
            header_start = i + 1
        elif ch == ";" and paren == 0:
            header_start = i + 1

    ifs = len(_IF.findall(body))
    cases = len(_CASE.findall(body))
    ternaries = len(_TERNARY.findall(body))
    branches = ifs + cases + ternaries
    cyclomatic = (
        1 + ifs + cases + ternaries
        + len(_LOOP.findall(body))
        + len(_CATCH.findall(body))
        + len(_LOGICAL.findall(body))
    )
    return max_depth, branches, cyclomatic
