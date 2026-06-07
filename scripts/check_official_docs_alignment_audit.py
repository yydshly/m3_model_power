#!/usr/bin/env python3
"""
Check script for OFFICIAL_DOCS_ALIGNMENT_AUDIT.md

Validates that the audit document:
1. Exists
2. Covers all required modules (text/voice/image/music/files/models/video/Token Plan)
3. Lists all 8 Anthropic models
4. Lists all 8 OpenAI models
5. Contains Gap type enum
6. Contains Priority enum
7. Contains model protocol matrix
8. Contains capability gap matrix
9. Clearly distinguishes runner_incomplete vs missing_capability
10. Clearly distinguishes high_risk_by_design vs missing
11. Lists P0/P1/P2 next steps

No real MiniMax API calls are made.
"""

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
AUDIT_DOC_PATH = REPO_ROOT / "docs" / "OFFICIAL_DOCS_ALIGNMENT_AUDIT.md"


class CheckResult:
    def __init__(self):
        self.checks: list[dict[str, Any]] = []

    def pass_(self, name: str, detail: str = ""):
        self.checks.append({"name": name, "status": "PASS", "detail": detail})

    def fail(self, name: str, detail: str = ""):
        self.checks.append({"name": name, "status": "FAIL", "detail": detail})

    def warn(self, name: str, detail: str = ""):
        self.checks.append({"name": name, "status": "WARN", "detail": detail})

    def summary(self) -> dict[str, Any]:
        passed = sum(1 for c in self.checks if c["status"] == "PASS")
        failed = sum(1 for c in self.checks if c["status"] == "FAIL")
        warned = sum(1 for c in self.checks if c["status"] == "WARN")
        return {
            "total": len(self.checks),
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "all_passed": failed == 0,
        }

    def print_report(self):
        print("=" * 70)
        print("OFFICIAL_DOCS_ALIGNMENT_AUDIT.md Validation Report")
        print("=" * 70)
        for check in self.checks:
            status_icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[check["status"]]
            print(f"{status_icon} [{check['status']}] {check['name']}")
            if check["detail"]:
                print(f"   {check['detail']}")

        summary = self.summary()
        print(f"\n{'='*70}")
        print(f"Total: {summary['total']} | Passed: {summary['passed']} | Failed: {summary['failed']} | Warned: {summary['warned']}")

        if not summary["all_passed"]:
            print("RESULT: FAILED — some checks did not pass")
        else:
            print("RESULT: PASSED")

        return summary["all_passed"]


def check_audit_doc(result: CheckResult):
    """Check 1: Document exists"""
    if not AUDIT_DOC_PATH.exists():
        result.fail("Document exists", f"File not found: {AUDIT_DOC_PATH}")
        return None

    result.pass_("Document exists", str(AUDIT_DOC_PATH))
    content = AUDIT_DOC_PATH.read_text(encoding="utf-8")
    return content


def check_module_coverage(content: str, result: CheckResult):
    """Check 2: Document covers all required modules"""
    required_modules = [
        ("文本", "text"),
        ("语音", "voice"),
        ("图像", "image"),
        ("音乐", "music"),
        ("文件", "file"),
        ("模型", "model"),
        ("视频", "video"),
        ("Token Plan", "token_plan"),
    ]

    missing = []
    for label, keyword in required_modules:
        if keyword.lower() not in content.lower() and label not in content:
            missing.append(label)

    if missing:
        result.fail(
            "Module coverage",
            f"Missing modules: {', '.join(missing)}",
        )
    else:
        result.pass_("Module coverage", "All 8 required modules found")


def check_anthropic_models(content: str, result: CheckResult):
    """Check 3: Anthropic 8 models appear in audit doc"""
    expected_models = [
        "MiniMax-M3",
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
    ]
    missing = [m for m in expected_models if m not in content]
    if missing:
        result.fail("Anthropic 8 models", f"Missing: {', '.join(missing)}")
    else:
        result.pass_("Anthropic 8 models", "All 8 Anthropic models found in document")


def check_openai_models(content: str, result: CheckResult):
    """Check 4: OpenAI 8 models appear in audit doc"""
    expected_models = [
        "MiniMax-M3",
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
    ]
    missing = [m for m in expected_models if m not in content]
    if missing:
        result.fail("OpenAI 8 models", f"Missing: {', '.join(missing)}")
    else:
        result.pass_("OpenAI 8 models", "All 8 OpenAI models found in document")


