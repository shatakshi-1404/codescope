import sys

from app.analysis.engine import analyze_directory


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m app.analysis.cli <directory>")
        return 2

    result = analyze_directory(sys.argv[1])
    s = result.score

    print(f"\nFiles: {result.files_analyzed}   Lines: {result.lines_analyzed}   "
          f"Functions: {result.function_count}   Classes: {result.class_count}   "
          f"Skipped: {result.skipped_files}")
    print(f"Language: {result.primary_language}")
    print(f"\nOverall {s.overall}/100   Quality {s.code_quality}   "
          f"Maintainability {s.maintainability}   Complexity {s.complexity}   Security {s.security}")
    print(f"Score details: {s.details}")

    print(f"\nIssues: {len(result.issues)}")
    for f in result.issues[:10]:
        print(f"  [{f.severity.value:<8}] {f.rule_id}  {f.file}:{f.line}  {f.title}")

    print(f"\nStatic security checks: {len(result.security_findings)}")
    for f in result.security_findings[:10]:
        print(f"  [{f.severity.value:<8}] {f.rule_id}  {f.file}:{f.line}  {f.title}")

    for w in result.warnings[:5]:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
