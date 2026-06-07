export type AssetPreviewItem =
  | { kind: 'audio'; url: string; label: string }
  | { kind: 'image'; url: string; label: string }
  | { kind: 'file'; label: string; file_id?: string; filename?: string; mime_type?: string; content_length?: number }

// ── Audio extraction ────────────────────────────────────────────────────────

/**
 * Unified audio source descriptor.
 * kind values:
 *   'url'       — HTTP/HTTPS URL to an audio file
 *   'data_url'  — data:audio/... URL (already a browser-playable data URI)
 *   'base64'    — raw base64-encoded bytes (converted to data:audio/mpeg;base64,...)
 *   'hex'       — hex-encoded bytes (converted to a Blob URL)
 *   'task'      — task status info (no playable audio yet)
 */
export type AudioSource =
  | { kind: 'url'; src: string }
  | { kind: 'data_url'; src: string }
  | { kind: 'base64'; src: string }
  | { kind: 'hex'; src: string }
  | { kind: 'task'; status: number; message: string; duration_sec?: number; sample_rate?: number; channel?: number; file_size_bytes?: number }

const AUDIO_MAX_DEPTH = 5

// MP3 magic bytes
const MP3_MAGICS = ['494433', 'fffb', 'fff3', 'fff9'] // ID3, various MP3 frames
// WAV magic bytes
const WAV_MAGIC = '52494646' // "RIFF"

function isValidHex(s: string): boolean {
  return /^[0-9a-fA-F]+$/.test(s) && s.length % 2 === 0
}

function hexStartsWith(hex: string, magics: string[]): boolean {
  const prefix = hex.slice(0, 8).toLowerCase()
  return magics.some(m => prefix.startsWith(m.toLowerCase()))
}

function isLikelyAudioHex(hex: string): boolean {
  return hexStartsWith(hex, [...MP3_MAGICS, WAV_MAGIC])
}

function hexToBlobUrl(hex: string, mime = 'audio/mpeg'): string {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  }
  const blob = new Blob([bytes], { type: mime })
  return URL.createObjectURL(blob)
}

function _extractAudio(data: unknown, depth: number): AudioSource | null {
  if (depth > AUDIO_MAX_DEPTH || data == null || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  // 1. Direct URL fields (most common — check first for speed)
  for (const key of ['audio_url', 'music_url', 'voice_url', 'speech_url', 'audio_file', 'url', 'file_url']) {
    const val = d[key]
    if (typeof val === 'string' && val) {
      if (val.startsWith('http://') || val.startsWith('https://')) {
        return { kind: 'url', src: val }
      }
      if (val.startsWith('data:audio/')) {
        return { kind: 'data_url', src: val }
      }
    }
  }

  // 2. Data URL audio
  for (const key of ['audio', 'music', 'voice', 'speech']) {
    const val = d[key]
    if (typeof val === 'string' && val) {
      if (val.startsWith('data:audio/')) {
        return { kind: 'data_url', src: val }
      }
    }
  }

  // 3. Base64 audio — only treat as audio if it looks like base64 and is reasonably long
  for (const key of ['audio_base64', 'audio', 'music_data', 'audio_data']) {
    const val = d[key]
    if (typeof val === 'string' && val && val.length > 100) {
      // Must look like valid base64 (alphanumeric + '+' + '/' + '=')
      if (/^[A-Za-z0-9+/=]{50,}$/.test(val)) {
        if (val.startsWith('data:audio/')) {
          return { kind: 'data_url', src: val }
        }
        return { kind: 'base64', src: val }
      }
    }
  }

  // 4. Hex audio — must be hex and start with known audio magic bytes
  for (const key of ['hex', 'audio_hex', 'music_hex', 'audio_data_hex']) {
    const val = d[key]
    if (typeof val === 'string' && val && isValidHex(val) && isLikelyAudioHex(val)) {
      return { kind: 'hex', src: val }
    }
  }

  // 5. Task status (music-gen polling result) — status=2 means task done but audio may be elsewhere
  //    Look for status + extra_info as the "task" variant
  if ('status' in d && typeof d.status === 'number') {
    const status = Number(d.status)
    const extra = d.extra_info as Record<string, unknown> | undefined
    const durationMs = extra?.music_duration as number | undefined
    const durationSec = durationMs !== undefined ? durationMs / 1000 : undefined
    const sampleRate = extra?.music_sample_rate as number | undefined
    const channel = extra?.music_channel as number | undefined
    const fileSize = extra?.music_size as number | undefined
    const baseResp = d.base_resp as Record<string, unknown> | undefined
    const statusMsg = (baseResp?.status_msg as string) || (status === 2 ? '任务已完成，请查询结果' : `状态: ${status}`)

    return {
      kind: 'task',
      status,
      message: statusMsg,
      duration_sec: durationSec,
      sample_rate: sampleRate,
      channel,
      file_size_bytes: fileSize,
    }
  }

  // 6. Recurse into common containers
  for (const key of ['data', 'result', 'output', 'response', 'body', 'content']) {
    const child = d[key]
    if (child != null && typeof child === 'object') {
      const found = _extractAudio(child, depth + 1)
      if (found) return found
    }
  }

  // 7. Recurse into arrays
  for (const val of Object.values(d)) {
    if (Array.isArray(val)) {
      for (const item of val) {
        const found = _extractAudio(item, depth + 1)
        if (found) return found
      }
    }
  }

  return null
}

export function extractAudioSource(data: unknown): AudioSource | null {
  return _extractAudio(data, 0)
}

export function audioSourceToSrc(audio: AudioSource): string {
  if (audio.kind === 'url') return audio.src
  if (audio.kind === 'data_url') return audio.src
  if (audio.kind === 'base64') return `data:audio/mpeg;base64,${audio.src}`
  if (audio.kind === 'hex') return hexToBlobUrl(audio.src)
  return ''
}

// ── Asset extraction (original logic) ───────────────────────────────────────

const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac']
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.svg']

function isAudioUrl(url: string): boolean {
  const lower = url.toLowerCase()
  return AUDIO_EXTENSIONS.some(ext => lower.endsWith(ext)) ||
    lower.includes('audio') || lower.includes('mp3') || lower.includes('wav') ||
    lower.includes('voice') || lower.includes('speech')
}

function isImageUrl(url: string): boolean {
  const lower = url.toLowerCase()
  return IMAGE_EXTENSIONS.some(ext => lower.endsWith(ext)) ||
    lower.includes('image') || lower.includes('img') ||
    lower.includes('png') || lower.includes('jpg') || lower.includes('jpeg')
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen) + '...'
}