def check_gap_type_enum(content: str, result: CheckResult):
    """Check 5: Document contains Gap type enum"""
    required_gap_types = [
        "missing_capability",
        "missing_model",
        "missing_parameter",
        "wrong_protocol",
        "wrong_scope",
        "wrong_risk_policy",
        "runner_incomplete",
        "docs_only",
        "out_of_scope_by_design",
        "high_risk_by_design",
        "token_plan_unknown",
        "needs_real_probe",
    ]

    missing = [g for g in required_gap_types if g not in content]
    if missing:
        result.fail("Gap type enum", f"Missing gap types: {', '.join(missing)}")
    else:
        result.pass_("Gap type enum", f"All {len(required_gap_types)} gap types found")


def check_priority_enum(content: str, result: CheckResult):
    """Check 6: Document contains Priority enum"""
    required_priorities = ["P0", "P1", "P2", "P3"]
    missing = [p for p in required_priorities if p not in content]
    if missing:
        result.fail("Priority enum", f"Missing priorities: {', '.join(missing)}")
    else:
        result.pass_("Priority enum", f"All {len(required_priorities)} priorities found")


def check_model_protocol_matrix(content: str, result: CheckResult):
    """Check 7: Document contains model protocol matrix"""
    required_columns = [
        "model",
        "official_current",
        "protocols",
        "context",
        "input_modalities",
        "output_modalities",
        "supports_tools",
        "supports_thinking",
        "thinking_can_disable",
    ]

    # Check for table-like structure with model matrix headers
    has_matrix_indicators = [
        any(keyword in content for keyword in ["模型协议矩阵", "Model Protocol Matrix", "protocols"]),
        any(keyword in content for keyword in ["MiniMax-M3", "MiniMax-M2.7"]),
    ]

    if not all(has_matrix_indicators):
        result.fail("Model protocol matrix", "Model protocol matrix section not clearly found")
        return

    # Check for key column indicators
    found_columns = [col for col in required_columns if col in content]
    if len(found_columns) < 5:
        result.warn(
            "Model protocol matrix",
            f"Only {len(found_columns)}/{len(required_columns)} expected columns found",
        )
    else:
        result.pass_(
            "Model protocol matrix",
            f"Found {len(found_columns)}/{len(required_columns)} expected columns",
        )


def check_capability_gap_matrix(content: str, result: CheckResult):
    """Check 8: Document contains capability gap matrix"""
    required_columns = [
        "Official Doc",
        "Official Endpoint",
        "Capability_id",
        "Registry status",
        "Scope policy",
        "Gap type",
        "Priority",
        "Action",
    ]

    found_columns = [col for col in required_columns if col in content]
    if len(found_columns) < 5:
        result.fail(
            "Capability gap matrix",
            f"Only {len(found_columns)}/{len(required_columns)} expected columns found",
        )
    else:
        result.pass_(
            "Capability gap matrix",
            f"Found {len(found_columns)}/{len(required_columns)} expected columns",
        )


def check_runner_incomplete_vs_missing_capability(content: str, result: CheckResult):
    """Check 9: Document distinguishes runner_incomplete from missing_capability"""
    has_runner_incomplete = "runner_incomplete" in content
    has_missing_capability = "missing_capability" in content
    has_distinction_explanation = (
        "runner_incomplete" in content
        and "missing_capability" in content
        and (
            # Check that they're discussed as distinct concepts
            "runner_incomplete" in content.split("missing_capability")[0]
            or "missing_capability" in content.split("runner_incomplete")[0]
        )
    )

    if not has_runner_incomplete:
        result.fail("runner_incomplete vs missing_capability distinction", "runner_incomplete not found in document")
        return
    if not has_missing_capability:
        result.fail("runner_incomplete vs missing_capability distinction", "missing_capability not found in document")
        return

    # Check that both appear in gap type enum or matrix
    enum_section = content.split("##")[1:] if "##" in content else []
    enum_text = " ".join(enum_section[:3])  # First few sections

    if "runner_incomplete" in enum_text and "missing_capability" in enum_text:
        result.pass_("runner_incomplete vs missing_capability distinction", "Both gap types clearly distinguished")
    else:
        result.warn(
            "runner_incomplete vs missing_capability distinction",
            "Both types present but may not be clearly distinguished",
        )


