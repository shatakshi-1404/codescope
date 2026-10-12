import hashlib
import re
from bisect import bisect_right

from app.analysis.complexity.js_complexity import measure_js_body
from app.analysis.types import ClassInfo, FileMetrics, FunctionMetrics, ImportInfo

# Matches comments and string literals so they can be blanked out.
_TOKEN = re.compile(
    r"""//[^\n]*|/\*.*?(?:\*/|\Z)|'(?:\\.|[^'\\\n])*'?|"(?:\\.|[^"\\\n])*"?|`(?:\\.|[^`\\])*`?""",
    re.S,
)
_NOT_NEWLINE = re.compile(r"[^\n]")

_KEYWORDS = frozenset(
    {"if", "for", "while", "switch", "catch", "with", "function", "return", "else",
     "do", "try", "typeof", "await", "new", "import", "super", "constructor_"}
)

_FUNC_DECL = re.compile(r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)?\s*\(")
_ARROW = re.compile(
    r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=\n]+)?=\s*(?:async\s*)?"
    r"(\([^()]*\)|[A-Za-z_$][\w$]*)\s*(?::\s*[^={\n]+?)?\s*=>\s*\{"
)
_METHOD = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|static|async|readonly|override|get|set)\s+)*"
    r"([A-Za-z_$][\w$]*)\s*\(([^()]*)\)\s*(?::\s*[^{;=\n]+)?\s*\{",
    re.M,
)
_IMPORT_STMT = re.compile(r"^[ \t]*import\s+([^;'\"]*?)\s*from\s*['\"]", re.M)
_IMPORT_ANY = re.compile(r"^[ \t]*import\b(?!\s*\()", re.M)
_REQUIRE = re.compile(r"\brequire\s*\(")
_CLASS = re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)")


def sanitize(source: str) -> str:
    """Blank comments and string CONTENTS. Length, newlines and quote characters are preserved."""

    def blank(m: re.Match) -> str:
        s = m.group(0)
        if s.startswith("//") or s.startswith("/*"):
            return _NOT_NEWLINE.sub(" ", s)
        quote = s[0]
        if len(s) >= 2 and s[-1] == quote:
            return quote + _NOT_NEWLINE.sub(" ", s[1:-1]) + quote
        return quote + _NOT_NEWLINE.sub(" ", s[1:])

    return _TOKEN.sub(blank, source)


def _brace_pairs(text: str) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for m in re.finditer(r"[{}]", text):
        if m.group() == "{":
            stack.append(m.start())
        elif stack:
            pairs[stack.pop()] = m.start()
    return pairs


def _find_close_paren(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, min(len(text), open_idx + 2000)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_body_brace(text: str, after_idx: int) -> int:
    """First `{` after the parameter list, unless a `;` shows it is only a declaration."""
    for i in range(after_idx + 1, min(len(text), after_idx + 200)):
        if text[i] == "{":
            return i
        if text[i] == ";":
            return -1
    return -1


def count_js_params(params: str) -> int:
    params = params.strip()
    if not params:
        return 0
    depth = 0
    count = 1
    prev = ""
    for ch in params:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ">" and prev != "=":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
        prev = ch
    if params.endswith(","):
        count -= 1
    if params.startswith("this:"):  # TypeScript `this` pseudo-parameter
        count -= 1
    return max(count, 0)


def _find_functions(clean: str, pairs: dict[int, int], line_of) -> list[FunctionMetrics]:
    found: dict[int, FunctionMetrics] = {}

    def add(name: str | None, decl_idx: int, params: str, open_idx: int) -> None:
        close_idx = pairs.get(open_idx)
        if close_idx is None or open_idx in found:
            return
        body = clean[open_idx + 1 : close_idx]
        depth, branches, cyclomatic = measure_js_body(body)
        start, end = line_of(decl_idx), line_of(close_idx)
        normalized = re.sub(r"\s+", " ", body).strip()
        found[open_idx] = FunctionMetrics(
            name=name or "<anonymous>",
            line=start,
            length=end - start + 1,
            param_count=count_js_params(params),
            max_nesting=depth,
            branch_count=branches,
            cyclomatic=cyclomatic,
            body_hash=hashlib.sha1(normalized.encode()).hexdigest()[:16],
            body_size=sum(1 for ln in body.splitlines() if ln.strip()),
        )

    for m in _FUNC_DECL.finditer(clean):
        open_paren = m.end() - 1
        close_paren = _find_close_paren(clean, open_paren)
        if close_paren == -1:
            continue
        brace = _find_body_brace(clean, close_paren)
        if brace == -1:
            continue
        name = m.group(1)
        if not name:  # `const foo = function () {}` / `foo: function () {}`
            prefix = clean[max(0, m.start() - 80) : m.start()]
            assigned = re.search(r"([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?$", prefix)
            name = assigned.group(1) if assigned else None
        add(name, m.start(), clean[open_paren + 1 : close_paren], brace)

    for m in _ARROW.finditer(clean):
        params = m.group(2)
        if params.startswith("("):
            params = params[1:-1]
        add(m.group(1), m.start(), params, m.end() - 1)

    for m in _METHOD.finditer(clean):
        if m.group(1) in _KEYWORDS:
            continue
        add(m.group(1), m.start(), m.group(2), m.end() - 1)

    return sorted(found.values(), key=lambda f: f.line)


def _imported_names(clause: str) -> list[str]:
    clause = re.sub(r"^type\s+", "", clause.strip())
    names: list[str] = []

    braces = re.search(r"\{([^}]*)\}", clause)
    if braces:
        for part in braces.group(1).split(","):
            part = re.sub(r"^type\s+", "", part.strip())
            if part:
                names.append(re.split(r"\s+as\s+", part)[-1].strip())
        clause = clause.replace(braces.group(0), "")

    ns = re.search(r"\*\s*as\s+([\w$]+)", clause)
    if ns:
        names.append(ns.group(1))
        clause = clause.replace(ns.group(0), "")

    default = clause.strip().strip(",").strip()
    if default and re.fullmatch(r"[A-Za-z_$][\w$]*", default):
        names.append(default)
    return names


def _unused_imports(clean: str, line_of) -> list[ImportInfo]:
    unused: list[ImportInfo] = []
    for m in _IMPORT_STMT.finditer(clean):
        for name in _imported_names(m.group(1)):
            if name == "React":  # automatic JSX runtime makes this look unused
                continue
            pattern = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
            if len(pattern.findall(clean)) <= 1:
                unused.append(ImportInfo(name, line_of(m.start())))
    return unused


def _count_loc(source: str) -> int:
    return sum(
        1
        for ln in source.splitlines()
        if ln.strip() and not ln.strip().startswith(("//", "/*", "*", "*/"))
    )


def parse_js(path: str, source: str, language: str) -> FileMetrics:
    clean = sanitize(source)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]

    def line_of(idx: int) -> int:
        return bisect_right(line_starts, idx)

    pairs = _brace_pairs(clean)
    return FileMetrics(
        path=path,
        language=language,
        total_lines=len(source.splitlines()),
        lines_of_code=_count_loc(source),
        functions=_find_functions(clean, pairs, line_of),
        classes=[ClassInfo(m.group(1), line_of(m.start())) for m in _CLASS.finditer(clean)],
        import_count=len(_IMPORT_ANY.findall(clean)) + len(_REQUIRE.findall(clean)),
        unused_imports=_unused_imports(clean, line_of),
    )