const MAX_DEPTH = 4
const MAX_ITEMS = 10
const MAX_STR_LEN = 300
// MAX_URL_LEN is for display labels only. Never truncate the actual media src URL.
const MAX_URL_LEN = 120

interface FoundAssets {
  items: AssetPreviewItem[]
  count: number
}

function _extract(current: unknown, depth: number, found: FoundAssets): void {
  if (found.count >= MAX_ITEMS) return
  if (depth > MAX_DEPTH) return

  if (typeof current === 'string') {
    const url = current.trim()
    if (url.startsWith('http://') || url.startsWith('https://')) {
      if (isAudioUrl(url)) {
        found.items.push({ kind: 'audio', url, label: truncate(url, MAX_URL_LEN) })
        found.count++
      } else if (isImageUrl(url)) {
        found.items.push({ kind: 'image', url, label: truncate(url, MAX_URL_LEN) })
        found.count++
      }
    }
    return
  }

  if (typeof current === 'object' && current !== null) {
    // Handle arrays — recurse into each element
    if (Array.isArray(current)) {
      for (const item of current) {
        if (found.count >= MAX_ITEMS) break
        _extract(item, depth + 1, found)
      }
      return
    }

    // Handle dicts — check for file/audio/image fields, then recurse
    const rec = current as Record<string, unknown>

    // File fields (check before recursing)
    if ('file_id' in rec && typeof rec.file_id === 'string') {
      found.items.push({
        kind: 'file',
        label: truncate(rec.file_id as string, MAX_STR_LEN),
        file_id: truncate(rec.file_id as string, MAX_STR_LEN),
        filename: rec.filename ? truncate(String(rec.filename), MAX_STR_LEN) : undefined,
        mime_type: rec.mime_type ? String(rec.mime_type) : undefined,
        content_length: rec.content_length ? Number(rec.content_length) : undefined,
      })
      found.count++
    }

    // Check for URL-like string fields
    const urlFieldNames = ['audio_url', 'music_url', 'voice_url', 'speech_url', 'audio', 'voice', 'url', 'asset_url', 'download_url', 'image_url', 'img_url', 'file_url', 'content_url']
    for (const field of urlFieldNames) {
      if (field in rec && typeof rec[field] === 'string') {
        const val = rec[field] as string
        if ((val.startsWith('http://') || val.startsWith('https://')) && found.count < MAX_ITEMS) {
          if (isAudioUrl(val)) {
            found.items.push({ kind: 'audio', url: val, label: `${field}: ${truncate(val, MAX_URL_LEN)}` })
            found.count++
          } else if (isImageUrl(val)) {
            found.items.push({ kind: 'image', url: val, label: `${field}: ${truncate(val, MAX_URL_LEN)}` })
            found.count++
          }
        }
      }
    }

    // Recurse into nested objects (but not strings/numbers/bools)
    for (const [, v] of Object.entries(rec)) {
      if (found.count >= MAX_ITEMS) break
      // Skip already-handled scalar fields
      if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') continue
      if (Array.isArray(v)) {
        for (const item of v) {
          if (found.count >= MAX_ITEMS) break
          _extract(item, depth + 1, found)
        }
      } else if (typeof v === 'object' && v !== null) {
        _extract(v, depth + 1, found)
      }
    }
  }
}

export function extractAssetRefs(data: unknown): AssetPreviewItem[] {
  const found: FoundAssets = { items: [], count: 0 }
  _extract(data, 0, found)
  return found.items
}
