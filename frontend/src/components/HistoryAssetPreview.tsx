/**
 * HistoryAssetPreview — renders asset previews from history result_summary.
 *
 * Reuses the same visual style as AssetResultPreview but accepts pre-extracted
 * assets from result_summary, so it works even when the full raw response
 * is not stored in history.
 */
import type { TestConsoleHistoryItem } from '../api'

type HistoryAsset = NonNullable<NonNullable<TestConsoleHistoryItem['result_summary']>['assets']>[number]

function HistoryAudioPreview({ item }: { item: HistoryAsset & { type: 'audio' } }) {
  if (!item.url) return null
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-2 font-mono truncate" title={item.url}>🔊 {item.label}</p>
      <audio controls src={item.url} className="w-full h-8" />
    </div>
  )
}

function HistoryImagePreview({ item }: { item: HistoryAsset & { type: 'image' } }) {
  if (!item.url) return null
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-2 font-mono truncate" title={item.url}>🖼 {item.label}</p>
      <img
        src={item.url}
        alt={item.label}
        className="max-w-full max-h-48 rounded object-contain"
        onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
      />
      <div className="mt-1 flex gap-3">
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-xs text-sky-600 hover:underline">
          打开图片
        </a>
      </div>
    </div>
  )
}

function HistoryFilePreview({ item }: { item: HistoryAsset & { type: 'file' } }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-1">📄 {item.label || '文件'}</p>
      <div className="space-y-0.5 text-xs font-mono">
        {item.file_id && <div>file_id: <span className="text-slate-700">{item.file_id}</span></div>}
        {item.filename && <div>filename: <span className="text-slate-700">{item.filename}</span></div>}
        {item.mime_type && <div>mime_type: <span className="text-slate-700">{item.mime_type}</span></div>}
        {item.content_length != null && (
          <div>size: <span className="text-slate-700">{item.content_length} bytes</span></div>
        )}
      </div>
    </div>
  )
}

type Props = {
  result_summary: TestConsoleHistoryItem['result_summary']
  /** Fallback: also show raw result as JSON in a collapsible */
  rawResult?: Record<string, unknown>
}

export default function HistoryAssetPreview({ result_summary, rawResult }: Props) {
  const assets = result_summary?.assets ?? []

  if (!assets.length) {
    return (
      <div className="text-xs text-slate-500">
        {result_summary?.output_type && result_summary.output_type !== 'unknown'
          ? `output_type: ${result_summary.output_type}（无资产 URL）`
          : '无资产结果'}
        {result_summary?.text_preview && (
          <div className="mt-1 text-slate-600 italic truncate">
            文本预览：{result_summary.text_preview}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {assets.map((asset, i) => {
        if (asset.type === 'image') return <HistoryImagePreview key={i} item={asset as HistoryAsset & { type: 'image' }} />
        if (asset.type === 'audio') return <HistoryAudioPreview key={i} item={asset as HistoryAsset & { type: 'audio' }} />
        if (asset.type === 'file') return <HistoryFilePreview key={i} item={asset as HistoryAsset & { type: 'file' }} />
        return null
      })}
      {rawResult && (
        <details className="mt-2">
          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
            历史记录摘要 JSON
          </summary>
          <pre className="mt-1 text-[10px] bg-slate-100 rounded p-2 overflow-auto max-h-40 whitespace-pre-wrap">
            {JSON.stringify(rawResult, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}
