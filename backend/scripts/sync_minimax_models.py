#!/usr/bin/env python3
"""
MiniMax 模型发现脚本 —— sync_minimax_models.py

功能：
1. 读取 .env 中的 MINIMAX_API_KEY
2. 请求 OpenAI 模型列表（GET /v1/models）
3. 请求 Anthropic 模型列表（GET /anthropic/v1/models）
4. 将返回结果保存到 backend/runtime/model_discovery/
5. 生成对比报告（official_current / local_configured / live_available）
6. 生成 Markdown 报告 docs/MINIMAX_MODEL_SUPPORT_REPORT.md

所有日志必须脱敏，不打印完整 Key。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

# ── 项目路径 ──────────────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent
RUNTIME_DIR = BACKEND / "runtime" / "model_discovery"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BACKEND.parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ── Core 客户端（minimax_core）─────────────────────────────────────────────────
from app.minimax_core.clients.openai import MiniMaxOpenAIClient
from app.minimax_core.clients.anthropic import MiniMaxAnthropicClient


def _redact(key: str) -> str:
    """脱敏：只显示前后少量字符。"""
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def _load_env() -> dict:
    env_path = BACKEND / ".env"
    if not env_path.exists():
        print("ERROR: backend/.env 不存在，请复制 .env.example 为 .env 并填入真实值。", file=sys.stderr)
        sys.exit(1)
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _load_local_models() -> list[dict]:
    models_path = BACKEND / "config" / "models.yaml"
    with models_path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("models", [])


def _call_openai_models(api_key: str) -> dict:
    """GET /v1/models — OpenAI 兼容端点。"""
    client = MiniMaxOpenAIClient(api_key=api_key, timeout=30)
    return client.list_models()


def _call_anthropic_models(api_key: str) -> dict:
    """GET /anthropic/v1/models — Anthropic 兼容端点。"""
    client = MiniMaxAnthropicClient(api_key=api_key, timeout=30)
    return client.list_models()


def _extract_model_ids(openai_resp: dict, anthropic_resp: dict) -> tuple[set[str], set[str], set[str]]:
    """从 API 响应中提取模型 ID 集合。

    MiniMax 的 Anthropic 端点实际返回 OpenAI 兼容格式（data[]），
    而非标准 Anthropic 格式（models[]），因此两个端点都从 data 取 id。
    """
    openai_ids = set()
    if "data" in openai_resp:
        for m in openai_resp["data"]:
            if "id" in m:
                openai_ids.add(m["id"])

    anthropic_ids = set()
    # MiniMax Anthropic 端点返回 OpenAI 兼容格式 {data: [...]} 而非 {models: [...]}
    if "data" in anthropic_resp:
        for m in anthropic_resp["data"]:
            if "id" in m:
                anthropic_ids.add(m["id"])
    elif "models" in anthropic_resp:
        for m in anthropic_resp["models"]:
            if "name" in m:
                anthropic_ids.add(m["name"])

    # live_available = union（两个端点返回的并集）
    live_ids = openai_ids | anthropic_ids
    return openai_ids, anthropic_ids, live_ids


def _build_report(
    local_models: list[dict],
    openai_resp: dict,
    anthropic_resp: dict,
    openai_ids: set[str],
    anthropic_ids: set[str],
    live_ids: set[str],
    api_key: str,
    base_url: str,
) -> dict:
    local_ids = {m["id"] for m in local_models}

    official_current_ids = {m["id"] for m in local_models if m.get("official_current", False)}
    legacy_ids = {m["id"] for m in local_models if m.get("tier") in ("legacy", "deprecated")}

    missing_in_local = live_ids - local_ids
    local_deprecated_or_unknown = local_ids - official_current_ids - live_ids
    local_current_not_live = official_current_ids - live_ids

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_key_tail": _redact(api_key),
        "base_url": base_url,
        "summary": {
            "official_current_models": len(official_current_ids),
            "live_available_models": len(live_ids),
            "local_configured_models": len(local_ids),
            "missing_in_local": sorted(missing_in_local),
            "local_deprecated_or_unknown": sorted(local_deprecated_or_unknown),
            "local_current_not_in_live": sorted(local_current_not_live),
        },
        "openai_live_ids": sorted(openai_ids),
        "anthropic_live_ids": sorted(anthropic_ids),
        "official_current_ids": sorted(official_current_ids),
        "local_all_ids": sorted(local_ids),
        "legacy_local_ids": sorted(legacy_ids),
        "openai_response": openai_resp,
        "anthropic_response": anthropic_resp,
    }
    return report


def _save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] 保存 {path.relative_to(BACKEND)}")


def _generate_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# MiniMax 模型支持报告",
        "",
        f"> 生成时间：{report['generated_at']}",
        f"> API Key：`{report['api_key_tail']}`",
        f"> Base URL：`{report['base_url']}`",
        "",
        "## 概览",
        "",
        f"| 维度 | 数量 |",
        f"|---|---|",
        f"| 官方当前模型（official_current） | {s['official_current_models']} |",
        f"| 实际可用模型（live） | {s['live_available_models']} |",
        f"| 本地配置模型（local） | {s['local_configured_models']} |",
        f"| 本地缺失（missing_in_local） | {len(s['missing_in_local'])} |",
        f"| 本地历史/未知（deprecated/unknown） | {len(s['local_deprecated_or_unknown'])} |",
        "",
    ]

    if s["missing_in_local"]:
        lines += [
            "## 本地缺失模型（live 返回但 local 未配置）",
            "",
            "以下模型由真实 API 返回，但 `models.yaml` 中未配置：",
            "",
        ]
        for mid in s["missing_in_local"]:
            lines.append(f"- `{mid}`")
        lines.append("")

    if s["local_deprecated_or_unknown"]:
        lines += [
            "## 本地历史/未知模型（local 有但非 official_current 且不在 live 中）",
            "",
        ]
        for mid in s["local_deprecated_or_unknown"]:
            lines.append(f"- `{mid}`")
        lines.append("")

    if s["local_current_not_in_live"]:
        lines += [
            "## 本地当前模型未在 live 中返回",
            "",
            "以下模型在 `models.yaml` 标记 `official_current: true`，但本次 live 查询未返回。"
            "可能是端点路由、权限或 API 版本差异：",
            "",
        ]
        for mid in s["local_current_not_in_live"]:
            lines.append(f"- `{mid}`")
        lines.append("")

    lines += [
        "## OpenAI 协议 live 模型",
        "",
        f"数量：{len(report['openai_live_ids'])}",
    ]
    for mid in report["openai_live_ids"]:
        lines.append(f"- `{mid}`")

    lines += [
        "",
        "## Anthropic 协议 live 模型",
        "",
        f"数量：{len(report['anthropic_live_ids'])}",
    ]
    for mid in report["anthropic_live_ids"]:
        lines.append(f"- `{mid}`")

    lines += [
        "",
        "## 官方当前模型（official_current: true）",
        "",
    ]
    for mid in report["official_current_ids"]:
        lines.append(f"- `{mid}`")

    lines += [
        "",
        "## 本地所有模型（包含历史）",
        "",
    ]
    for mid in report["local_all_ids"]:
        lines.append(f"- `{mid}`")

    lines += [
        "",
        "---",
        "*此报告由 `backend/scripts/sync_minimax_models.py` 自动生成*",
    ]
    return "\n".join(lines)


def main() -> None:
    print("═" * 60)
    print("MiniMax 模型发现脚本")
    print("═" * 60)

    env = _load_env()
    api_key = env.get("MINIMAX_API_KEY", "")
    base_url = env.get("MINIMAX_BASE_URL", "https://api.minimaxi.com").rstrip("/")

    if not api_key:
        print("ERROR: MINIMAX_API_KEY 未配置", file=sys.stderr)
        sys.exit(1)

    print(f"API Key: {_redact(api_key)}")
    print(f"Base URL: {base_url}")
    print()

    # 加载本地配置
    local_models = _load_local_models()
    print(f"本地配置模型数：{len(local_models)}")

    # 调用 live API
    print("\n调用 OpenAI 模型列表...")
    try:
        openai_resp = _call_openai_models(api_key)
    except Exception as exc:
        print(f"  [FAIL] 失败：{exc}")
        openai_resp = {"error": str(exc)}

    print("调用 Anthropic 模型列表...")
    try:
        anthropic_resp = _call_anthropic_models(api_key)
    except Exception as exc:
        print(f"  [FAIL] 失败：{exc}")
        anthropic_resp = {"error": str(exc)}

    openai_ids, anthropic_ids, live_ids = _extract_model_ids(openai_resp, anthropic_resp)

    print(f"\nOpenAI 协议返回模型：{len(openai_ids)}")
    print(f"Anthropic 协议返回模型：{len(anthropic_ids)}")
    print(f"合并 live 模型：{len(live_ids)}")

    # 构建报告
    report = _build_report(
        local_models, openai_resp, anthropic_resp,
        openai_ids, anthropic_ids, live_ids,
        api_key, base_url,
    )

    # 保存 JSON
    print("\n保存 JSON 文件...")
    _save_json(report, RUNTIME_DIR / "model_discovery_report.json")
    _save_json(openai_resp, RUNTIME_DIR / "openai_models.json")
    _save_json(anthropic_resp, RUNTIME_DIR / "anthropic_models.json")

    # 生成 Markdown 报告
    md = _generate_markdown(report)
    md_path = DOCS_DIR / "MINIMAX_MODEL_SUPPORT_REPORT.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  [OK] 保存 {md_path.relative_to(BACKEND.parent)}")

    # 摘要
    s = report["summary"]
    print("\n" + "═" * 60)
    print("摘要")
    print("═" * 60)
    print(f"  官方当前模型：{s['official_current_models']}")
    print(f"  实际可用模型：{s['live_available_models']}")
    print(f"  本地配置模型：{s['local_configured_models']}")
    print(f"  本地缺失：{len(s['missing_in_local'])} → {s['missing_in_local']}")
    print(f"  本地历史/未知：{len(s['local_deprecated_or_unknown'])}")
    print("═" * 60)


if __name__ == "__main__":
    main()
