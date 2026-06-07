import { extractAssetRefs, type AssetPreviewItem } from './assetResultUtils'
import { JsonView } from './JsonView'

function AudioPreview({ item }: { item: AssetPreviewItem & { kind: 'audio' } }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
      <p className="text-xs text-slate-500 mb-2 font-mono truncate" title={item.url}>🔊 {item.label}</p>
      <audio controls src={item.url} className="w-full h-8" />
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
}

export default function AssetResultPreview({ data }: Props) {
  const assets = extractAssetRefs(data)

  if (assets.length === 0) {
    return <JsonView data={data} />
  }

  return (
    <div className="space-y-3">
      {assets.map((asset, i) => {
        if (asset.kind === 'audio') return <AudioPreview key={i} item={asset} />
        if (asset.kind === 'image') return <ImagePreview key={i} item={asset} />
        if (asset.kind === 'file') return <FilePreview key={i} item={asset} />
        return null
      })}
      <details className="mt-2">
        <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
          完整结果（{assets.length} 个资产）
        </summary>
        <div className="mt-2">
          <JsonView data={data} />
        </div>
      </details>
    </div>
  )
}
