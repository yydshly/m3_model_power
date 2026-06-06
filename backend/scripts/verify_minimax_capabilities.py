#!/usr/bin/env python3
"""
MiniMax 能力验收脚本 —— verify_minimax_capabilities.py

验收范围分级：

  Level 1（安全，默认执行）：
    models-openai-list, models-anthropic-list,
    models-openai-retrieve, models-anthropic-retrieve,
    chat-openai (max_tokens=16),
    chat-anthropic (max_tokens=16),
    chat-responses-create (短 input),
    chat-responses-tokens (短 input),
    file-list, voice-list

  Level 2（中等成本，默认不执行，需 --confirm-cost）：
    tts-sync, image-t2i, lyrics-gen, music-gen

  Level 3（高成本/可能计费，默认禁止，需 --confirm-high-cost）：
    voice-clone-do, voice-design,
    video-t2v, video-i2v, video-s2v,
    music-cover-prep, tts-async 长文本

用法：
  python scripts/verify_minimax_capabilities.py --level safe        # 默认
  python scripts/verify_minimax_capabilities.py --level medium --confirm-cost
  python scripts/verify_minimax_capabilities.py --level high --confirm-cost --confirm-high-cost

输出：
  backend/runtime/capability_verification/latest.json
  docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

BACKEND = Path(__file__).resolve().parent.parent

# ── Core 客户端（minimax_core）─────────────────────────────────────────────────
from app.minimax_core.clients.openai import MiniMaxOpenAIClient
from app.minimax_core.clients.anthropic import MiniMaxAnthropicClient
from app.minimax_core.clients.native import MiniMaxNativeClient
from app.minimax_core.clients.files import MiniMaxFilesClient
from app.minimax_core.contracts import AssetRef
from app.minimax_core.invoker import CapabilityInvoker, NotImplementedCapability

# CapabilityInvoker 支持的能力列表（safe + medium）
_INVOKER_SUPPORTED = {
    "chat-openai", "chat-anthropic", "chat-responses-create",
    "chat-responses-tokens", "tts-sync", "image-t2i",
    "lyrics-gen", "music-gen", "file-list", "voice-list",
}
RUNTIME_DIR = BACKEND / "runtime" / "capability_verification"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BACKEND.parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def _redact(key: str) -> str:
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def _load_env() -> dict:
    env_path = BACKEND / ".env"
    if not env_path.exists():
        print("ERROR: backend/.env 不存在", file=sys.stderr)
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


def _load_capabilities() -> list[dict]:
    with (BACKEND / "config" / "capabilities.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("capabilities", [])


def _load_models() -> list[dict]:
    with (BACKEND / "config" / "models.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("models", [])


# ── 能力分级定义 ─────────────────────────────────────────────────────────────

CAPABILITY_GROUPS = {
    "safe": [
        "models-openai-list",
        "models-anthropic-list",
        "models-openai-retrieve",
        "models-anthropic-retrieve",
        "chat-openai",
        "chat-anthropic",
        "chat-responses-create",
        "chat-responses-tokens",
        "file-list",
        "voice-list",
    ],
    "medium": [
        "tts-sync",
        "image-t2i",
        "lyrics-gen",
        "music-gen",
    ],
    "high": [
        "voice-clone-do",
        "voice-design",
        "video-t2v",
        "video-i2v",
        "video-s2v",
        "music-cover-prep",
        "tts-async",
    ],
}


# ── 单个能力验收 ─────────────────────────────────────────────────────────────

def _verify_single(
    cap_id: str,
    api_key: str,
) -> dict:
    """使用 CapabilityInvoker 验收单个能力。"""
    started_at = datetime.now(timezone.utc).isoformat()
    result: dict = {
        "capability_id": cap_id,
        "status": "skipped",
        "level": "safe",
        "http_status": None,
        "model": None,
        "protocol": None,
        "started_at": started_at,
        "ended_at": None,
        "latency_ms": None,
        "error_code": None,
        "error_message": None,
        "response_shape_ok": None,
        "sensitive_data_redacted": True,
        # medium specific
        "output_type": None,
        "asset_saved": False,
        "asset_committed": False,
    }

    # CapabilityInvoker 支持的能力走统一路径
    if cap_id in _INVOKER_SUPPORTED:
        return _verify_via_invoker(cap_id, api_key, started_at, result)

    # 其余能力（models-* / high / video 等）走旧 client 路径
    return _verify_via_client(cap_id, api_key, started_at, result)


# ── CapabilityInvoker 路径 ─────────────────────────────────────────────────

# payload 映射
_INVOKER_PAYLOADS: dict[str, dict] = {
    "chat-openai":            {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16},
    "chat-anthropic":         {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16},
    "chat-responses-create":  {"model": "MiniMax-M3", "input": "Hi"},
    "chat-responses-tokens":  {"model": "MiniMax-M3", "input": "Hi"},
    "tts-sync":               {"model": "speech-02-turbo", "text": "你好，这是 MiniMax 语音能力验收。", "voice_setting": {"voice_id": "female-tianmei"}, "audio_setting": {"sample_rate": 32000, "format": "mp3"}},
    "image-t2i":              {"model": "image-01", "prompt": "一只白色小猫坐在窗边，简洁插画风格", "aspect_ratio": "16:9", "n": 1},
    "lyrics-gen":             {"mode": "write_full_song", "prompt": "一首关于夏天傍晚的轻快民谣"},
    "music-gen":              {"model": "music-2.6", "prompt": "轻快民谣，简单吉他伴奏", "lyrics": "[Verse]\n晚风吹过窗台\n我把一天慢慢放下来\n[Chorus]\n月光落在肩上\n心也变得安静起来", "stream": False, "output_format": "url", "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"}},
    "file-list":              {},
    "voice-list":             {"voice_type": "all"},
}


def _verify_via_invoker(cap_id: str, api_key: str, started_at: str, result: dict) -> dict:
    """通过 CapabilityInvoker 调用能力。"""
    payload = _INVOKER_PAYLOADS.get(cap_id, {})

    invoker = CapabilityInvoker(api_key=api_key, timeout=180.0)
    t0 = time.monotonic()

    try:
        response = invoker.invoke(cap_id, payload)
        latency_ms = int((time.monotonic() - t0) * 1000)
        result["latency_ms"] = latency_ms
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        result["response_shape_ok"] = response.ok
        result["status"] = "success" if response.ok else "failed"
        result["model"] = response.model
        result["output_type"] = response.output_type

        # medium 能力特有字段
        if cap_id in ("tts-sync", "image-t2i", "lyrics-gen", "music-gen"):
            result["level"] = "medium"
            _handle_medium_result(cap_id, response.raw, result)

    except NotImplementedCapability as exc:
        result["status"] = "skipped"
        result["error_message"] = f"not_implemented: {exc.capability_id}"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        result["latency_ms"] = latency_ms
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        result["status"] = "failed"
        err_msg = str(exc)
        if hasattr(exc, "http_status"):
            result["http_status"] = exc.http_status
        if hasattr(exc, "message"):
            err_msg = exc.message
        result["error_message"] = err_msg

    return result


# ── 旧 client 路径（models-* / high / video 等）──────────────────────────────

_cap_client_config: dict[str, tuple[str, str, dict | None, float]] = {
    "models-openai-list":     ("openai",   "list_models",           None,  30),
    "models-anthropic-list":  ("anthropic","list_models",           None,  30),
    "models-openai-retrieve": ("openai",   "retrieve_model",        None,  30),
    "models-anthropic-retrieve": ("anthropic","retrieve_model",     None,  30),
    "voice-clone-do":        ("native",   "voice_clone",           {"file_id": "dummy", "voice_id": "test_script_voice", "need_noise_reduction": False},  30),
    "voice-design":          ("native",   "voice_design",          {"prompt": "a calm female voice", "preview_text": "hello"},  30),
    "video-t2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "duration": 5},  180),
    "video-i2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "first_frame_image": "https://example.com/f.jpg", "duration": 5},  180),
    "video-s2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "subject_reference": [{"type": "character", "image": ["https://example.com/s.jpg"]}]},  180),
    "music-cover-prep":       ("native",   "music_generation",     {"purpose": "song"},  180),
    "tts-async":             ("native",   "tts_http",             {"model": "speech-02-turbo", "text": "测试语音", "voice_setting": {"voice_id": "female-shaonu"}},  180),
}


def _verify_via_client(cap_id: str, api_key: str, started_at: str, result: dict) -> dict:
    """对 CapabilityInvoker 未覆盖的能力（models-* / video / voice-clone）走 client 直接调用。"""
    if cap_id not in _cap_client_config:
        result["status"] = "skipped"
        result["error_message"] = "no config for this capability"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    client_type, method_name, body, timeout = _cap_client_config[cap_id]

    try:
        clients = {
            "openai":    MiniMaxOpenAIClient(api_key=api_key, timeout=timeout),
            "anthropic": MiniMaxAnthropicClient(api_key=api_key, timeout=timeout),
            "native":    MiniMaxNativeClient(api_key=api_key, timeout=timeout),
            "files":     MiniMaxFilesClient(api_key=api_key, timeout=timeout),
        }
        client = clients[client_type]
    except Exception as exc:
        result["status"] = "failed"
        result["error_message"] = f"client_init_error: {exc}"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    t0 = time.monotonic()
    status_code: int | None = None
    data: dict | None = None
    err: str | None = None

    try:
        method = getattr(client, method_name)
        data = method(body) if body else method()
        status_code = 200
    except Exception as exc:
        err = str(exc)
        if hasattr(exc, "http_status"):
            status_code = exc.http_status
            err = exc.message if hasattr(exc, "message") else str(exc)

    latency_ms = int((time.monotonic() - t0) * 1000)
    result["latency_ms"] = latency_ms
    result["ended_at"] = datetime.now(timezone.utc).isoformat()
    result["http_status"] = status_code

    if err:
        result["status"] = "failed"
        result["error_message"] = err
        return result

    if status_code in (401, 403):
        result["status"] = "unauthorized"
        result["error_message"] = f"HTTP {status_code}"
        return result
    if status_code == 429:
        result["status"] = "quota_limited"
        result["error_message"] = "HTTP 429 Rate Limited"
        return result
    if status_code and status_code >= 400:
        result["status"] = "failed"
        result["error_message"] = f"HTTP {status_code}: {str(data)[:200]}"
        return result

    shape_ok = _check_response_shape(cap_id, data)
    result["response_shape_ok"] = shape_ok
    result["status"] = "success" if shape_ok else "success_with_warning"
    result["model"] = body.get("model") if body else None

    if cap_id in ("tts-sync", "image-t2i", "lyrics-gen", "music-gen"):
        result["level"] = "medium"
        _handle_medium_result(cap_id, data, result)

    return result


def _handle_medium_result(cap_id: str, data: dict | None, result: dict) -> None:
    """处理 medium 能力结果，构建 AssetRef 并填充 result。

    语义规则：
      - asset_saved:  音频/图片文件是否实际写入 runtime/assets/
      - asset_reference_saved: URL/引用是否记录（未下载文件）
      - committed:     永远为 False（runtime 资产不提交 Git）

    result 中统一新增 assets[] 字段（list[AssetRef]）。
    """
    runtime_dir = Path(__file__).resolve().parent.parent / "runtime" / "assets"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    result["assets"] = []

    if cap_id == "tts-sync":
        result["output_type"] = "audio"
        if not (data and isinstance(data, dict)):
            return

        extra = data.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        data_dict = data.get("data") if isinstance(data.get("data"), dict) else None
        audio_hex = data_dict.get("audio") if data_dict else None

        if audio_hex:
            audio_bytes = bytes.fromhex(audio_hex)
            size_bytes = len(audio_bytes)
            out_path = runtime_dir / f"tts_sync_sample.{audio_format}"
            try:
                out_path.write_bytes(audio_bytes)
                asset_saved = True
            except Exception as e:
                result["asset_save_error"] = str(e)
                asset_saved = False

            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=str(out_path.relative_to(runtime_dir.parent.parent)) if asset_saved else None,
                url=None,
                size_bytes=size_bytes if asset_saved else None,
                duration_ms=extra.get("audio_length") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref]
            result["audio_returned"] = True
            result["audio_payload_type"] = "hex"
            result["audio_format"] = audio_format
            result["audio_length"] = extra.get("audio_length") if isinstance(extra, dict) else None
            result["audio_sample_rate"] = extra.get("audio_sample_rate") if isinstance(extra, dict) else None
            result["usage_characters"] = extra.get("usage_characters") if isinstance(extra, dict) else None
            result["asset_saved"] = asset_saved
            result["asset_committed"] = False
            result["asset_size"] = size_bytes if asset_saved else None
        else:
            result["audio_returned"] = False
            result["audio_payload_type"] = "unknown"
            result["audio_format"] = audio_format

    elif cap_id == "image-t2i":
        result["output_type"] = "image"
        if not (data and isinstance(data, dict)):
            return

        img_data = data.get("data") if isinstance(data.get("data"), dict) else None
        image_urls = img_data.get("image_urls") if img_data else None
        metadata = data.get("metadata") or {}
        success_count = int(metadata.get("success_count", 0)) if metadata.get("success_count") else 0
        failed_count = int(metadata.get("failed_count", 0)) if metadata.get("failed_count") else 0

        result["image_urls_count"] = len(image_urls) if image_urls else 0
        result["first_image_url_present"] = bool(image_urls and len(image_urls) > 0)
        result["success_count"] = success_count
        result["failed_count"] = failed_count
        result["task_id"] = data.get("id") or data.get("trace_id")

        if image_urls and len(image_urls) > 0:
            first_url = image_urls[0]
            ref = AssetRef(
                type="image",
                format=None,
                path=None,
                url=first_url,
                size_bytes=None,
                committed=False,
            )
            result["assets"] = [ref]
            result["audio_returned"] = True
            result["audio_payload_type"] = "url"
            result["asset_saved"] = False
            result["asset_reference_saved"] = True
            result["asset_committed"] = False
        else:
            result["audio_returned"] = False
            result["audio_payload_type"] = "unknown"
            result["asset_saved"] = False
            result["asset_reference_saved"] = False

    elif cap_id == "lyrics-gen":
        result["output_type"] = "text"
        if not (data and isinstance(data, dict)):
            return

        lyrics = data.get("lyrics") or ""
        result["song_title"] = data.get("song_title") or ""
        result["style_tags"] = data.get("style_tags") or ""
        result["lyrics_preview"] = lyrics[:200] if lyrics else ""
        result["audio_returned"] = bool(lyrics)
        result["audio_payload_type"] = "text"
        # 歌词是纯文本，不走 AssetRef（AssetRef 面向二进制/URL 资产）
        result["asset_saved"] = False
        result["asset_reference_saved"] = bool(lyrics)
        result["asset_committed"] = False

    elif cap_id == "music-gen":
        result["output_type"] = "music"
        if not (data and isinstance(data, dict)):
            return

        extra = data.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        img_data = data.get("data") if isinstance(data.get("data"), dict) else None
        audio_url = img_data.get("audio_url") or img_data.get("music_url") if img_data else None
        audio_hex = img_data.get("audio") if img_data else None

        result["audio_returned"] = bool(audio_url or audio_hex)
        result["audio_payload_type"] = "url" if audio_url else ("hex" if audio_hex else "unknown")
        result["audio_url_present"] = bool(audio_url)
        result["audio_hex_present"] = bool(audio_hex)
        result["audio_format"] = audio_format
        result["music_duration"] = extra.get("music_duration") if isinstance(extra, dict) else None
        result["music_sample_rate"] = extra.get("music_sample_rate") if isinstance(extra, dict) else None
        result["bitrate"] = extra.get("bitrate") if isinstance(extra, dict) else None

        if audio_url:
            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=None,
                url=audio_url,
                size_bytes=None,
                duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref]
            result["asset_saved"] = False
            result["asset_reference_saved"] = True
            result["asset_committed"] = False
        elif audio_hex:
            audio_bytes = bytes.fromhex(audio_hex)
            size_bytes = len(audio_bytes)
            out_path = runtime_dir / f"music_gen_sample.{audio_format}"
            try:
                out_path.write_bytes(audio_bytes)
                asset_saved = True
            except Exception as e:
                result["asset_save_error"] = str(e)
                asset_saved = False
                size_bytes = None

            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=str(out_path.relative_to(runtime_dir.parent.parent)) if asset_saved else None,
                url=None,
                size_bytes=size_bytes,
                duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref]
            result["asset_saved"] = asset_saved
            result["asset_reference_saved"] = False
            result["asset_committed"] = False
            result["asset_size"] = size_bytes
        else:
            result["asset_saved"] = False
            result["asset_reference_saved"] = False



def _check_response_shape(cap_id: str, data) -> bool:
    if data is None:
        return False
    if cap_id == "models-openai-list":
        return isinstance(data, dict) and "data" in data
    if cap_id == "models-anthropic-list":
        # MiniMax Anthropic 端点返回 OpenAI 兼容格式 {data: [...]} 而非标准 Anthropic {models: [...]}
        return isinstance(data, dict) and "data" in data
    if cap_id == "models-openai-retrieve":
        return isinstance(data, dict) and "id" in data
    if cap_id == "models-anthropic-retrieve":
        # MiniMax Anthropic 端点返回 OpenAI 兼容格式 {id: ...} 而非标准 Anthropic {name: ...}
        return isinstance(data, dict) and "id" in data
    if cap_id in ("chat-openai", "chat-anthropic", "chat-responses-create"):
        return isinstance(data, dict)
    if cap_id == "file-list":
        return isinstance(data, dict)
    if cap_id == "voice-list":
        return isinstance(data, dict)
    if cap_id in ("tts-sync", "image-t2i", "music-gen", "lyrics-gen", "tts-async"):
        return isinstance(data, dict)
    if cap_id in ("voice-clone-do", "voice-design", "video-t2v", "video-i2v", "video-s2v", "music-cover-prep"):
        return isinstance(data, dict)
    return True


# ── 报告生成 ─────────────────────────────────────────────────────────────────

def _generate_markdown(results: list[dict]) -> str:
    lines = [
        "# MiniMax 能力验收报告",
        "",
        f"> 生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "## 验收摘要",
        "",
        f"| 状态 | 数量 |",
        f"|---|---|",
    ]
    from collections import Counter
    counts = Counter(r["status"] for r in results)
    for status, cnt in sorted(counts.items()):
        lines.append(f"| {status} | {cnt} |")
    lines.append("")

    lines += [
        "## 详细结果",
        "",
        "| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: x["capability_id"]):
        lines.append(
            f"| {r['capability_id']} | {r['status']} "
            f"| {r.get('http_status', '-')} | {r.get('latency_ms', '-')} "
            f"| {r.get('model', '-')} | {r.get('error_message', '-')[:60] if r.get('error_message') else '-'} |"
        )
    lines += ["", "---", "*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*"]
    return "\n".join(lines)


# ── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax 能力验收脚本")
    parser.add_argument("--level", choices=["safe", "medium", "high"], default="safe",
                        help="验收级别：safe(默认)/medium/high")
    parser.add_argument("--confirm-cost", action="store_true",
                        help="确认中等成本验收（tts-sync, image-t2i 等）")
    parser.add_argument("--confirm-high-cost", action="store_true",
                        help="确认高成本验收（video, voice-clone 等）")
    args = parser.parse_args()

    if args.level == "medium" and not args.confirm_cost:
        print("ERROR: medium 级别需要 --confirm-cost 参数确认费用风险。", file=sys.stderr)
        sys.exit(1)
    if args.level == "high" and not (args.confirm_cost and args.confirm_high_cost):
        print("ERROR: high 级别需要 --confirm-cost --confirm-high-cost 双重确认。", file=sys.stderr)
        sys.exit(1)

    # safe / medium / high 分级安全隔离
    # --level safe      → 只跑 safe（默认）
    # --level medium    → 只跑 medium（需 --confirm-cost）
    # --level high      → 跑 medium + high（需双重确认）
    # --level safe+medium → 只在本任务中用于 isolated medium 模式（不通过 arg 暴露）

    env = _load_env()
    api_key = env.get("MINIMAX_API_KEY", "")

    if not api_key:
        print("ERROR: MINIMAX_API_KEY 未配置", file=sys.stderr)
        sys.exit(1)

    # 决定调用哪些能力
    if args.level == "safe":
        cap_ids = CAPABILITY_GROUPS["safe"]
    elif args.level == "medium":
        cap_ids = CAPABILITY_GROUPS["medium"]  # 仅 medium，不包含 safe
    else:
        cap_ids = CAPABILITY_GROUPS["safe"] + CAPABILITY_GROUPS["medium"] + CAPABILITY_GROUPS["high"]

    capabilities = _load_capabilities()
    models = _load_models()

    print("=" * 60)
    print(f"MiniMax 能力验收 - Level: {args.level}")
    print(f"API Key: {_redact(api_key)}")
    print(f"待验收能力数: {len(cap_ids)}")
    print("=" * 60)

    results: list[dict] = []
    for cap_id in cap_ids:
        cap_info = next((c for c in capabilities if c.get("id") == cap_id), None)
        cap_label = cap_info.get("label", cap_id) if cap_info else cap_id
        print(f"\n[{cap_id}] {cap_label}...", end=" ", flush=True)

        result = _verify_single(cap_id, api_key)
        results.append(result)

        status_icon = {"success": "[OK]", "failed": "[FAIL]", "skipped": "-",
                       "unauthorized": "[WARN]", "quota_limited": "[WAIT]",
                       "success_with_warning": "[WARN2]"}.get(result["status"], "?")
        print(f"{status_icon} {result['status']} ({result.get('latency_ms', '-')}ms)")

        if result.get("error_message"):
            print(f"    错误：{result['error_message'][:100]}")

    # 保存结果
    output: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "level": args.level,
        "api_key_tail": _redact(api_key),
        "total": len(results),
        "results": results,
    }

    out_path = RUNTIME_DIR / "latest.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OK] 保存 {out_path.relative_to(BACKEND)}")

    md = _generate_markdown(results)
    md_path = DOCS_DIR / "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[OK] 保存 {md_path.relative_to(BACKEND.parent)}")

    # 摘要
    from collections import Counter
    counts = Counter(r["status"] for r in results)
    print("\n" + "═" * 60)
    print("验收摘要")
    print("═" * 60)
    for status, cnt in sorted(counts.items()):
        print(f"  {status}: {cnt}")
    print("═" * 60)


if __name__ == "__main__":
    main()
