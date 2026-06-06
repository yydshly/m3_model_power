"""report_scope_gap.py

输出 Token Plan 范围统计：
  - in_scope / warning_only / out_of_scope 各层级能力数量
  - in_scope 中已验收 / 未验收明细（基于所有历史 probe 结果）
  - 完成率

聚合所有历史 probe 结果，不依赖单一 latest.json：
  - capability_verification/latest.json（safe 级别最新运行）
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


def _load_from_latest_json() -> dict[str, dict]:
    """从 capability_verification/latest.json 读取 safe 级别结果。"""
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
    # lyrics-gen 在 section 5.9b 或 6.2 中标记为 medium 验收完成 / capability_level_verified
    # 查找 lyrics-gen 条目
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
    """从所有来源聚合已验收能力。返回 {capability_id: info}。"""
    verified = {}

    # 1. latest.json (safe level)
    verified.update(_load_from_latest_json())

    # 2. model_level_probe_report.json (chat/tts-sync/image-t2i/music-gen)
    for cid, info in _load_from_model_level_probe().items():
        if cid not in verified:
            verified[cid] = info

    # 3. tts_ws_probe_report.json (tts-ws)
    for cid, info in _load_from_tts_ws_probe().items():
        if cid not in verified:
            verified[cid] = info

    # 4. Matrix 文档中明确记录的成功状态
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
