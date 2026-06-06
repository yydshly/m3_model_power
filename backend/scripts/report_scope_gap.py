"""report_scope_gap.py

输出 Token Plan 范围统计：
  - in_scope / warning_only / out_of_scope 各层级能力数量
  - in_scope 中已验收 / 未验收明细（基于所有历史 probe 结果）
  - 完成率

聚合所有历史 probe 结果，不依赖单一 latest.json：
  - capability_verification/latest.json（最新运行结果）
  - docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md（历次验收报告，综合判断）
  - reports/tts_ws_probe_report.json（tts-ws WebSocket probe）
  - reports/model_level_probe_report.json（chat/tts-sync/image-t2i/music-gen model level）
  - Matrix 文档中明确记录的成功状态（tts-async full_async_flow, lyrics-gen medium 等）

不读取 .env，不调用真实 API。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.minimax_core.registry.loader import get_capability_registry


def _load_from_aggregate_index() -> dict[str, dict]:
    """从累计验收索引读取所有已验证能力（优先读取 docs 版本）。

    读取优先级：
      1. docs/MINIMAX_CAPABILITY_VERIFICATION_INDEX.json（脱敏快照，可提交 Git）
      2. backend/runtime/capability_verification/all_verified.json（本地完整版）

    如果索引文件不存在，退回到 latest.json。
    """
    docs_index = BACKEND.parent / "docs" / "MINIMAX_CAPABILITY_VERIFICATION_INDEX.json"
    runtime_index = BACKEND / "runtime" / "capability_verification" / "all_verified.json"

    index_path = docs_index if docs_index.exists() else (runtime_index if runtime_index.exists() else None)
    if index_path is None:
        return _load_from_latest_json()

    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return _load_from_latest_json()

    out = {}
    for cid, rec in data.get("capabilities", {}).items():
        if rec.get("verified"):
            out[cid] = {
                "source": f"aggregate_index ({index_path.name})",
                "status": rec.get("best_status", "success"),
                "level": rec.get("evidence", {}).get("level", "safe"),
                "best_status": rec.get("best_status"),
                "last_success": rec.get("last_success"),
            }
    return out


def _load_from_latest_json() -> dict[str, dict]:
    """从 capability_verification/latest.json 读取最新结果。

    注意：latest.json 每次运行会被整体覆盖，不代表全量历史。
    仅在 aggregate index 不存在时使用。
    """
    vfile = BACKEND / "runtime" / "capability_verification" / "latest.json"
    if not vfile.exists():
        return {}
    with open(vfile, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("results", []):
        cid = r.get("capability_id")
        if cid and r.get("status") == "success":
            out[cid] = {"source": "latest.json", "status": "success", "level": r.get("level", "safe")}
    return out


def _load_from_verification_report() -> dict[str, dict]:
    """从 docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md 读取历次 success 记录。

    解析 markdown 表格中 status=success 的能力，这些是经过实际 API 验证的。
    注意：Verification Report 只记录最近一次 run 的结果，需要结合历史判断。
    """
    report_file = BACKEND.parent / "docs" / "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md"
    if not report_file.exists():
        return {}
    content = report_file.read_text(encoding="utf-8")

    # 解析 markdown 表格：| capability_id | status | http | latency | ...
    # 格式：| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
    out = {}
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # 跳过表头和分隔符行
        if "能力 ID" in line or "---|---|" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            # parts[0] 是空（对齐）, parts[1] 是 capability ID, parts[2] 是 status
            cap_id = parts[1].strip("` ")
            status = parts[2].strip()
            if cap_id and status == "success":
                out[cap_id] = {"source": "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md", "status": "success"}
    return out


def _load_from_model_level_probe() -> dict[str, dict]:
    """从 reports/model_level_probe_report.json 读取 model-level probe 结果。"""
    mfile = BACKEND / "runtime" / "reports" / "model_level_probe_report.json"
    if not mfile.exists():
        return {}
    with open(mfile, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("results", []):
        cid = r.get("capability_id")
        ps = r.get("probe_status")
        if cid and ps == "success" and cid not in out:
            out[cid] = {"source": "model_level_probe_report.json", "status": "success", "probe_status": ps}
    return out


def _load_from_tts_ws_probe() -> dict[str, dict]:
    """从 reports/tts_ws_probe_report.json 读取 tts-ws WebSocket probe 结果。"""
    tfile = BACKEND / "runtime" / "reports" / "tts_ws_probe_report.json"
    if not tfile.exists():
        return {}
    with open(tfile, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("status") == "success":
        return {"tts-ws": {"source": "tts_ws_probe_report.json", "status": "success", "model": data.get("model")}}
    return {}


def _check_matrix_doc_for_lyrics_gen() -> bool:
    """从 Matrix 文档检查 lyrics-gen 是否已验收。"""
    doc = BACKEND.parent / "docs" / "MINIMAX_FULL_CAPABILITY_MATRIX.md"
    if not doc.exists():
        return False
    content = doc.read_text(encoding="utf-8")
    return bool(
        re.search(r"`lyrics-gen`.*?(?:medium.?验收完成|capability_level_verified|success)", content, re.DOTALL)
        or re.search(r"lyrics-gen.*?验收完成", content)
    )


def _check_matrix_doc_for_tts_async() -> bool:
    """从 Matrix 文档检查 tts-async 是否已通过 full_async_flow 验收。"""
    doc = BACKEND.parent / "docs" / "MINIMAX_FULL_CAPABILITY_MATRIX.md"
    if not doc.exists():
        return False
    content = doc.read_text(encoding="utf-8")
    return bool(
        re.search(r"`tts-async`.*?full_async_flow_verified", content)
        or re.search(r"tts-async.*?全链路.*?成功", content)
    )


def _aggregate_verified() -> dict[str, dict]:
    """从所有来源聚合已验收能力。返回 {capability_id: info}。

    读取优先级：
      1. aggregate_index（累计索引，primary 权威来源）
      2. Verification Report markdown（备用）
      3. latest.json（备用）
      4. model_level_probe_report.json（备用）
      5. tts_ws_probe_report.json（备用）
      6. Matrix 文档（lyrics-gen, tts-async 备用）
    """
    verified = {}

    # 1. Aggregate index（primary — 从 docs 或 runtime 读取）
    for cid, info in _load_from_aggregate_index().items():
        if cid not in verified:
            verified[cid] = info

    # 2. Verification Report markdown（补充不在索引中的记录）
    for cid, info in _load_from_verification_report().items():
        if cid not in verified:
            verified[cid] = info

    # 3. latest.json（补充不在索引中的记录）
    for cid, info in _load_from_latest_json().items():
        if cid not in verified:
            verified[cid] = info

    # 4. model_level_probe_report.json（补充）
    for cid, info in _load_from_model_level_probe().items():
        if cid not in verified:
            verified[cid] = info

    # 5. tts_ws_probe_report.json（补充）
    for cid, info in _load_from_tts_ws_probe().items():
        if cid not in verified:
            verified[cid] = info

    # 6. Matrix 文档中明确记录的成功状态（tts-async, lyrics-gen 备用）
    if _check_matrix_doc_for_lyrics_gen() and "lyrics-gen" not in verified:
        verified["lyrics-gen"] = {"source": "MINIMAX_FULL_CAPABILITY_MATRIX.md (section 5.9b/6.2)", "status": "success"}

    if _check_matrix_doc_for_tts_async() and "tts-async" not in verified:
        verified["tts-async"] = {"source": "MINIMAX_FULL_CAPABILITY_MATRIX.md (section 5.9b)", "status": "success"}

    return verified


def main() -> dict:
    caps = get_capability_registry().all()
    verified = _aggregate_verified()

    in_scope = [c for c in caps if c.scope_policy.current_scope == "in_scope"]
    warning = [c for c in caps if c.scope_policy.current_scope == "warning_only"]
    out = [c for c in caps if c.scope_policy.current_scope == "out_of_scope"]

    in_scope_verified_ids = {c.id for c in in_scope if c.id in verified}
    in_scope_unverified = [c for c in in_scope if c.id not in verified]

    in_scope_total = len(in_scope)
    in_scope_verified = len(in_scope_verified_ids)
    in_scope_unverified_count = len(in_scope_unverified)
    completion_rate = (in_scope_verified / in_scope_total * 100) if in_scope_total > 0 else 0

    print("=" * 60)
    print("Token Plan 范围统计报告")
    print("=" * 60)
    print(f"in_scope_total:        {in_scope_total}")
    print(f"in_scope_verified:    {in_scope_verified}")
    print(f"in_scope_unverified:  {in_scope_unverified_count}")
    print(f"warning_only_total:   {len(warning)}")
    print(f"out_of_scope_total:   {len(out)}")
    print(f"完成率:               {completion_rate:.1f}% ({in_scope_verified}/{in_scope_total})")
    print()
    print("聚合数据来源:")
    for cid, info in sorted(verified.items()):
        print(f"  {cid}: {info}")
    print()
    print("in_scope_unverified_ids:")
    for c in sorted(in_scope_unverified, key=lambda x: x.id):
        op = c.operation_policy
        reason = "requires_uploaded_asset" if op.requires_uploaded_asset else "no_probe_record"
        print(f"  - {c.id}: {reason}")
    print()
    print("=" * 60)

    return {
        "in_scope_total": in_scope_total,
        "in_scope_verified": in_scope_verified,
        "in_scope_unverified": in_scope_unverified_count,
        "warning_only_total": len(warning),
        "out_of_scope_total": len(out),
        "in_scope_unverified_ids": sorted([c.id for c in in_scope_unverified]),
        "completion_rate": completion_rate,
        "verified_sources": {cid: info for cid, info in verified.items() if cid in in_scope_verified_ids},
    }


if __name__ == "__main__":
    main()