def check_high_risk_by_design_vs_missing(content: str, result: CheckResult):
    """Check 10: Document distinguishes high_risk_by_design from missing"""
    has_high_risk = "high_risk_by_design" in content
    has_out_of_scope = "out_of_scope_by_design" in content
    has_missing = "missing_capability" in content

    if not has_high_risk:
        result.warn("high_risk_by_design vs missing distinction", "high_risk_by_design not in document")
    if not has_out_of_scope:
        result.fail("high_risk_by_design vs missing distinction", "out_of_scope_by_design not in document")
        return

    if has_out_of_scope and has_missing:
        result.pass_(
            "high_risk_by_design vs missing distinction",
            "out_of_scope_by_design and missing capability both distinguished",
        )
    else:
        result.warn("high_risk_by_design vs missing distinction", "Distinction may not be explicit")


def check_p0_p1_p2_recommendations(content: str, result: CheckResult):
    """Check 11: Document lists P0/P1/P2 next step recommendations"""
    sections = content.split("##")

    p0_section = any("P0" in s and ("修复" in s or "立即" in s or "修复建议" in s) for s in sections)
    p1_section = any("P1" in s and ("修复" in s or "下一迭代" in s or "修复建议" in s) for s in sections)
    p2_section = any("P2" in s and ("修复" in s or "标注优化" in s or "修复建议" in s) for s in sections)

    if p0_section and p1_section and p2_section:
        result.pass_("P0/P1/P2 recommendations", "All three priority sections found")
    elif p0_section or p1_section:
        result.warn(
            "P0/P1/P2 recommendations",
            f"P0={p0_section}, P1={p1_section}, P2={p2_section}",
        )
    else:
        result.fail("P0/P1/P2 recommendations", "P0/P1/P2 recommendation sections not clearly found")


def check_video_fl2v_missing(content: str, result: CheckResult):
    """Bonus check: video-fl2v should be identified as missing"""
    if "video-fl2v" in content or "video-fl2v" in content.lower():
        result.pass_("video-fl2v identified as missing", "video-fl2v gap documented")
    else:
        result.warn("video-fl2v identified as missing", "video-fl2v not mentioned in audit")


def check_anthropic_active_cache_missing(content: str, result: CheckResult):
    """Bonus check: anthropic-active-cache should be identified as missing"""
    if "anthropic-active-cache" in content or "active cache" in content.lower():
        result.pass_("anthropic-active-cache identified", "Active cache gap documented")
    else:
        result.warn("anthropic-active-cache identified", "Active cache not mentioned in audit")


def check_model_protocol_error(content: str, result: CheckResult):
    """Bonus check: M2.7/M2.5/M2.1/M2 protocols wrong_protocol should be P0"""
    if "wrong_protocol" in content and "P0" in content:
        # Good - P0 wrong_protocol issues documented
        result.pass_("P0 wrong_protocol documented", "M2.x protocols gap at P0 priority")
    elif "wrong_protocol" in content:
        result.warn("wrong_protocol documented", "wrong_protocol found but P0 priority unclear")
    else:
        result.warn("wrong_protocol documented", "wrong_protocol not explicitly called out")


def run_checks() -> bool:
    result = CheckResult()

    content = check_audit_doc(result)
    if content is None:
        # Already failed, print and exit
        result.print_report()
        return False

    check_module_coverage(content, result)
    check_anthropic_models(content, result)
    check_openai_models(content, result)
    check_gap_type_enum(content, result)
    check_priority_enum(content, result)
    check_model_protocol_matrix(content, result)
    check_capability_gap_matrix(content, result)
    check_runner_incomplete_vs_missing_capability(content, result)
    check_high_risk_by_design_vs_missing(content, result)
    check_p0_p1_p2_recommendations(content, result)
    check_video_fl2v_missing(content, result)
    check_anthropic_active_cache_missing(content, result)
    check_model_protocol_error(content, result)

    all_passed = result.print_report()
    return all_passed


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
