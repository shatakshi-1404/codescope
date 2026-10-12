from app.intelligence.clustering import cluster_texts, normalize
from app.intelligence.summary import SummaryInput, generate_summary, improvement_plan, score_label


def _inp(**over) -> SummaryInput:
    base = dict(
        repo_name="acme/api", overall=82.0, code_quality=84.0, maintainability=79.0,
        complexity=76.0, security=91.0, files_analyzed=40, lines_analyzed=5200,
        issue_severity={"HIGH": 2, "LOW": 6}, security_severity={},
        issue_categories={"complexity": 5, "naming": 3}, top_files=[("app/core.py", 4)],
        previous_overall=None,
    )
    base.update(over)
    return SummaryInput(**base)


# ---------------------------------------------------------------- summary
def test_summary_content_and_determinism():
    text = generate_summary(_inp())
    assert text == generate_summary(_inp())
    assert "82/100" in text
    assert "strongest area is security (91)" in text
    assert "weakest is complexity (76)" in text
    assert "8 quality issues were found, 2 of them high or critical" in text
    assert "not a full security audit" in text


def test_summary_reports_trend():
    assert "improved by 4.0 points" in generate_summary(_inp(previous_overall=78.0))
    assert "declined by 3.0 points" in generate_summary(_inp(previous_overall=85.0))
    assert "unchanged" in generate_summary(_inp(previous_overall=82.2))


def test_summary_with_no_issues():
    text = generate_summary(_inp(issue_severity={}, issue_categories={}, top_files=[]))
    assert "No code quality issues were detected." in text


def test_score_labels():
    assert [score_label(s) for s in (95, 85, 70, 55, 10)] == [
        "excellent", "good", "fair", "needs attention", "poor",
    ]


def test_plan_puts_critical_security_first_and_is_capped():
    plan = improvement_plan(
        {"HIGH": 3}, {"CRITICAL": 1, "HIGH": 2},
        {"complexity": 5, "naming": 3, "duplication": 2, "unused-code": 1},
    )
    assert "critical" in plan[0].lower()
    assert len(plan) == 4


def test_plan_default_when_clean():
    assert len(improvement_plan({}, {}, {})) == 1


# ------------------------------------------------------------- clustering
def test_normalize_drops_identifiers_numbers_and_stopwords():
    assert normalize("`parse_config` has 61 lines (threshold: 50).") == ("line",)


def test_same_rule_findings_cluster_together():
    texts = [
        "`a` has 61 lines (threshold: 50).",
        "`b` has 90 lines (threshold: 50).",
        "`c` has 7 parameters (threshold: 5).",
    ]
    assert cluster_texts(texts) == [[0, 1], [2]]


def test_similar_security_descriptions_merge_but_unrelated_stay_apart():
    texts = [
        "eval() executes arbitrary code and is dangerous with untrusted input.",
        "exec() executes arbitrary code and is dangerous with untrusted input.",
        "`os` is imported but never used in this file.",
    ]
    clusters = cluster_texts(texts)
    assert [0, 1] in clusters and [2] in clusters


def test_empty_input():
    assert cluster_texts([]) == []
