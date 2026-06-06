import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getModelsFor, type Model } from '../api'
import { AsyncVideoPanel } from '../components/AsyncVideoPanel'
import { ChatPanel } from '../components/ChatPanel'
import { CostBadge, CostNotice } from '../components/CostBadge'
import { InvokePanel } from '../components/InvokePanel'
import { QuotaBadge, StatusBadge, TierBadge } from '../components/StatusBadge'
import { StreamPanel } from '../components/StreamPanel'
import { TtsWsPanel } from '../components/TtsWsPanel'
import { UploadPanel } from '../components/UploadPanel'
import { useRegistry } from '../store'

type Mode = 'invoke' | 'stream' | 'upload'

export default function CapabilityPage() {
  const { id } = useParams<{ id: string }>()
  const { registry } = useRegistry()
  const [models, setModels] = useState<Model[]>([])
  const [mode, setMode] = useState<Mode>('invoke')

  useEffect(() => {
    if (id) {
      getModelsFor(id)
        .then((ms) => {
          // 走配额 → 旗舰/HD → Turbo → 标准 → 旧版排序，下拉第一个就是该用的
          const order: Record<string, number> = { highspeed: 0, flagship: 1, hd: 1, turbo: 2, standard: 3, legacy: 4, deprecated: 5 }
          ms.sort((a, b) => {
            if (a.quota_eligible !== b.quota_eligible) return a.quota_eligible ? -1 : 1
            return order[a.tier] - order[b.tier]
          })
          setModels(ms)
        })
        .catch(() => setModels([]))
    }
    const cap = registry?.capabilities.find((c) => c.id === id)
    if (cap?.category === 'chat' && cap.streaming) setMode('stream')
    else setMode('invoke')
  }, [id, registry])

  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  const cap = registry.capabilities.find((c) => c.id === id)
  if (!cap) return <div className="p-8 text-sm text-red-600">能力不存在：{id}</div>

  // multipart 能力强制 upload；其余尊重用户选择
  const effectiveMode: Mode = cap.multipart ? 'upload' : mode

  return (
    <div className="p-8 max-w-4xl">
      <Link to={`/category/${cap.category}`} className="text-xs text-slate-500 hover:text-slate-900">
        ← 返回 {registry.categories.find((c) => c.id === cap.category)?.label}
      </Link>
      <div className="mt-2 flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-semibold text-slate-900">{cap.label}</h1>
        <StatusBadge status={cap.status} />
        <CostBadge level={cap.cost_level} />
        {cap.streaming && <span className="text-xs text-sky-600">流式</span>}
        {cap.async_job && <span className="text-xs text-purple-600">异步任务</span>}
        {cap.multipart && <span className="text-xs text-rose-600">上传</span>}
      </div>
      <p className="text-sm text-slate-600 mt-2">{cap.desc}</p>
      {cap.notes && <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">{cap.notes}</div>}

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
        <span>
          <span className="text-slate-400">上游：</span>
          <span className="font-mono">{cap.method} {cap.mm_path}</span>
        </span>
        <a className="text-sky-600 hover:underline" href={cap.doc_url} target="_blank" rel="noreferrer">
          📄 官方文档
        </a>
        {cap.tags.map((t) => (
          <span key={t} className="px-1.5 py-0.5 bg-slate-100 rounded">#{t}</span>
        ))}
      </div>

      {cap.requires_model === false ? (
        <section className="mt-6">
          <div className="text-xs text-slate-400 italic">该能力无需选择模型</div>
        </section>
      ) : models.length > 0 ? (
        <section className="mt-6">
          <div className="text-xs text-slate-500 mb-2">适用模型（来自 models.yaml）</div>
          <div className="flex flex-wrap gap-2">
            {models.map((m) => (
              <span key={m.id} className="inline-flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 rounded text-xs">
                <span className="font-medium">{m.label}</span>
                <TierBadge tier={m.tier} />
                <QuotaBadge eligible={m.quota_eligible} />
                {(m.input_modalities?.includes('image') || m.input_modalities?.includes('video')) && <span className="text-[10px] text-indigo-600">多模态</span>}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <hr className="my-6 border-slate-200" />

      {cap.status === 'unsupported' && (
        <Notice tone="slate">当前订阅档位不支持此能力。如需启用请升级套餐或修改 capabilities.yaml。</Notice>
      )}
      {cap.status === 'planned' && (
        <Notice tone="amber">
          该能力已在能力图谱中声明，但工作台尚未实现调用界面。
          可参考<a className="underline ml-1" href={cap.doc_url} target="_blank" rel="noreferrer">官方文档</a>
          直接使用上游 <code className="font-mono">{cap.method} {cap.mm_path}</code>。
          {cap.notes && <div className="mt-2 text-amber-700">{cap.notes}</div>}
        </Notice>
      )}
      {cap.status === 'implemented' && !cap.has_handler && !cap.multipart && cap.id !== 'tts-ws' && (
        <Notice tone="amber">YAML 声明为 implemented 但后端未注册 handler，请检查 backend/app/capabilities/*.py。</Notice>
      )}
      {cap.status === 'implemented' && (cap.has_handler || cap.multipart || cap.id === 'tts-ws') && (
        <>
          <CostNotice cap={cap} />
          {(cap.streaming || cap.multipart) && (
            <div className="mb-4 inline-flex border border-slate-300 rounded overflow-hidden text-xs">
              {!cap.multipart && (
                <button
                  className={`px-3 py-1 ${effectiveMode === 'invoke' ? 'bg-slate-900 text-white' : 'bg-white'}`}
                  onClick={() => setMode('invoke')}
                >
                  同步调用
                </button>
              )}
              {cap.streaming && (
                <button
                  className={`px-3 py-1 ${effectiveMode === 'stream' ? 'bg-sky-600 text-white' : 'bg-white'}`}
                  onClick={() => setMode('stream')}
                >
                  流式调用
                </button>
              )}
              {cap.multipart && (
                <button
                  className={`px-3 py-1 ${effectiveMode === 'upload' ? 'bg-rose-600 text-white' : 'bg-white'}`}
                  onClick={() => setMode('upload')}
                >
                  上传
                </button>
              )}
            </div>
          )}
          {effectiveMode === 'invoke' && cap.id === 'tts-ws' && (
            <TtsWsPanel cap={cap} models={models} />
          )}
          {effectiveMode === 'invoke' && cap.has_handler && cap.async_job && cap.category === 'vision' && (
            <AsyncVideoPanel cap={cap} models={models} />
          )}
          {effectiveMode === 'invoke' && cap.has_handler && !(cap.async_job && cap.category === 'vision') && cap.id !== 'tts-ws' && (
            <InvokePanel cap={cap} models={models} defaultPayload={cap.example} />
          )}
          {effectiveMode === 'stream' && cap.category === 'chat' && <ChatPanel cap={cap} models={models} />}
          {effectiveMode === 'stream' && cap.category !== 'chat' && <StreamPanel cap={cap} models={models} />}
          {effectiveMode === 'upload' && <UploadPanel cap={cap} />}
        </>
      )}
    </div>
  )
}

function Notice({ tone, children }: { tone: 'amber' | 'slate'; children: React.ReactNode }) {
  const cls = tone === 'amber' ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-slate-50 border-slate-200 text-slate-700'
  return <div className={`rounded border p-4 text-sm ${cls}`}>{children}</div>
}
