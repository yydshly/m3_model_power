"""generate_full_capability_matrix.py

生成全量覆盖矩阵报告：
  - docs/MINIMAX_FULL_CAPABILITY_MATRIX.md
  - backend/runtime/reports/minimax_full_capability_matrix.json

不读取 .env，不调用真实 API，只基于 registry 和已有报告生成矩阵。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND / "runtime" / "reports"
DOCS_DIR = BACKEND.parent / "docs"
sys.path.insert(0, str(BACKEND))

from app.minimax_core.registry.loader import get_model_registry, get_capability_registry


# ── helpers ────────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── 已知 probe 结果（来自已有验收报告）──────────────────────────────
# 键：capability_id，值：(probed_model, result, scope)
# scope: "model_level" = 该能力所有支持模型均已逐项验收
#        "capability_level" = 该能力已验收，但仅测了一个模型，未逐项验证所有模型
KNOWN_PROBE_RESULTS: dict[str, tuple[str | None, str, str]] = {
    # capability_id: (probed_model, result, scope)
    "image-t2i": ("image-01", "success", "capability_level"),
    "lyrics-gen": (None, "success", "not_applicable"),  # requires_model=false
    "music-gen": ("music-2.6", "success", "capability_level"),
    "tts-sync": ("speech-02-turbo", "success", "capability_level"),
}

# chat 模型通过 /v1/models 验证（model_level via models_api）
CHAT_MODEL_PROBE: dict[str, tuple[str, str]] = {
    m: ("live_api", "success") for m in [
        "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5", "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2",
    ]
}

# 从 runtime report 加载最新 probe 结果（如果存在）
def _load_live_probe_results() -> dict[str, dict]:
    """加载 backend/runtime/reports/model_level_probe_report.json。"""
    probe_path = REPORTS_DIR / "model_level_probe_report.json"
    if not probe_path.exists():
        return {}
    try:
        doc = json.loads(probe_path.read_text(encoding="utf-8"))
        # 键："{model_id}|{capability_id}"
        out: dict[str, dict] = {}
        for r in doc.get("results", []):
            key = f"{r['model_id']}|{r['capability_id']}"
            out[key] = r
        return out
    except Exception:
        return {}


# ── 验收状态分层说明（Markdown）─────────────────────────────────────────────────
VERIFICATION_TIER_EXPLANATION = """
## 验收状态分层说明

| 层级 | 状态名 | 含义 |
|---|---|---|
| L1 | `official_current` | 官方当前文档中列出 |
| L2 | `models_api_verified` | 通过 `/v1/models` 或 `/anthropic/v1/models` 发现（仅 chat 模型） |
| L3 | `capability_level_verified` | 能力端点已实测可用，但仅测了一个模型，未逐项验证所有模型 |
| L4 | `model_level_verified` | 具体模型已作为请求中 `model` 参数单独调用成功 |
| — | `not_probed` | 尚未进行任何实测 |
| — | `high_cost_pending` | 成本或风险较高，暂不执行（video / voice-clone / voice-design 等） |
| — | `not_applicable` | 不需要模型（如 lyrics-gen / file-* / models-*） |

