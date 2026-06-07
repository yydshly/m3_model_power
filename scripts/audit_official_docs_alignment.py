#!/usr/bin/env python3
"""
MiniMax Official Docs Alignment Audit Script

Compares the EXPECTED_OFFICIAL_CAPABILITIES (derived from MiniMax official docs)
against the actual models.yaml and capabilities.yaml to produce a gap report.

No real MiniMax API calls are made.
"""

import json
import sys
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
MODELS_YAML_PATH = REPO_ROOT / "backend" / "config" / "models.yaml"
CAPABILITIES_YAML_PATH = REPO_ROOT / "backend" / "config" / "capabilities.yaml"
TEMPLATES_JSON_PATH = REPO_ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"


# ── Expected Official Capabilities ──────────────────────────────────────────
# Derived from https://platform.minimaxi.com/docs/llms.txt
# Format: capability_id -> expected metadata

EXPECTED_OFFICIAL_CAPABILITIES: dict[str, dict[str, Any]] = {
    # ── Text: Anthropic ────────────────────────────────────────────────────
    "chat-anthropic": {
        "official_doc": "Anthropic Messages API（Anthropic 兼容）",
        "official_endpoint": "POST /anthropic/v1/messages",
        "openapi_spec": "openapi-chat-anthropic",
        "source_doc": "text-chat-anthropic.md",
        "models": [
            "MiniMax-M3",
            "MiniMax-M2.7",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.5",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.1",
            "MiniMax-M2.1-highspeed",
            "MiniMax-M2",
        ],
        "params": [
            "model",
            "system",
            "messages",
            "temperature",
            "top_p",
            "max_tokens",
            "thinking",
            "tools",
            "tool_choice",
            "metadata",
            "stream",
            "stop_sequences",
        ],
        "required_params": ["model", "messages", "max_tokens"],
        "streaming": True,
        "protocols": ["anthropic"],
        "category": "chat",
    },
    "models-anthropic-list": {
        "official_doc": "获取模型列表",
        "official_endpoint": "GET /anthropic/v1/models",
        "openapi_spec": None,
        "source_doc": "models/anthropic/list-models.md",
        "models": [],  # No model selection for list
        "params": [],
        "required_params": [],
        "streaming": False,
        "protocols": ["anthropic"],
        "category": "models",
    },
    "models-anthropic-retrieve": {
        "official_doc": "获取单个模型详情",
        "official_endpoint": "GET /anthropic/v1/models/{model}",
        "openapi_spec": None,
        "source_doc": "models/anthropic/retrieve-model.md",
        "models": [],  # model is a path param
        "params": ["model"],
        "required_params": ["model"],
        "streaming": False,
        "protocols": ["anthropic"],
        "category": "models",
    },
    "anthropic-active-cache": {
        "official_doc": "Anthropic 主动缓存",
        "official_endpoint": "(cache control headers on /anthropic/v1/messages)",
        "openapi_spec": None,
        "source_doc": "anthropic-api-compatible-cache.md",
        "models": ["MiniMax-M3"],  # Only M3 supports active cache
        "params": ["anthropic-beta", "anthropic-active-chat", "anthropic-force-attempt"],
        "required_params": [],
        "streaming": True,
        "protocols": ["anthropic"],
        "category": "chat",
    },
    # ── Text: OpenAI ──────────────────────────────────────────────────────
    "chat-openai": {
        "official_doc": "Chat Completions API",
        "official_endpoint": "POST /v1/chat/completions",
        "openapi_spec": "openapi-chat-openai",
        "source_doc": "text-chat-openai.md",
        "models": [
            "MiniMax-M3",
            "MiniMax-M2.7",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.5",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.1",
            "MiniMax-M2.1-highspeed",
            "MiniMax-M2",
        ],
        "params": [
            "model",
            "messages",
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "thinking",
            "reasoning_split",
            "tools",
            "tool_choice",
            "stream_options",
            "presence_penalty",
            "frequency_penalty",
            "logit_bias",
            "user",
        ],
        "required_params": ["model", "messages"],
        "streaming": True,
        "protocols": ["openai"],
        "category": "chat",
    },
    "models-openai-list": {
        "official_doc": "获取模型列表",
        "official_endpoint": "GET /v1/models",
        "openapi_spec": None,
        "source_doc": "models/openai/list-models.md",
        "models": [],
        "params": [],
        "required_params": [],
        "streaming": False,
        "protocols": ["openai"],
        "category": "models",
    },
    "models-openai-retrieve": {
        "official_doc": "获取单个模型详情",
        "official_endpoint": "GET /v1/models/{model}",
        "openapi_spec": None,
        "source_doc": "models/openai/retrieve-model.md",
        "models": [],
        "params": ["model"],
        "required_params": ["model"],
        "streaming": False,
        "protocols": ["openai"],
        "category": "models",
    },
    # ── Text: Responses ───────────────────────────────────────────────────
    "chat-responses-create": {
        "official_doc": "对话生成 (Responses)",
        "official_endpoint": "POST /v1/responses",
        "openapi_spec": "openapi-responses",
        "source_doc": "responses-create.md",
        "models": ["MiniMax-M3"],
        "params": [
            "model",
            "input",
            "input_modality",
            "output_modality",
            "max_output_tokens",
            "stream",
            "temperature",
            "top_p",
            "tools",
            "reasoning",
            "thinking",
            "prompt_caching",
        ],
        "required_params": ["model", "input"],
        "streaming": True,
        "protocols": ["responses"],
        "category": "chat",
    },
    "chat-responses-tokens": {
        "official_doc": "Token 估算",
        "official_endpoint": "POST /v1/responses/input_tokens",
        "openapi_spec": None,
        "source_doc": "responses-input-tokens.md",
        "models": ["MiniMax-M3"],
        "params": ["model", "input"],
        "required_params": ["model", "input"],
        "streaming": False,
        "protocols": ["responses"],
        "category": "chat",
    },
    "prompt-caching": {
        "official_doc": "Prompt 缓存",
        "official_endpoint": "(cache control params on existing endpoints)",
        "openapi_spec": None,
        "source_doc": "text-prompt-caching.md",
        "models": ["MiniMax-M3"],
        "params": ["prompt_caching", "cache_window"],
        "required_params": [],
        "streaming": True,
        "protocols": ["anthropic", "openai", "responses"],
        "category": "chat",
    },
    # ── Voice / TTS ───────────────────────────────────────────────────────
    "tts-sync": {
        "official_doc": "同步 HTTP TTS",
        "official_endpoint": "POST /v1/t2a_v2",
        "openapi_spec": None,
        "source_doc": "speech-t2a-http.md",
        "models": [
            "speech-2.8-hd",
            "speech-2.8-turbo",
            "speech-2.6-hd",
            "speech-2.6-turbo",
            "speech-02-hd",
            "speech-02-turbo",
        ],
        "params": [
            "model",
            "text",
            "voice_setting",
            "voice_setting.voice_id",
            "voice_setting.speed",
            "voice_setting.vol",
            "voice_setting.pitch",
            "voice_setting.emotion",
            "audio_setting",
            "audio_setting.sample_rate",
            "audio_setting.bitrate",
            "audio_setting.format",
            "output_format",
            "aigc_watermark",
            "subtitle_enable",
            "voice_modify",
        ],
        "required_params": ["model", "text", "voice_setting.voice_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "tts-ws": {
        "official_doc": "同步 WebSocket TTS",
        "official_endpoint": "WS /ws/v1/t2a_v2",
        "openapi_spec": None,
        "source_doc": "speech-t2a-websocket.md",
        "models": [
            "speech-2.8-hd",
            "speech-2.8-turbo",
            "speech-2.6-hd",
            "speech-2.6-turbo",
            "speech-02-hd",
            "speech-02-turbo",
        ],
        "params": [
            "model",
            "text",
            "voice_setting",
            "voice_setting.voice_id",
            "voice_setting.speed",
        ],
        "required_params": ["model", "text", "voice_setting.voice_id"],
        "streaming": True,
        "protocols": ["native"],
        "category": "voice",
    },
    "tts-async": {
        "official_doc": "异步 TTS",
        "official_endpoint": "POST /v1/t2a_async_v2",
        "openapi_spec": None,
        "source_doc": "speech-t2a-async-create.md",
        "models": [
            "speech-2.8-hd",
            "speech-2.8-turbo",
            "speech-2.6-hd",
            "speech-2.6-turbo",
            "speech-02-hd",
            "speech-02-turbo",
        ],
        "params": ["model", "text", "voice_setting", "voice_setting.voice_id", "voice_setting.speed"],
        "required_params": ["model", "text", "voice_setting.voice_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-list": {
        "official_doc": "音色列表",
        "official_endpoint": "POST /v1/get_voice",
        "openapi_spec": None,
        "source_doc": "voice-management-get.md",
        "models": [],
        "params": ["voice_type"],
        "required_params": [],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-clone-do": {
        "official_doc": "音色快速复刻",
        "official_endpoint": "POST /v1/voice_clone",
        "openapi_spec": None,
        "source_doc": "voice-cloning-clone.md",
        "models": [],
        "params": ["file_id", "voice_id", "need_noise_reduction", "need_volume_normalization"],
        "required_params": ["file_id", "voice_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-design": {
        "official_doc": "音色设计",
        "official_endpoint": "POST /v1/voice_design",
        "openapi_spec": None,
        "source_doc": "voice-design-design.md",
        "models": [],
        "params": ["prompt", "preview_text"],
        "required_params": ["prompt"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-delete": {
        "official_doc": "删除音色",
        "official_endpoint": "POST /v1/delete_voice",
        "openapi_spec": None,
        "source_doc": "voice-management-delete.md",
        "models": [],
        "params": ["voice_type", "voice_id"],
        "required_params": ["voice_type", "voice_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-clone-upload-audio": {
        "official_doc": "上传复刻音频",
        "official_endpoint": "POST /v1/files/upload",
        "openapi_spec": None,
        "source_doc": "voice-cloning-uploadcloneaudio.md",
        "models": [],
        "params": ["file", "purpose"],
        "required_params": ["file"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    "voice-clone-upload-prompt": {
        "official_doc": "上传示例音频",
        "official_endpoint": "POST /v1/files/upload",
        "openapi_spec": None,
        "source_doc": "voice-cloning-uploadprompt.md",
        "models": [],
        "params": ["file", "purpose"],
        "required_params": ["file"],
        "streaming": False,
        "protocols": ["native"],
        "category": "voice",
    },
    # ── Image ──────────────────────────────────────────────────────────────
    "image-t2i": {
        "official_doc": "文生图 (T2I)",
        "official_endpoint": "POST /v1/image_generation",
        "openapi_spec": "text-to-image",
        "source_doc": "image-generation-t2i.md",
        "models": ["image-01", "image-01-live"],
        "params": [
            "model",
            "prompt",
            "aspect_ratio",
            "width",
            "height",
            "style.style_type",
            "style.style_weight",
            "response_format",
            "seed",
            "n",
            "prompt_optimizer",
            "aigc_watermark",
        ],
        "required_params": ["model", "prompt"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "image-i2i": {
        "official_doc": "图生图 (I2I)",
        "official_endpoint": "POST /v1/image_generation",
        "openapi_spec": "image-to-image",
        "source_doc": "image-generation-i2i.md",
        "models": ["image-01", "image-01-live"],
        "params": [
            "model",
            "prompt",
            "subject_reference",
            "subject_reference[].type",
            "subject_reference[].image_file",
            "aspect_ratio",
            "response_format",
            "seed",
            "n",
            "prompt_optimizer",
            "aigc_watermark",
        ],
        "required_params": ["model", "prompt", "subject_reference"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    # ── Music ───────────────────────────────────────────────────────────────
    "lyrics-gen": {
        "official_doc": "歌词生成",
        "official_endpoint": "POST /v1/lyrics_generation",
        "openapi_spec": None,
        "source_doc": "lyrics-generation.md",
        "models": [],
        "params": ["mode", "prompt", "lyrics", "title"],
        "required_params": ["mode", "prompt"],
        "streaming": False,
        "protocols": ["native"],
        "category": "music",
    },
    "music-gen": {
        "official_doc": "音乐生成",
        "official_endpoint": "POST /v1/music_generation",
        "openapi_spec": None,
        "source_doc": "music-generation.md",
        "models": ["music-2.6", "music-cover"],
        "params": [
            "model",
            "prompt",
            "lyrics",
            "title",
            "style",
            "stream",
            "is_instrumental",
            "lyrics_optimizer",
            "audio_url",
            "audio_base64",
            "cover_feature_id",
            "output_format",
            "aigc_watermark",
        ],
        "required_params": ["model"],
        "streaming": False,
        "protocols": ["native"],
        "category": "music",
    },
    "music-cover-prep": {
        "official_doc": "翻唱前处理",
        "official_endpoint": "POST /v1/music_cover/preprocess",
        "openapi_spec": None,
        "source_doc": "music-cover-preprocess.md",
        "models": ["music-cover"],
        "params": ["purpose", "audio_url", "audio_base64"],
        "required_params": ["purpose"],
        "streaming": False,
        "protocols": ["native"],
        "category": "music",
    },
    # ── Files ───────────────────────────────────────────────────────────────
    "file-upload": {
        "official_doc": "文件上传",
        "official_endpoint": "POST /v1/files/upload",
        "openapi_spec": None,
        "source_doc": "file-management-upload.md",
        "models": [],
        "params": ["file", "purpose"],
        "required_params": ["file", "purpose"],
        "streaming": False,
        "protocols": ["native"],
        "category": "files",
    },
    "file-list": {
        "official_doc": "文件列表",
        "official_endpoint": "GET /v1/files/list",
        "openapi_spec": None,
        "source_doc": "file-management-list.md",
        "models": [],
        "params": ["purpose"],
        "required_params": [],
        "streaming": False,
        "protocols": ["native"],
        "category": "files",
    },
    "file-retrieve": {
        "official_doc": "文件检索",
        "official_endpoint": "GET /v1/files/retrieve",
        "openapi_spec": None,
        "source_doc": "file-management-retrieve.md",
        "models": [],
        "params": ["file_id"],
        "required_params": ["file_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "files",
    },
    "file-content": {
        "official_doc": "文件内容下载",
        "official_endpoint": "GET /v1/files/retrieve_content",
        "openapi_spec": None,
        "source_doc": "file-management-retrieve-content.md",
        "models": [],
        "params": ["file_id"],
        "required_params": ["file_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "files",
    },
    "file-delete": {
        "official_doc": "文件删除",
        "official_endpoint": "POST /v1/files/delete",
        "openapi_spec": None,
        "source_doc": "file-management-delete.md",
        "models": [],
        "params": ["file_id"],
        "required_params": ["file_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "files",
    },
    # ── Video ───────────────────────────────────────────────────────────────
    "video-t2v": {
        "official_doc": "文生视频 (T2V)",
        "official_endpoint": "POST /v1/video_generation",
        "openapi_spec": "text-to-video",
        "source_doc": "video-generation-t2v.md",
        "models": ["MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3-Fast", "MiniMax-Hailuo-02"],
        "params": ["model", "prompt", "duration", "resolution", "first_frame_image"],
        "required_params": ["model", "prompt"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-i2v": {
        "official_doc": "图生视频 (I2V)",
        "official_endpoint": "POST /v1/video_generation",
        "openapi_spec": "image-to-video",
        "source_doc": "video-generation-i2v.md",
        "models": ["MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3-Fast", "MiniMax-Hailuo-02"],
        "params": ["model", "prompt", "first_frame_image", "duration", "resolution"],
        "required_params": ["model", "prompt", "first_frame_image"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-fl2v": {
        "official_doc": "首尾帧生成视频 (FL2V)",
        "official_endpoint": "POST /v1/video_generation",
        "openapi_spec": "start-end-to-video",
        "source_doc": "video-generation-fl2v.md",
        "models": ["MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3-Fast", "MiniMax-Hailuo-02"],
        "params": ["model", "prompt", "first_frame_image", "last_frame_image", "duration", "resolution"],
        "required_params": ["model", "prompt", "first_frame_image", "last_frame_image"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-s2v": {
        "official_doc": "主体参考视频 (S2V)",
        "official_endpoint": "POST /v1/video_generation",
        "openapi_spec": "subject-reference-to-video",
        "source_doc": "video-generation-s2v.md",
        "models": ["MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3-Fast", "MiniMax-Hailuo-02"],
        "params": ["model", "prompt", "subject_reference", "duration", "resolution"],
        "required_params": ["model", "prompt", "subject_reference"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-query": {
        "official_doc": "查询任务状态",
        "official_endpoint": "GET /v1/query/video_generation",
        "openapi_spec": None,
        "source_doc": "video-generation-query.md",
        "models": [],
        "params": ["task_id"],
        "required_params": ["task_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-download": {
        "official_doc": "视频下载",
        "official_endpoint": "GET /v1/files/retrieve",
        "openapi_spec": None,
        "source_doc": "video-generation-download.md",
        "models": [],
        "params": ["file_id"],
        "required_params": ["file_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-agent-create": {
        "official_doc": "视频 Agent 创建",
        "official_endpoint": "POST /v1/video_agent",
        "openapi_spec": None,
        "source_doc": "video-agent-create.md",
        "models": [],
        "params": ["model", "prompt"],
        "required_params": ["model", "prompt"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
    "video-agent-query": {
        "official_doc": "视频 Agent 查询",
        "official_endpoint": "GET /v1/video_agent",
        "openapi_spec": None,
        "source_doc": "video-agent-query.md",
        "models": [],
        "params": ["task_id"],
        "required_params": ["task_id"],
        "streaming": False,
        "protocols": ["native"],
        "category": "vision",
    },
}


# ── Gap Types ────────────────────────────────────────────────────────────────

class GapType:
    MISSING_CAPABILITY = "missing_capability"
    MISSING_MODEL = "missing_model"
    MISSING_PARAMETER = "missing_parameter"
    WRONG_PROTOCOL = "wrong_protocol"
    WRONG_SCOPE = "wrong_scope"
    WRONG_RISK_POLICY = "wrong_risk_policy"
    RUNNER_INCOMPLETE = "runner_incomplete"
    DOCS_ONLY = "docs_only"
    OUT_OF_SCOPE_BY_DESIGN = "out_of_scope_by_design"
    HIGH_RISK_BY_DESIGN = "high_risk_by_design"
    TOKEN_PLAN_UNKNOWN = "token_plan_unknown"
    NEEDS_REAL_PROBE = "needs_real_probe"


# ── Priority ────────────────────────────────────────────────────────────────

class Priority:
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


# ── Report ───────────────────────────────────────────────────────────────────

class GapReport:
    def __init__(self):
        self.gaps: list[dict[str, Any]] = []

    def add(
        self,
        capability_id: str,
        gap_type: str,
        priority: str,
        detail: str,
        official_doc: str | None = None,
        expected: Any = None,
        actual: Any = None,
    ):
        self.gaps.append({
            "capability_id": capability_id,
            "gap_type": gap_type,
            "priority": priority,
            "detail": detail,
            "official_doc": official_doc,
            "expected": expected,
            "actual": actual,
        })

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for gap in self.gaps:
            t = gap["gap_type"]
            counts[t] = counts.get(t, 0) + 1

        priority_counts: dict[str, int] = {}
        for gap in self.gaps:
            p = gap["priority"]
            priority_counts[p] = priority_counts.get(p, 0) + 1

        return {
            "total_gaps": len(self.gaps),
            "by_gap_type": counts,
            "by_priority": priority_counts,
        }

    def print_report(self):
        print("=" * 80)
        print("MiniMax Official Docs Alignment Audit Report")
        print("=" * 80)

        summary = self.summary()
        print(f"\nTotal gaps found: {summary['total_gaps']}")

        print("\n── By Gap Type ──")
        for gt, count in sorted(summary["by_gap_type"].items()):
            print(f"  {gt}: {count}")

        print("\n── By Priority ──")
        for p, count in sorted(summary["by_priority"].items()):
            print(f"  {p}: {count}")

        print("\n── Detailed Gaps ──")
        for gap in sorted(self.gaps, key=lambda g: (g["priority"], g["gap_type"])):
            print(f"\n[{gap['priority']}] {gap['capability_id']} | {gap['gap_type']}")
            print(f"  Official doc: {gap['official_doc']}")
            print(f"  Detail: {gap['detail']}")
            if gap["expected"] is not None:
                print(f"  Expected: {gap['expected']}")
            if gap["actual"] is not None:
                print(f"  Actual:   {gap['actual']}")

        return summary


# ── Load actual config ───────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML using PyYAML."""
    import yaml
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Audit ───────────────────────────────────────────────────────────────────

def audit():
    report = GapReport()

    # Load actual configs
    models_data = load_yaml(MODELS_YAML_PATH)
    capabilities_data = load_yaml(CAPABILITIES_YAML_PATH)
    templates_data = load_json(TEMPLATES_JSON_PATH)

    models: list[dict[str, Any]] = models_data.get("models", [])
    capabilities: list[dict[str, Any]] = capabilities_data.get("capabilities", [])
    templates: dict[str, Any] = templates_data.get("templates", {})

    # Index by id
    model_by_id = {m["id"]: m for m in models}
    cap_by_id = {c["id"]: c for c in capabilities}

    # ── 1. Check missing capabilities ─────────────────────────────────────
    for cap_id, expected in EXPECTED_OFFICIAL_CAPABILITIES.items():
        if cap_id not in cap_by_id:
            official_doc = expected.get("official_doc", "unknown")
            # Determine if this is docs_only or missing_capability
            # Video and advanced features are often out_of_scope_by_design
            category = expected.get("category", "")
            if category in ("vision",) and "agent" in cap_id.lower():
                gap_type = GapType.MISSING_CAPABILITY
                priority = Priority.P2  # Video agent is high-cost
            elif category in ("vision",):
                gap_type = GapType.MISSING_CAPABILITY
                priority = Priority.P1  # Video FL2V should be added
            else:
                gap_type = GapType.MISSING_CAPABILITY
                priority = Priority.P1

            report.add(
                capability_id=cap_id,
                gap_type=gap_type,
                priority=priority,
                detail=f"Capability not found in capabilities.yaml",
                official_doc=official_doc,
                expected="registered in capabilities.yaml",
                actual="not found",
            )

    # ── 2. Check model protocols vs expected ──────────────────────────────
    chat_models = [m for m in models if m.get("family") == "chat"]
    for m in chat_models:
        model_id = m["id"]
        actual_protocols = set(m.get("protocols", []))

        # Determine expected protocols based on official docs
        # M3 supports all three
        # All M2.x highspeed support [openai, anthropic]
        # All M2.x standard support [openai] according to current yaml
        # BUT: official docs say all 8 models support both protocols
        # We need to check if M2.7/M2.5/M2.1/M2 are missing anthropic

        if model_id in ("MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"):
            expected_protocols = {"openai", "anthropic"}
            missing = expected_protocols - actual_protocols
            if missing:
                report.add(
                    capability_id="chat-anthropic",
                    gap_type=GapType.WRONG_PROTOCOL,
                    priority=Priority.P0,
                    detail=f"Model {model_id} supports anthropic per official docs but protocols=[openai] in models.yaml",
                    official_doc="text-chat-anthropic.md",
                    expected=sorted(expected_protocols),
                    actual=sorted(actual_protocols),
                )

    # ── 3. Check Runner model dropdown completeness ──────────────────────
    for cap_id in ("chat-anthropic", "chat-openai", "chat-responses-create"):
        if cap_id not in templates:
            continue
        template = templates[cap_id]
        form_schema = template.get("form_schema", {})
        model_field = form_schema.get("model", {})
        options = model_field.get("options", [])
        runner_models = {opt["value"] for opt in options}

        if cap_id in EXPECTED_OFFICIAL_CAPABILITIES:
            expected = EXPECTED_OFFICIAL_CAPABILITIES[cap_id]
            expected_models = set(expected.get("models", []))
            missing_models = expected_models - runner_models
            if missing_models:
                report.add(
                    capability_id=cap_id,
                    gap_type=GapType.RUNNER_INCOMPLETE,
                    priority=Priority.P0,
                    detail=f"Runner model dropdown missing {len(missing_models)} models: {sorted(missing_models)}",
                    official_doc=expected.get("official_doc"),
                    expected=sorted(expected_models),
                    actual=sorted(runner_models),
                )

    # ── 4. Check parameters in Runner ────────────────────────────────────
    for cap_id, expected in EXPECTED_OFFICIAL_CAPABILITIES.items():
        if cap_id not in templates:
            continue
        template = templates[cap_id]
        form_schema = template.get("form_schema", {})
        form_fields = set(form_schema.keys())

        expected_params = set(expected.get("params", []))
        required_params = set(expected.get("required_params", []))

        # Map form fields to expected params (rough approximation)
        # Missing required params are more critical
        missing_required = required_params - form_fields
        if missing_required and cap_id in ("chat-anthropic", "chat-openai", "chat-responses-create"):
            # These are the key chat protocols where param completeness matters most
            report.add(
                capability_id=cap_id,
                gap_type=GapType.RUNNER_INCOMPLETE,
                priority=Priority.P1,
                detail=f"Runner form missing required params: {sorted(missing_required)}",
                official_doc=expected.get("official_doc"),
                expected=sorted(required_params),
                actual=sorted(form_fields),
            )

    # ── 5. Check capabilities scope policy ───────────────────────────────
    for cap_id, expected in EXPECTED_OFFICIAL_CAPABILITIES.items():
        if cap_id not in cap_by_id:
            continue
        cap = cap_by_id[cap_id]
        scope = cap.get("scope_policy", {}).get("current_scope", "unknown")
        category = expected.get("category", "")

        # Video capabilities should be out_of_scope
        if category == "vision" and "video" in cap_id:
            if scope != "out_of_scope":
                report.add(
                    capability_id=cap_id,
                    gap_type=GapType.WRONG_SCOPE,
                    priority=Priority.P2,
                    detail=f"Video capability scope is '{scope}', expected 'out_of_scope'",
                    official_doc=expected.get("official_doc"),
                    expected="out_of_scope",
                    actual=scope,
                )

    return report


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    report = audit()
    summary = report.print_report()

    # Exit with non-zero if P0 gaps found
    p0_count = summary["by_priority"].get("P0", 0)
    print(f"\n{'='*80}")
    print(f"P0 gaps (immediate action required): {p0_count}")
    if p0_count > 0:
        print("WARNING: P0 gaps found — do not merge until resolved")
        sys.exit(1)
    else:
        print("No P0 gaps found.")
        sys.exit(0)
