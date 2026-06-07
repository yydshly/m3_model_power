export type AssetPreviewItem =
  | { kind: 'audio'; url: string; label: string }
  | { kind: 'image'; url: string; label: string }
  | { kind: 'file'; label: string; file_id?: string; filename?: string; mime_type?: string; content_length?: number }

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
    const urlFieldNames = ['audio_url', 'audio', 'voice_url', 'speech_url', 'url', 'asset_url', 'download_url', 'image_url', 'img_url', 'file_url', 'content_url']
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
