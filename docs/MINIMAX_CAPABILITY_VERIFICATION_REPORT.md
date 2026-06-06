# MiniMax 能力验收报告

> 生成时间: 2026-06-06 07:48 UTC
> 级别: medium（4项，均成功）

## 验收摘要

| 状态 | 数量 |
|---|
| success | 4 |

## 详细结果

| 能力 ID | Level | 状态 | HTTP | 延迟(ms) | 模型 | 输出类型 | 资产已存 | 关键字段 |
|---|---|---|---|---|---|---|---|---|
| image-t2i | medium | success | 200 | 15234 | image-01 | image | True | urls=1 ok=1 fail=0 |
| lyrics-gen | medium | success | 200 | 3110 | None | text | True | title=夏夜微风 tags=民谣, 轻快, 夏天, 傍晚, 浪漫 |
| music-gen | medium | success | 200 | 44905 | music-2.6 | music | True | hex=True dur=72489ms fmt=mp3 br=256000 |
| tts-sync | medium | success | 200 | 1625 | speech-02-turbo | audio | True | size=63348B fmt=mp3 len=3852ms |

## 资产验证结果

- **tts-sync**: audio hex解码成功，63348字节，MP3格式，时长3852ms，31字符
- **image-t2i**: image_urls返回1个URL，success_count=1，failed_count=0
- **lyrics-gen**: 歌词生成成功，flat响应结构，song_title/style_tags/lyrics均存在
- **music-gen**: audio hex返回72489ms MP3音频，bitrate=256000，未下载到文件

## 已知响应结构

- **tts-sync**: data.audio 是 hex；extra_info 含 audio_format/audio_length 等
- **image-t2i**: data.image_urls 是列表；metadata 含 success_count/failed_count
- **lyrics-gen**: flat 结构（无 data 包装），song_title/style_tags/lyrics 在顶层
- **music-gen**: data.audio 是 hex；extra_info 含 music_duration/bitrate

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py --level medium --confirm-cost` 自动生成*