**重要说明**：
- `/v1/models` 主要覆盖 chat 模型，speech/image/video/music 不出现于其中，不代表不可用
- `models_api_verified` ≠ `model_level_verified`
- `capability_level_verified` ≠ 所有模型逐项验证
- `high_cost_pending` 能力必须显式确认后才执行（video / voice-clone / voice-design / tts-async / music-cover-prep）
"""


# ── build data structures ───────────────────────────────────────────────────────

def build_model_row(m, live_probe: dict | None = None) -> dict:
    """单个模型的矩阵行数据（含 capability_probe 字段）。"""
    # capability probe 状态判断
    discovery = m.discovery_method
    status = m.discovery_status
    if discovery == "models_api" and status == "available":
        probe_status = "model_level_verified"
        probed_model = m.id
        probe_result = "success"
        probe_scope = "model_level"
        probed_by = "live_api"
    elif discovery == "capability_probe":
        if status == "available":
            probe_status = "model_level_verified"
            probed_model = m.id
            probe_result = "success"
            probe_scope = "model_level"
            probed_by = "capability_probe"
        elif status == "unknown":
            probe_status = "not_probed"
            probed_model = None
            probe_result = None
            probe_scope = "not_probed"
            probed_by = None
        else:
            probe_status = "probe_failed"
            probed_model = m.id
            probe_result = "failure"
            probe_scope = "model_level"
            probed_by = "capability_probe"
    elif discovery == "manual_official":
        probe_status = "not_probed"
        probed_model = None
        probe_result = None
        probe_scope = "not_probed"
        probed_by = None
    else:
        probe_status = "not_applicable"
        probed_model = None
        probe_result = None
        probe_scope = "not_applicable"
        probed_by = None

    # 用 live probe 结果覆盖默认推断
    _probe_status = probe_status
    _probed_by = probed_by
    _probed_model = probed_model
    _probe_scope = probe_scope
    _probe_result = probe_result
    if live_probe and live_probe.get("probe_status") in ("success", "failed"):
        _probe_status = live_probe["probe_status"]
        _probed_by = live_probe.get("probed_by", probed_by)
        _probed_model = live_probe.get("probed_model", probed_model)
        _probe_scope = live_probe.get("probe_scope", probe_scope)
        _probe_result = live_probe.get("probe_result", probe_result)

    return {
        "model_id": m.id,
        "display_name": m.label,
        "family": m.family,
        "tier": m.tier,
        "official_current": m.official_current,
        "subscription_expected": m.subscription_expected,
        "enabled": m.enabled,
        "context_window": m.context,
        "input_modalities": m.input_modalities,
        "output_modalities": m.output_modalities,
        "protocols": m.protocols,
        "capabilities": m.capabilities,
        "supports_tools": m.supports_tools,
        "supports_thinking": m.supports_thinking,
        "thinking_can_disable": m.thinking_can_disable,
        "live_openai_available": True if m.live_available else (False if m.live_available is False else None),
        "live_anthropic_available": True if m.live_available else (False if m.live_available is False else None),
        "cost_level": m.cost_level,
        "discovery_method": m.discovery_method,
        "discovery_status": m.discovery_status,
        "discovery_note": m.discovery_note,
        "note": m.note,
        # capability probe 明细
        "capability_probe_status": _probe_status,
        "probed_by": _probed_by,
        "probed_model": _probed_model,
        "probe_scope": _probe_scope,
        "probe_result": _probe_result,
    }


def build_protocol_row(m) -> dict:
    """单个模型的协议支持矩阵行。"""
    protocols = m.protocols or []
    return {
        "model_id": m.id,
        "openai_chat_supported": "openai" in protocols,
        "openai_chat_verified": m.live_available is True and "openai" in protocols,
        "anthropic_messages_supported": "anthropic" in protocols,
        "anthropic_messages_verified": m.live_available is True and "anthropic" in protocols,
        "responses_supported": "responses" in protocols,
        "responses_verified": m.family == "chat" and m.live_available is True,
        "input_tokens_supported": m.family == "chat",
        "input_tokens_verified": m.family == "chat" and m.live_available is True,
        "tool_use_supported": m.supports_tools,
        "thinking_supported": m.supports_thinking,
        "thinking_can_disable": m.thinking_can_disable,
        "multimodal_input_supported": bool(m.input_modalities) and any(
            mod in (m.input_modalities or []) for mod in ("image", "video")
        ),
    }


def build_capability_row(c, cap_registry) -> dict:
    """单个能力的矩阵行（含 capability_probe 明细）。"""
    models = cap_registry.models_for_capability(c.id)
    supported_ids = [m.id for m in models]
    default = cap_registry.default_model_for_capability(c.id)

    # capability probe 状态判断
    if c.requires_model is False:
        cap_probe_status = "not_applicable"
        probed_by = None
        probed_model = None
        probe_scope = "not_applicable"
        probe_result = None
    elif c.id in KNOWN_PROBE_RESULTS:
        probed_model, probe_result, scope = KNOWN_PROBE_RESULTS[c.id]
        if scope == "model_level":
            cap_probe_status = "model_level_verified"
        else:
            cap_probe_status = "capability_level_verified"
        probed_by = "verification_report"
        probe_scope = scope
    else:
        cap_probe_status = "not_probed"
        probed_by = None
        probed_model = None
        probe_scope = "not_probed"
        probe_result = None

    return {
        "capability_id": c.id,
        "name": c.name,
        "category": c.category,
        "endpoint": c.endpoint,
        "method": c.method,
        "protocol": c.protocol,
        "requires_model": c.requires_model,
        "model_family": c.model_family,
        "protocols": c.protocols,
        "supported_models_count": len(supported_ids),
        "supported_models": supported_ids,
        "default_model": default.id if default else None,
        "is_streaming": c.is_streaming,
        "is_async": c.is_async,
        "requires_upload": c.requires_upload,
        "cost_level": c.cost_level,
        "doc_url": c.doc_url,
        "implementation_status": c.status,
        # capability probe 明细
        "capability_probe_status": cap_probe_status,
        "probed_by": probed_by,
        "probed_model": probed_model,
        "probe_scope": probe_scope,
        "probe_result": probe_result,
    }


def build_model_to_capability_matrix(model_registry, cap_registry) -> dict:
    """每个模型 → 它支持哪些能力。"""
    out: dict[str, list[str]] = {}
    for m in model_registry.all():
        supported: list[str] = []
        for c in cap_registry.all():
            models = cap_registry.models_for_capability(c.id)
            if m.id in [x.id for x in models]:
                supported.append(c.id)
        out[m.id] = sorted(supported)
    return out


def build_gap_matrix(model_registry, cap_registry, live_probe: dict | None = None) -> dict:
    """计算各类缺口。"""
    models = model_registry.all()
    official = {m.id for m in models if m.official_current}

    gap = {
        "official_current_but_missing_in_local": [],
        "local_but_not_official_current": [],
        "official_chat_not_live_openai": [],
        "official_chat_not_live_anthropic": [],
        "capability_without_supported_models": [],
        "requires_model_false_capabilities": [],
        "not_verified_capabilities": [],
        "not_applicable_to_models_api": [],
        "capability_level_not_model_level": [],
        "models_not_individually_probed": [],
    }

    for m in model_registry.official_current():
        if model_registry.by_id(m.id) is None:
            gap["official_current_but_missing_in_local"].append(m.id)

    for m in models:
        if not m.official_current and m.tier not in ("legacy", "deprecated"):
            gap["local_but_not_official_current"].append(m.id)

    for m_id in official:
        m = model_registry.by_id(m_id)
        if m and m.family == "chat" and m.live_available is not True:
            gap["official_chat_not_live_openai"].append(m_id)

    for m_id in official:
        m = model_registry.by_id(m_id)
        if m and m.family == "chat":
            if "anthropic" not in (m.protocols or []):
                gap["official_chat_not_live_anthropic"].append(m_id)

    for c in cap_registry.all():
        models_for_cap = cap_registry.models_for_capability(c.id)
        if not models_for_cap and c.requires_model is True:
            gap["capability_without_supported_models"].append(c.id)

    for c in cap_registry.all():
        if c.requires_model is False:
            gap["requires_model_false_capabilities"].append(c.id)

    for c in cap_registry.all():
        if c.status != "implemented":
            gap["not_verified_capabilities"].append(c.id)

    for c in cap_registry.all():
        if c.category in ("files", "models"):
            gap["not_applicable_to_models_api"].append(c.id)

    # capability_level 但非 model_level
    for c in cap_registry.all():
        if c.id in KNOWN_PROBE_RESULTS:
            _, _, scope = KNOWN_PROBE_RESULTS[c.id]
            if scope == "capability_level":
                gap["capability_level_not_model_level"].append(c.id)

    # 模型未逐项 probe（capability_probe 且 status=unknown）
    for m in models:
        if m.discovery_method == "capability_probe" and m.discovery_status == "unknown":
            gap["models_not_individually_probed"].append(m.id)

    # high_cost_pending（禁止自动执行的能力）
    gap["high_cost_pending"] = [
        "video-t2v", "video-i2v", "video-s2v",
        "voice-clone-do", "voice-design",
        "tts-async", "music-cover-prep",
    ]

    # chat probe 失败
    gap["chat_openai_probe_failed"] = []
    gap["chat_anthropic_probe_failed"] = []
    if live_probe:
        for key, r in live_probe.items():
            if r.get("probe_status") == "failed":
                cap_id = r.get("capability_id", "")
                if cap_id == "chat-openai":
                    gap["chat_openai_probe_failed"].append(r["model_id"])
                elif cap_id == "chat-anthropic":
                    gap["chat_anthropic_probe_failed"].append(r["model_id"])

    return gap


# ── markdown generator ─────────────────────────────────────────────────────────

def render_markdown(data: dict) -> str:
    lines: list[str] = []
    md = lines.append

    md("# MiniMax 全量能力覆盖矩阵")
    md("")
    md(f"> 生成时间：{ts()}")
    md("> 本报告基于本地 registry 配置和已有 probe 结果生成。")
    md("")
    md(VERIFICATION_TIER_EXPLANATION.strip())
    md("")

    # ── 1. Model Inventory Matrix ────────────────────────────────────────────
    md("## 1. Model Inventory Matrix")
    md("")
    md(f"共 {len(data['model_inventory'])} 个模型。")
    md("")

    families = ["chat", "speech", "image", "video", "music"]
    family_labels = {
        "chat": "对话 / LLM",
        "speech": "语音合成",
        "image": "图像",
        "video": "视频",
        "music": "音乐",
    }

    for fam in families:
        rows = [r for r in data["model_inventory"] if r["family"] == fam]
        if not rows:
            continue
        md(f"### {family_labels.get(fam, fam)}")
        md("")
        md("| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |")
        md("|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            live = r["live_openai_available"]
            live_str = "✓" if live is True else ("✗" if live is False else "—")
            official = "✓" if r["official_current"] else "✗"
            sub_expected = "✓" if r["subscription_expected"] else ("✗" if r["subscription_expected"] is False else "?")
            enabled_str = "✓" if r["enabled"] else "✗"
            ctx = f"{r['context_window']:,}" if r["context_window"] else "—"
            input_mods = ",".join(r["input_modalities"]) if r["input_modalities"] else "—"
            protocols = ",".join(r["protocols"]) if r["protocols"] else "—"
            probe = r["capability_probe_status"] or "—"
            md(f"| `{r['model_id']}` | {r['tier']} | {official} | {live_str} | {sub_expected} | {enabled_str} | {ctx} | {input_mods} | {protocols} | {probe} |")
        md("")

    # ── 2. Protocol Support Matrix ───────────────────────────────────────────
    md("## 2. Protocol Support Matrix")
    md("")
    md("| model_id | openai_chat | anthropic_messages | responses | tool_use | thinking | thinking_disable | multimodal_input |")
    md("|---|---|---|---|---|---|---|---|")
    for r in data["protocol_matrix"]:
        md(f"| `{r['model_id']}` | {'✓' if r['openai_chat_supported'] else '—'} | {'✓' if r['anthropic_messages_supported'] else '—'} | {'✓' if r['responses_supported'] else '—'} | {'✓' if r['tool_use_supported'] else '—'} | {'✓' if r['thinking_supported'] else '—'} | {'✓' if r['thinking_can_disable'] else '—'} | {'✓' if r['multimodal_input_supported'] else '—'} |")
    md("")

    # ── 2b. Probe Result Matrix ──────────────────────────────────────────────
    if data.get("probe_results"):
        md("## 2b. Probe Result Matrix")
        md("")
        md("| model_id | capability_id | protocol | probe_scope | probe_status | http_status | latency_ms | output_present | error_type | last_probed_at |")
        md("|---|---|---|---|---|---|---|---|---|---|")
        for r in data["probe_results"]:
            output_p = str(r.get("output_present", "—"))
            http_s = str(r.get("http_status", "—"))
            lat = str(r.get("latency_ms", "—")) if r.get("latency_ms") else "—"
            err_type = r.get("error_type", "—") or "—"
            last_p = r.get("last_probed_at", "—") or "—"
            md(f"| `{r['model_id']}` | `{r['capability_id']}` | {r['protocol']} | {r['probe_scope']} | {r['probe_status']} | {http_s} | {lat} | {output_p} | {err_type} | {last_p} |")
        md("")

    # ── 3. Capability Matrix ─────────────────────────────────────────────────
    md("## 3. Capability Matrix")
    md("")
    md(f"共 {len(data['capability_matrix'])} 个能力。")
    md("")
    md("| capability_id | name | category | requires_model | model_family | cost_level | status | supported_models | default_model | probe_status | probed_model | probe_scope |")
    md("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in data["capability_matrix"]:
        requires_model_str = "无需模型" if not r["requires_model"] else ("✓" if r["requires_model"] else "—")
        supported = r["supported_models"]
        supported_str = ",".join(supported) if supported else "—"
        default = r["default_model"] or "—"
        probe = r["capability_probe_status"] or "—"
        probed = r["probed_model"] if r["probed_model"] else "—"
        scope = r["probe_scope"] or "—"
        md(f"| `{r['capability_id']}` | {r['name']} | {r['category']} | {requires_model_str} | {r['model_family'] or '—'} | {r['cost_level']} | {r['implementation_status']} | {supported_str} | {default} | {probe} | {probed} | {scope} |")
    md("")

    # ── 4. Model-to-Capability Reverse Matrix ───────────────────────────────
    md("## 4. Model-to-Capability Reverse Matrix")
    md("")
    for fam in families:
        fam_ids = [m["model_id"] for m in data["model_inventory"] if m["family"] == fam]
        if not fam_ids:
            continue
        md(f"### {family_labels.get(fam, fam)}")
        md("")
        for mid in fam_ids:
            caps = data["model_to_capability"].get(mid, [])
            if caps:
                md(f"**`{mid}`**: {', '.join(caps)}")
            else:
                md(f"**`{mid}`**: —")
        md("")

    # ── 5. Gap Matrix ───────────────────────────────────────────────────────
    md("## 5. Gap Matrix")
    md("")
    gap = data["gap_matrix"]

    sections = [
        ("5.1 official_current 但本地缺失", "official_current_but_missing_in_local"),
        ("5.2 本地有但非 official_current（不含 legacy/deprecated）", "local_but_not_official_current"),
        ("5.3 官方 chat 模型未在 live OpenAI 中返回", "official_chat_not_live_openai"),
        ("5.4 官方 chat 模型未在 live Anthropic 中返回（或协议不支持）", "official_chat_not_live_anthropic"),
        ("5.5 无支持模型的能力（requires_model=true）", "capability_without_supported_models"),
        ("5.6 无需模型的能力（requires_model=false）", "requires_model_false_capabilities"),
        ("5.7 未验收的能力（status != implemented）", "not_verified_capabilities"),
        ("5.8 不适用于 /v1/models 的能力分类（file-*, models-*）", "not_applicable_to_models_api"),
        ("5.9 能力已验收但仅 capability_level（非 model_level）", "capability_level_not_model_level"),
        ("5.10 模型未逐项 probe（capability_probe 且 status=unknown）", "models_not_individually_probed"),
        ("5.11 高成本暂缓（video / voice-clone / voice-design / tts-async / music-cover-prep）", "high_cost_pending"),
        ("5.12 chat-openai 模型级 probe 失败", "chat_openai_probe_failed"),
        ("5.13 chat-anthropic 模型级 probe 失败", "chat_anthropic_probe_failed"),
    ]

    for title, key in sections:
        md(f"### {title}")
        items = gap.get(key, [])
        if items:
            for x in items:
                md(f"- `{x}`")
        else:
            md("（无）")
        md("")

    # ── 6. Summary Statistics ───────────────────────────────────────────────
    md("## 6. Summary Statistics")
    md("")
    stats = data["summary"]
    md("| 维度 | 数量 |")
    md("|---|---|")
    md(f"| 官方当前模型总数 | {stats['official_current_total']} |")
    md(f"| 本地配置模型总数 | {stats['local_total']} |")
    md(f"| live 可用 chat 模型数 | {stats['live_chat_models']} |")
    md(f"| music 模型总数（含变体） | {stats['music_models_total']} |")
    md(f"| 已实测（非 legacy/deprecated）模型数 | {stats['verified_non_legacy']} |")
    md(f"| 未实测 official_current 模型数 | {stats['unverified_official_current']} |")
    md(f"| capability_probe 待验收模型数 | {stats['capability_probe_pending']} |")
    md(f"| capability_level 验收能力数 | {stats['capability_level_verified_capabilities']} |")
    md(f"| model_level 已验收 chat 模型数（/v1/models） | {stats['model_level_verified_models']} |")
    md(f"| model_level probe 成功（本次） | {stats['model_level_probe_success']} |")
    md(f"| model_level probe 失败（本次） | {stats['model_level_probe_failed']} |")
    md(f"| 能力总数 | {stats['capabilities_total']} |")
    md(f"| requires_model=false 能力数 | {stats['requires_model_false_count']} |")
    md(f"| file-*/models-* 能力数 | {stats['files_models_capabilities']} |")
    md("")

    md("---")
    md(f"*本报告由 `backend/scripts/generate_full_capability_matrix.py` 自动生成*")

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    model_registry = get_model_registry()
    cap_registry = get_capability_registry()
    models = model_registry.all()
    caps = cap_registry.all()

    # 加载 live probe 结果
    live_probe = _load_live_probe_results()

    # 构建 probe 结果列表（用于 Probe Result Matrix）
    probe_results = list(live_probe.values())

    model_inventory = [build_model_row(m, live_probe.get(f"{m.id}|{c.id}"))
                       for m in models
                       for c in cap_registry.all()
                       if f"{m.id}|{c.id}" in live_probe]
    # 没有 live probe 的模型各一行（去重）
    probed_model_ids = {r["model_id"] for r in model_inventory}
    for m in models:
        if m.id not in probed_model_ids:
            model_inventory.append(build_model_row(m, None))
    # 全量按 model_id 去重（已 probe 的模型只留一行，取最新 probe）
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for r in reversed(model_inventory):
        if r["model_id"] not in seen_ids:
            seen_ids.add(r["model_id"])
            deduped.append(r)
    model_inventory = list(reversed(deduped))

    protocol_matrix = [build_protocol_row(m) for m in models if m.family == "chat"]
    capability_matrix = [build_capability_row(c, cap_registry) for c in caps]
    model_to_capability = build_model_to_capability_matrix(model_registry, cap_registry)
    gap_matrix = build_gap_matrix(model_registry, cap_registry, live_probe)

    official_ids = {m.id for m in models if m.official_current}
    non_legacy = [m for m in models if m.tier not in ("legacy", "deprecated")]

    # capability probe stats
    cap_level = sum(1 for r in capability_matrix if r["capability_probe_status"] == "capability_level_verified")
    # model_level: chat models verified via /v1/models API
    model_level_verified_models = len([m for m in models if m.discovery_method == "models_api" and m.discovery_status == "available"])
    # live probe results
    live_probe_success = sum(1 for r in probe_results if r.get("probe_status") == "success")
    live_probe_failed = sum(1 for r in probe_results if r.get("probe_status") == "failed")

    summary = {
        "official_current_total": len(official_ids),
        "local_total": len(models),
        "live_chat_models": len([m for m in models if m.family == "chat" and m.live_available is True]),
        "music_models_total": len([m for m in models if m.family == "music"]),
        "verified_non_legacy": len([m for m in non_legacy if m.live_available is True or m.discovery_status == "available"]),
        "unverified_official_current": len([m for m in models if m.official_current and m.live_available is not True and m.tier not in ("legacy", "deprecated")]),
        "capability_probe_pending": len([m for m in models if m.discovery_method == "capability_probe" and m.discovery_status == "unknown"]),
        "capability_level_verified_capabilities": cap_level,
        "model_level_verified_models": model_level_verified_models,
        "model_level_probe_success": live_probe_success,
        "model_level_probe_failed": live_probe_failed,
        "capabilities_total": len(caps),
        "requires_model_false_count": len([c for c in caps if c.requires_model is False]),
        "files_models_capabilities": len([c for c in caps if c.category in ("files", "models")]),
    }

    data = {
        "generated_at": ts(),
        "model_inventory": model_inventory,
        "protocol_matrix": protocol_matrix,
        "capability_matrix": capability_matrix,
        "model_to_capability": model_to_capability,
        "gap_matrix": gap_matrix,
        "probe_results": probe_results,
        "summary": summary,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "minimax_full_capability_matrix.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON report → {json_path}")

    md_content = render_markdown(data)
    md_path = DOCS_DIR / "MINIMAX_FULL_CAPABILITY_MATRIX.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown report → {md_path}")


if __name__ == "__main__":
    main()
