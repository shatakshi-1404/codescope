import ast
import math
import re
from collections import Counter

from app.analysis.types import Finding, Severity

CATEGORY = "security"


def _f(rule_id, path, line, severity, title, description, recommendation) -> Finding:
    return Finding(rule_id, path, line, CATEGORY, severity, title, description, recommendation)


# =============================================================== Python (AST)
_SUBPROCESS_FUNCS = {"run", "call", "Popen", "check_call", "check_output"}
_SQL_EXEC = {"execute", "executemany", "executescript"}


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _is_const_str(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _kw_is(node: ast.Call, key: str, value: bool) -> bool:
    return any(
        kw.arg == key and isinstance(kw.value, ast.Constant) and kw.value.value is value
        for kw in node.keywords
    )


def _is_dynamic_sql(node: ast.AST) -> bool:
    """f-string with values, "..." % x, "..." + x, or "...".format(x)."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        parts = list(ast.walk(node))
        has_str = any(_is_const_str(n) for n in parts)
        has_dynamic = any(isinstance(n, (ast.Name, ast.Attribute, ast.Call, ast.Subscript)) for n in parts)
        return has_str and has_dynamic
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and _is_const_str(node.func.value)
    ):
        return True
    return False


def _mentions_password(node: ast.AST) -> bool:
    try:
        text = ast.unparse(node).lower()
    except Exception:  # unparse can fail on exotic nodes; treat as "no"
        return False
    return any(w in text for w in ("password", "passwd", "pwd"))


def _check_call(path: str, node: ast.Call) -> list[Finding]:
    out: list[Finding] = []
    name = _dotted(node.func)
    attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
    line = node.lineno

    if name == "eval":
        out.append(_f("SEC-EVAL", path, line, Severity.HIGH, "Use of eval()",
                      "eval() executes arbitrary code and is dangerous with untrusted input.",
                      "Use ast.literal_eval for data, or a proper parser."))
    elif name == "exec":
        out.append(_f("SEC-EXEC", path, line, Severity.HIGH, "Use of exec()",
                      "exec() executes arbitrary code and is dangerous with untrusted input.",
                      "Avoid dynamic code execution; use explicit dispatch instead."))

    if name.startswith("subprocess.") and attr in _SUBPROCESS_FUNCS and _kw_is(node, "shell", True):
        dynamic = bool(node.args) and not _is_const_str(node.args[0])
        out.append(_f(
            "SEC-SUBPROCESS-SHELL", path, line, Severity.HIGH if dynamic else Severity.LOW,
            "subprocess with shell=True",
            "shell=True runs the command through a shell; "
            + ("the command is built dynamically, so shell injection is possible."
               if dynamic else "the command is a constant string, so risk is low."),
            "Pass the command as a list and drop shell=True.",
        ))

    if name in ("os.system", "os.popen"):
        dynamic = bool(node.args) and not _is_const_str(node.args[0])
        out.append(_f(
            "SEC-SUBPROCESS-SHELL", path, line, Severity.HIGH if dynamic else Severity.LOW,
            f"Use of {name}()",
            f"{name}() runs a shell command"
            + (" built from a dynamic value, which allows command injection." if dynamic else "."),
            "Use subprocess.run with a list of arguments instead.",
        ))

    if attr in _SQL_EXEC and node.args and _is_dynamic_sql(node.args[0]):
        out.append(_f("SEC-SQL-INJECTION", path, line, Severity.HIGH,
                      "SQL built with string formatting",
                      "A SQL statement is assembled with string formatting/concatenation, "
                      "which can allow SQL injection.",
                      "Use parameterized queries: execute(sql, params)."))

    if name in ("hashlib.md5", "hashlib.sha1") and _mentions_password(node):
        out.append(_f("SEC-WEAK-PASSWORD-HASH", path, line, Severity.HIGH,
                      "Password hashed with a weak algorithm",
                      f"{name} is fast and unsuitable for password storage.",
                      "Use argon2, bcrypt or scrypt."))

    if name in ("pickle.load", "pickle.loads", "cPickle.loads"):
        out.append(_f("SEC-DESERIALIZATION", path, line, Severity.MEDIUM,
                      "Unsafe deserialization with pickle",
                      "Unpickling untrusted data can execute arbitrary code.",
                      "Use JSON or another safe format for untrusted data."))

    if _kw_is(node, "verify", False):
        out.append(_f("SEC-TLS-VERIFY", path, line, Severity.MEDIUM,
                      "TLS certificate verification disabled",
                      "verify=False disables HTTPS certificate checks.",
                      "Remove verify=False or point it at a trusted CA bundle."))
    return out


def scan_python(path: str, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            findings.extend(_check_call(path, node))
    return findings


# ===================================================== JavaScript / TypeScript
_JS_RULES = (
    ("SEC-EVAL", re.compile(r"(?<![.\w$])eval\s*\("), Severity.HIGH, "Use of eval()",
     "eval() executes arbitrary code and is dangerous with untrusted input.",
     "Avoid eval; parse data with JSON.parse or use explicit logic.", None),
    ("SEC-EVAL", re.compile(r"\bnew\s+Function\s*\("), Severity.HIGH, "Dynamic code via new Function()",
     "new Function() compiles a string into code, like eval().",
     "Avoid generating code from strings.", None),
    ("SEC-DOM-XSS", re.compile(r"\.innerHTML\s*=(?!=)|\bdangerouslySetInnerHTML\b|\bdocument\.write\s*\("),
     Severity.MEDIUM, "Possible DOM XSS sink",
     "Writing HTML from strings can enable cross-site scripting if the data is untrusted.",
     "Use textContent or sanitize the HTML (e.g. DOMPurify).", None),
    ("SEC-COMMAND-INJECTION",
     re.compile(r"(?:child_process\.|(?<![.\w]))(?:exec|execSync)\s*\(\s*(?:`[^`\n]*\$\{|[^)\n]*\+)"),
     Severity.HIGH, "Shell command built from dynamic input",
     "exec/execSync receives a command assembled from variables, which allows command injection.",
     "Use execFile/spawn with an argument array.", None),
    ("SEC-SQL-INJECTION",
     re.compile(r"\.(?:query|execute|raw)\s*\(\s*(?:`[^`\n]*\$\{|['\"][^'\"\n]*['\"]\s*\+)"),
     Severity.HIGH, "SQL built with string interpolation",
     "A SQL statement is assembled with interpolation/concatenation, which can allow SQL injection.",
     "Use parameterized queries / placeholders.", None),
    ("SEC-WEAK-PASSWORD-HASH", re.compile(r"createHash\(\s*['\"](?:md5|sha1)['\"]\s*\)"),
     Severity.HIGH, "Password hashed with a weak algorithm",
     "md5/sha1 are fast and unsuitable for password storage.",
     "Use argon2, bcrypt or scrypt.", lambda line: "pass" in line.lower()),
    ("SEC-TLS-VERIFY", re.compile(r"rejectUnauthorized\s*:\s*false"), Severity.MEDIUM,
     "TLS certificate verification disabled",
     "rejectUnauthorized: false disables HTTPS certificate checks.",
     "Remove it or configure a trusted CA.", None),
)


def scan_javascript(path: str, source: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or len(line) > 2000 or stripped.startswith(("//", "*", "/*")):
            continue
        for rule_id, regex, severity, title, desc, rec, condition in _JS_RULES:
            if regex.search(line) and (condition is None or condition(line)):
                findings.append(_f(rule_id, path, lineno, severity, title, desc, rec))
    return findings


# ================================================== Secrets (all languages)
_PLACEHOLDER = re.compile(
    r"(?i)(example|placeholder|changeme|change_me|your[_-]|xxxx|<[^>]*>|\$\{|\{\{|"
    r"process\.env|os\.environ|getenv|dummy|sample|test|\*{3,}|todo)"
)
_TRIVIAL = {"password", "passwd", "pwd", "secret", "token", "none", "null", "true", "false"}
_IDENTIFIER_LIKE = re.compile(r"[a-z]+(?:[_\- .][a-z]+)+")

_PASSWORD = re.compile(
    r"""(?i)\b([\w.]*(?:password|passwd|pwd)\w*)["']?(?:\s*:\s*[\w\[\], .|]+)?\s*[:=]\s*(["'])([^"'\n]{4,})\2"""
)
_API_KEY = re.compile(
    r"""(?i)\b[\w.]*(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token|auth[_-]?token|"""
    r"""client[_-]?secret|private[_-]?key)\w*["']?\s*[:=]\s*(["'])([A-Za-z0-9_\-/+=.]{16,})\1"""
)
_TOKEN_FORMATS = (
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\bsk_live_[0-9a-zA-Z]{24,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
)
_STRING_LITERAL = re.compile(r"""["']([A-Za-z0-9+/=_\-]{32,128})["']""")


def _looks_real(value: str) -> bool:
    if _PLACEHOLDER.search(value) or value.lower() in _TRIVIAL:
        return False
    if _IDENTIFIER_LIKE.fullmatch(value):
        return False
    return True


def _entropy(s: str) -> float:
    counts = Counter(s)
    return -sum((c / len(s)) * math.log2(c / len(s)) for c in counts.values())


def scan_secrets(path: str, source: str, language: str) -> list[Finding]:
    findings: list[Finding] = []
    flagged: set[int] = set()
    comment_prefixes = ("#",) if language == "python" else ("//", "*", "/*")

    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or len(line) > 2000:
            continue
        is_comment = stripped.startswith(comment_prefixes)

        # Known token formats are reported even inside comments (a leaked key is a leak).
        for label, regex in _TOKEN_FORMATS:
            if regex.search(line):
                findings.append(_f(
                    "SEC-SECRET-TOKEN", path, lineno, Severity.CRITICAL, f"{label} in source code",
                    f"A value matching the format of a {label} was found. The value is not shown here.",
                    "Revoke and rotate it immediately, then load secrets from environment variables.",
                ))
                flagged.add(lineno)
                break
        if lineno in flagged or is_comment:
            continue

        m = _PASSWORD.search(line)
        if m and _looks_real(m.group(3)):
            findings.append(_f(
                "SEC-HARDCODED-PASSWORD", path, lineno, Severity.HIGH, "Hardcoded password",
                f"`{m.group(1)}` is assigned a literal string value.",
                "Move it to an environment variable or secret manager and rotate it.",
            ))
            flagged.add(lineno)
            continue

        m = _API_KEY.search(line)
        if m and _looks_real(m.group(2)):
            findings.append(_f(
                "SEC-HARDCODED-API-KEY", path, lineno, Severity.HIGH, "Hardcoded API key or secret",
                "A key/secret-like variable is assigned a literal string value.",
                "Move it to an environment variable or secret manager and rotate it.",
            ))
            flagged.add(lineno)
            continue

        if "integrity" in line:
            continue
        for sm in _STRING_LITERAL.finditer(line):
            if _entropy(sm.group(1)) > 4.5:
                findings.append(_f(
                    "SEC-HIGH-ENTROPY", path, lineno, Severity.MEDIUM, "Suspicious high-entropy string",
                    "A long random-looking string literal may be a secret. Review it manually.",
                    "If it is a credential, move it out of source code.",
                ))
                break
    return findings
