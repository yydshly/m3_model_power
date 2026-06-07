import { useRef, useState } from 'react'
import { extractAssetRefs, extractAudioSource, type AssetPreviewItem, type AudioSource } from './assetResultUtils'
import { JsonView } from './JsonView'

// ── Audio preview with error handling ──────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function AudioTaskStatus({ audio, src }: { audio: Extract<AudioSource, { kind: 'task' }>; src?: string }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-orange-50">
      <p className="text-xs text-orange-700 font-medium">🎵 音乐生成任务状态</p>
      <p className="text-xs text-orange-600 mt-1">{audio.message}</p>
      <div className="mt-2 space-y-1 text-xs text-slate-600">
        {audio.duration_sec !== undefined && (
          <div>时长：{audio.duration_sec.toFixed(1)} 秒</div>
        )}
        {audio.sample_rate !== undefined && (
          <div>采样率：{audio.sample_rate} Hz</div>
        )}
        {audio.channel !== undefined && (
          <div>声道：{audio.channel === 2 ? '立体声' : audio.channel === 1 ? '单声道' : audio.channel}</div>
        )}
        {audio.file_size_bytes !== undefined && (
          <div>文件大小：{formatBytes(audio.file_size_bytes)}</div>
        )}
      </div>
      {src && (
        <div className="mt-2">
          <a href={src} target="_blank" rel="noopener noreferrer" className="text-xs text-sky-600 hover:underline">
            打开结果链接
          </a>
        </div>
      )}
      <p className="text-[10px] text-slate-400 mt-2">
        当前响应未包含可直接播放的音频数据。状态码 {audio.status} 表示任务已提交，请通过结果查询接口获取音频。
      </p>
    </div>
  )
}

function AudioPreviewWithError({ item }: { item: AssetPreviewItem & { kind: 'audio' } }) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [loadError, setLoadError] = useState(false)

  function handleLoadedMetadata() {
    const el = audioRef.current
    if (el && (isNaN(el.duration) || el.duration === 0)) {
      setLoadError(true)
    }
  }

  function handleError() {
    setLoadError(true)
  }

  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-2 font-mono truncate" title={item.url}>🔊 {item.label}</p>
      <audio
        ref={audioRef}
        controls
        src={item.url}
        className="w-full h-8"
        onLoadedMetadata={handleLoadedMetadata}
        onError={handleError}
      />
      {loadError && (
        <p className="text-[10px] text-red-500 mt-1">
          浏览器未能解析该音频。可能是编码格式不支持，或接口返回的不是最终音频文件。请查看完整 JSON。
        </p>
      )}
    </div>
  )
}

function ImagePreview({ item }: { item: AssetPreviewItem & { kind: 'image' } }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-2 font-mono truncate" title={item.url}>🖼 {item.label}</p>
      <img
        src={item.url}
        alt={item.label}
        className="max-w-full max-h-48 rounded object-contain"
        onError={e => {
          (e.target as HTMLImageElement).style.display = 'none'
        }}
      />
    </div>
  )
}

function FilePreview({ item }: { item: AssetPreviewItem & { kind: 'file' } }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-1">📄 文件信息</p>
      <div className="space-y-0.5 text-xs font-mono">
        {item.file_id && <div>file_id: <span className="text-slate-700">{item.file_id}</span></div>}
        {item.filename && <div>filename: <span className="text-slate-700">{item.filename}</span></div>}
        {item.mime_type && <div>mime_type: <span className="text-slate-700">{item.mime_type}</span></div>}
        {item.content_length != null && (
          <div>content_length: <span className="text-slate-700">{item.content_length} bytes</span></div>
        )}
      </div>
    </div>
  )
}

type Props = {
  /** The raw result data from invoke */
  data: unknown
  /** Optional unified audio source (used by ResultBanner to avoid double-extraction) */
  audioSource?: AudioSource | null
  /** Skip the AudioTaskStatus card if AudioBanner already showed it */
  skipAudioTaskCard?: boolean
  /** Skip rendering primary assets of these kinds (e.g. ['image'] when ImageComparePreview already shows them) */
  skipPrimaryKinds?: string[]
}

export default function AssetResultPreview({ data, audioSource: providedAudio, skipAudioTaskCard, skipPrimaryKinds }: Props) {
  const assets = extractAssetRefs(data)
  const audioSource = providedAudio ?? extractAudioSource(data)

  // Filter out assets whose kinds should be skipped
  const filteredAssets = skipPrimaryKinds
    ? assets.filter(a => !skipPrimaryKinds.includes(a.kind))
    : assets

  if (!filteredAssets.length && !audioSource) {
    return <JsonView data={data} />
  }

  return (
    <div className="space-y-3">
      {/* Task status (music-gen pending results) — skip if AudioBanner already showed it */}
      {!skipAudioTaskCard && audioSource?.kind === 'task' && (
        <AudioTaskStatus audio={audioSource} />
      )}

      {/* Standard asset previews */}
      {filteredAssets.map((asset, i) => {
        if (asset.kind === 'audio') return <AudioPreviewWithError key={i} item={asset} />
        if (asset.kind === 'image') return <ImagePreview key={i} item={asset} />
        if (asset.kind === 'file') return <FilePreview key={i} item={asset} />
        return null
      })}
      <details className="mt-2">
        <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
          完整结果{filteredAssets.length > 0 ? `（${filteredAssets.length} 个资产）` : ''}
        </summary>
        <div className="mt-2">
          <JsonView data={data} />
        </div>
      </details>
    </div>
  )
}
