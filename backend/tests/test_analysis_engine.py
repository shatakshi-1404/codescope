from app.analysis.analyzers.registry import get_analyzer
from app.analysis.config import Thresholds
from app.analysis.engine import analyze_directory
from app.analysis.metrics.scoring import compute_score
from app.analysis.quality.rules import check_duplicates, severity_by_ratio
from app.analysis.types import Severity

T = Thresholds()


def analyze(path: str, src: str):
    return get_analyzer(path).analyze(path, src, T)


# ------------------------------------------------------------------- Python
def test_python_metrics():
    src = (
        "import os\n\nclass A:\n    def m(self, x):\n        if x:\n            return 1\n"
        "        return 2\n\ndef f(a, b):\n    for i in range(a):\n        if i > b:\n"
        "            pass\n    return a\n"
    )
    m = analyze("x.py", src).metrics
    assert m.class_count == 1
    assert m.function_count == 2
    f = next(fn for fn in m.functions if fn.name == "f")
    assert (f.param_count, f.max_nesting, f.cyclomatic, f.length) == (2, 2, 3, 5)
    method = next(fn for fn in m.functions if fn.name == "A.m")
    assert method.param_count == 1  # self is not counted


def test_elif_does_not_add_nesting():
    src = "def f(x):\n    if x == 1:\n        return 1\n    elif x == 2:\n        return 2\n    elif x == 3:\n        return 3\n    return 0\n"
    fn = analyze("x.py", src).metrics.functions[0]
    assert fn.max_nesting == 1
    assert fn.cyclomatic == 4


def test_unused_import_detected():
    fa = analyze("x.py", "import os\nimport sys\nprint(sys.argv)\n")
    assert [u.name for u in fa.metrics.unused_imports] == ["os"]
    assert "QUAL-007" in {i.rule_id for i in fa.issues}


def test_long_function_flagged_with_deterministic_severity():
    src = "def big():\n" + "    x = 1\n" * 60
    issue = next(i for i in analyze("x.py", src).issues if i.rule_id == "QUAL-001")
    assert issue.severity == Severity.LOW  # 61 lines vs threshold 50 -> ratio 1.22


def test_severity_scale():
    assert severity_by_ratio(50, 50) is None
    assert severity_by_ratio(60, 50) == Severity.LOW
    assert severity_by_ratio(75, 50) == Severity.MEDIUM
    assert severity_by_ratio(125, 50) == Severity.HIGH


def test_syntax_error_is_reported_not_raised():
    fa = analyze("bad.py", "def (:\n")
    assert fa.metrics.parse_error is not None


def test_duplicate_functions_across_files():
    body = "(x):\n" + "".join(f"    y{i} = x + {i}\n" for i in range(8)) + "    return y0\n"
    a = analyze("a.py", "def one" + body).metrics
    b = analyze("b.py", "def two" + body).metrics
    found = check_duplicates([a, b], T)
    assert len(found) == 1 and found[0].rule_id == "QUAL-008" and found[0].file == "b.py"


# ----------------------------------------------------------------- Security
def test_python_security_rules():
    src = (
        'API_KEY = "abcd1234abcd1234abcd1234"\n'
        "result = eval(user_input)\n"
        'cur.execute(f"SELECT * FROM t WHERE id = {uid}")\n'
        'cur.execute("SELECT 1 WHERE id = %s", (uid,))\n'
    )
    rules = [(f.rule_id, f.line) for f in analyze("s.py", src).security]
    assert ("SEC-HARDCODED-API-KEY", 1) in rules
    assert ("SEC-EVAL", 2) in rules
    assert ("SEC-SQL-INJECTION", 3) in rules
    assert ("SEC-SQL-INJECTION", 4) not in rules  # parameterized query is safe


def test_known_token_format_is_critical_and_not_echoed():
    fa = analyze("s.py", 'key = "AKIAABCDEFGHIJKLMNOP"\n')
    finding = fa.security[0]
    assert finding.severity == Severity.CRITICAL
    assert "AKIAABCDEFGHIJKLMNOP" not in finding.description


def test_placeholder_passwords_are_ignored():
    fa = analyze("s.py", 'password = os.environ["PW"]\npassword = "changeme"\npassword_field = "id_password"\n')
    assert fa.security == []


# --------------------------------------------------------------- JavaScript
JS = """import React from 'react';
import { unusedThing } from './x';

export function Foo(a, b, c) {
  if (a) {
    for (let i = 0; i < b; i++) {
      if (c && i > 1) {
        console.log(i);
      }
    }
  }
  return a ? 1 : 2;
}
"""


def test_javascript_metrics():
    fa = analyze("a.js", JS)
    foo = fa.metrics.functions[0]
    assert foo.name == "Foo"
    assert foo.param_count == 3
    assert foo.max_nesting == 3
    assert [u.name for u in fa.metrics.unused_imports] == ["unusedThing"]


def test_javascript_security():
    src = "el.innerHTML = userInput;\nconst r = eval(code);\n"
    rules = {f.rule_id for f in analyze("a.js", src).security}
    assert {"SEC-DOM-XSS", "SEC-EVAL"} <= rules


# ------------------------------------------------------------------ Scoring
def test_perfect_score_without_findings():
    m = analyze("x.py", "def f(a):\n    return a\n").metrics
    assert compute_score([m], [], []).overall == 100.0


def test_critical_security_finding_caps_security_score():
    fa = analyze("s.py", 'key = "AKIAABCDEFGHIJKLMNOP"\n')
    score = compute_score([fa.metrics], fa.issues, fa.security)
    assert score.security <= 60.0


# ------------------------------------------------------------------- Engine
def test_engine_skips_ignored_directories(tmp_path):
    (tmp_path / "a.py").write_text("print(1)\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.js").write_text("var x = 1;\n")
    result = analyze_directory(tmp_path)
    assert [f.path for f in result.files] == ["a.py"]


def test_engine_does_not_follow_symlinks(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("print('secret')\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "link.py").symlink_to(outside)
    result = analyze_directory(repo)
    assert result.files_analyzed == 0
