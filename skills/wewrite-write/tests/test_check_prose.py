"""check_prose.py 的长度与复述闸门回归测试。

样例取自 2026-10-16 opencsg-99-credit-burned 那篇被打回的稿子：账单数字在正文里
反复出现，结论节把正文的数字又念了一遍，而旧版闸门只打印汉字数、不做任何比较。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_prose.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_gate(article: str, brief: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), str(FIXTURES / article)]
    if brief:
        command += ["--brief", str(FIXTURES / brief)]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def test_repeated_precise_number_is_a_failure():
    result = run_gate("padded_article.md", "brief_analysis.yaml")

    assert result.returncode == 1, result.stdout
    assert "精确数字 111.67 在正文出现 4 次" in result.stdout


def test_table_occurrences_are_not_counted_as_prose():
    # 表格里 111.67 出现两次。如果表格没被排除，次数会是 6 而不是 4。
    result = run_gate("padded_article.md", "brief_analysis.yaml")

    assert "在正文出现 4 次" in result.stdout
    assert "在正文出现 6 次" not in result.stdout


def test_conclusion_restating_body_number_is_a_failure():
    result = run_gate("padded_article.md", "brief_analysis.yaml")

    assert result.returncode == 1, result.stdout
    assert "结论复述：第 16 行又讲了一遍第 3 行已有的事实（111.67）" in result.stdout


def test_length_cap_from_brief_is_enforced():
    result = run_gate("padded_article.md", "brief_tight_cap.yaml")

    assert result.returncode == 1, result.stdout
    assert "超过任务书声明的上限 40" in result.stdout


def test_brief_without_length_cap_warns_instead_of_silently_skipping():
    result = run_gate("clean_article.md", "brief_no_cap.yaml")

    assert result.returncode == 0, result.stdout
    assert "没有写 length_cap" in result.stdout


def test_clean_article_passes():
    result = run_gate("clean_article.md", "brief_analysis.yaml")

    assert result.returncode == 0, result.stdout
    assert "需要修改" not in result.stdout


def test_three_digit_labels_are_not_recitation():
    # 199 是额度档位，反复出现指不同侧面，不该算复述。
    result = run_gate("labels_article.md", "brief_analysis.yaml")

    assert result.returncode == 0, result.stdout


def test_reported_han_excludes_tables_and_headings():
    article = FIXTURES / "clean_article.md"
    whole_file = len(re.findall(r"[\u4e00-\u9fff]", article.read_text(encoding="utf-8")))
    result = run_gate("clean_article.md", "brief_analysis.yaml")

    reported = re.search(r"正文汉字 (\d+)", result.stdout)
    assert reported, result.stdout
    assert int(reported.group(1)) < whole_file
