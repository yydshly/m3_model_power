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


# ── HTTP 调用 ────────────────────────────────────────────────────────────────

def _call(
    method: str,
    url: str,
    headers: dict,
    json_body: dict | None = None,
    timeout: float = 30,
) -> tuple[int, dict | None, str | None]:
    """返回 (http_status, response_dict, error_message)。"""
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                resp = client.get(url, headers=headers)
            elif method == "POST":
                resp = client.post(url, headers=headers, json=json_body)
            else:
                return 400, None, f"unsupported method: {method}"
            try:
                data = resp.json()
            except Exception:
                data = None
            return resp.status_code, data, None
    except httpx.TimeoutException:
        return 0, None, "timeout"
    except httpx.ConnectError as exc:
        return 0, None, f"connection_error: {exc}"
    except Exception as exc:
        return 0, None, str(exc)


# ── 单个能力验收 ─────────────────────────────────────────────────────────────

def _get_default_model(cap_id: str, models: list[dict]) -> str:
    """返回该能力下默认推荐的模型 ID。"""
    cap = next((c for c in models if c.get("id") == cap_id), None)
    if not cap:
        return "MiniMax-M3"
    # 按优先级：highspeed > flagship > standard > legacy
    order = {"highspeed": 0, "flagship": 1, "standard": 2, "hd": 1, "turbo": 2, "legacy": 3, "deprecated": 4}
    eligible = [m for m in models if m.get("enabled", True)]
    eligible.sort(key=lambda m: order.get(m.get("tier", "standard"), 99))
    return eligible[0]["id"] if eligible else "MiniMax-M3"


def _verify_single(
    cap_id: str,
    base_url: str,
    api_key: str,
) -> dict:
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

    # 判断是否为 Anthropic 协议
    is_anthropic = "anthropic" in cap_id
    headers = {"X-Api-Key": api_key, "anthropic-version": "2023-06-01"} if is_anthropic else {"Authorization": f"Bearer {api_key}"}

    # 能力 → 请求信息
    cap_config = {
        "models-openai-list": {"method": "GET", "path": "/v1/models"},
        "models-anthropic-list": {"method": "GET", "path": "/anthropic/v1/models"},
        "models-openai-retrieve": {"method": "GET", "path": "/v1/models/MiniMax-M3"},
        "models-anthropic-retrieve": {"method": "GET", "path": "/anthropic/v1/models/MiniMax-M3"},
        "chat-openai": {"method": "POST", "path": "/v1/chat/completions", "body": {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16}},
        "chat-anthropic": {"method": "POST", "path": "/anthropic/v1/messages", "body": {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16}},
        "chat-responses-create": {"method": "POST", "path": "/v1/responses", "body": {"model": "MiniMax-M3", "input": "Hi"}},
        "chat-responses-tokens": {"method": "POST", "path": "/v1/responses/input_tokens", "body": {"model": "MiniMax-M3", "input": "Hi"}},
        "file-list": {"method": "GET", "path": "/v1/files/list"},
        "voice-list": {"method": "POST", "path": "/v1/get_voice", "body": {"voice_type": "all"}},
        "tts-sync": {"method": "POST", "path": "/v1/t2a_v2", "body": {"model": "speech-02-turbo", "text": "你好，这是 MiniMax 语音能力验收。", "voice_setting": {"voice_id": "female-tianmei"}, "audio_setting": {"sample_rate": 32000, "format": "mp3"}}},
        "image-t2i": {"method": "POST", "path": "/v1/image_generation", "body": {"model": "image-01", "prompt": "一只白色小猫坐在窗边，简洁插画风格", "aspect_ratio": "16:9", "n": 1}},
        "lyrics-gen": {"method": "POST", "path": "/v1/lyrics_generation", "body": {"mode": "write_full_song", "prompt": "一首关于夏天傍晚的轻快民谣"}},
        "music-gen": {"method": "POST", "path": "/v1/music_generation", "body": {"model": "music-2.6", "prompt": "轻快民谣，简单吉他伴奏", "lyrics": "[Verse]\n晚风吹过窗台\n我把一天慢慢放下来\n[Chorus]\n月光落在肩上\n心也变得安静起来", "stream": False, "output_format": "url", "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"}}},
        "voice-clone-do": {"method": "POST", "path": "/v1/voice_clone", "body": {"file_id": "dummy", "voice_id": "test_script_voice", "need_noise_reduction": False}},
        "voice-design": {"method": "POST", "path": "/v1/voice_design", "body": {"prompt": "a calm female voice", "preview_text": "hello"}},
        "video-t2v": {"method": "POST", "path": "/v1/video_generation", "body": {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "duration": 5}},
        "video-i2v": {"method": "POST", "path": "/v1/video_generation", "body": {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "first_frame_image": "https://example.com/f.jpg", "duration": 5}},
        "video-s2v": {"method": "POST", "path": "/v1/video_generation", "body": {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "subject_reference": [{"type": "character", "image": ["https://example.com/s.jpg"]}]}},
        "music-cover-prep": {"method": "POST", "path": "/v1/music_cover/preprocess", "body": {"purpose": "song"}},
        "tts-async": {"method": "POST", "path": "/v1/t2a_async_v2", "body": {"model": "speech-02-turbo", "text": "测试语音", "voice_setting": {"voice_id": "female-shaonu"}}},
    }

    if cap_id not in cap_config:
        result["status"] = "skipped"
        result["error_message"] = "no config for this capability"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    cfg = cap_config[cap_id]
    url = f"{base_url.rstrip('/')}{cfg['path']}"
    body = cfg.get("body")
    timeout = 180 if cap_id in ("video-t2v", "video-i2v", "video-s2v", "music-cover-prep", "tts-async", "music-gen") else 30

    t0 = time.monotonic()
    status_code, data, err = _call(cfg["method"], url, headers, body, timeout=timeout)
    latency_ms = int((time.monotonic() - t0) * 1000)
    result["latency_ms"] = latency_ms
    result["ended_at"] = datetime.now(timezone.utc).isoformat()
    result["http_status"] = status_code

    if err:
        result["status"] = "failed"
        result["error_message"] = err
        return result

    if status_code == 401 or status_code == 403:
        result["status"] = "unauthorized"
        result["error_message"] = f"HTTP {status_code}"
        return result

    if status_code == 429:
        result["status"] = "quota_limited"
        result["error_message"] = "HTTP 429 Rate Limited"
        return result

    if status_code >= 400:
        result["status"] = "failed"
        result["error_message"] = f"HTTP {status_code}: {str(data)[:200]}"
        return result

    # shape 检查
    shape_ok = _check_response_shape(cap_id, data)
    result["response_shape_ok"] = shape_ok
    result["status"] = "success" if shape_ok else "success_with_warning"
    result["model"] = body.get("model") if body else None

    # medium 能力特有字段
    if cap_id in ("tts-sync", "image-t2i", "lyrics-gen", "music-gen"):
        result["level"] = "medium"
        _handle_medium_result(cap_id, data, result)

    return result


def _handle_medium_result(cap_id: str, data: dict | None, result: dict) -> None:
    """处理 medium 能力特有字段：output_type / asset_saved / asset_committed。
    根据 MiniMax 官方响应结构解析。
    """
    runtime_dir = Path(__file__).resolve().parent.parent / "runtime" / "assets"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if cap_id == "tts-sync":
        result["output_type"] = "audio"
        if data and isinstance(data, dict):
            # data.audio is hex MP3; extra_info is a sibling of data (not nested inside it)
            extra = data.get("extra_info") or {}
            audio_format = (extra.get("audio_format") if isinstance(extra, dict) else "mp3") or "mp3"
            data_dict = data.get("data") if isinstance(data.get("data"), dict) else None
            audio_hex = data_dict.get("audio") if data_dict else None
            if audio_hex:
                try:
                    audio_bytes = bytes.fromhex(audio_hex)
                    out_path = runtime_dir / f"tts_sync_sample.{audio_format}"
                    out_path.write_bytes(audio_bytes)
                    result["asset_saved"] = True
                    result["asset_committed"] = False
                    result["asset_path"] = str(out_path.relative_to(runtime_dir.parent.parent))
                    result["asset_size"] = len(audio_bytes)
                    if isinstance(extra, dict):
                        result["audio_length"] = extra.get("audio_length")
                        result["audio_sample_rate"] = extra.get("audio_sample_rate")
                        result["audio_format"] = extra.get("audio_format") or audio_format
                        result["usage_characters"] = extra.get("usage_characters")
                    else:
                        result["audio_format"] = audio_format
                except Exception as e:
                    result["asset_save_error"] = str(e)
            else:
                result["audio_format"] = audio_format

    elif cap_id == "image-t2i":
        result["output_type"] = "image"
        if data and isinstance(data, dict):
            # MiniMax image-t2i: {data: {image_urls: [...]}, metadata: {success_count, failed_count}}
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
                result["asset_saved"] = True  # URL已知，不下载图片
                result["asset_committed"] = False

    elif cap_id == "lyrics-gen":
        result["output_type"] = "text"
        if data and isinstance(data, dict):
            # lyrics-gen response is FLAT: {song_title, style_tags, lyrics, base_resp}
            lyrics = data.get("lyrics") or ""
            result["song_title"] = data.get("song_title") or ""
            result["style_tags"] = data.get("style_tags") or ""
            result["lyrics_preview"] = lyrics[:200] if lyrics else ""
            if lyrics:
                result["asset_saved"] = True
                result["asset_committed"] = False

    elif cap_id == "music-gen":
        result["output_type"] = "music"
        if data and isinstance(data, dict):
            # music-gen: {data: {audio: "..."} 或 {audio_url: "..."}, extra_info: {...}}
            extra = data.get("extra_info") or {}
            audio_url = None
            audio_hex = None
            audio_format = (extra.get("audio_format") or "mp3") if isinstance(extra, dict) else "mp3"
            img_data = data.get("data") if isinstance(data.get("data"), dict) else None
            if img_data:
                audio_url = img_data.get("audio_url") or img_data.get("music_url")
                audio_hex = img_data.get("audio")
            result["audio_url_present"] = bool(audio_url)
            result["audio_hex_present"] = bool(audio_hex)
            result["audio_format"] = audio_format
            result["music_duration"] = extra.get("music_duration") if isinstance(extra, dict) else None
            result["music_sample_rate"] = extra.get("music_sample_rate") if isinstance(extra, dict) else None
            result["bitrate"] = extra.get("bitrate") if isinstance(extra, dict) else None
            if audio_url or audio_hex:
                result["asset_saved"] = True
                result["asset_committed"] = False


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
    base_url = env.get("MINIMAX_BASE_URL", "https://api.minimaxi.com").rstrip("/")
    group_id = env.get("MINIMAX_GROUP_ID", "")

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
    print(f"Base URL: {base_url}")
    print(f"待验收能力数: {len(cap_ids)}")
    print("=" * 60)

    results: list[dict] = []
    for cap_id in cap_ids:
        cap_info = next((c for c in capabilities if c.get("id") == cap_id), None)
        cap_label = cap_info.get("label", cap_id) if cap_info else cap_id
        print(f"\n[{cap_id}] {cap_label}...", end=" ", flush=True)

        result = _verify_single(cap_id, base_url, api_key)
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
        "base_url": base_url,
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
