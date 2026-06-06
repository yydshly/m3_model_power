import { QuotaBadge, TierBadge } from '../components/StatusBadge'
import { useRegistry } from '../store'

/** 模型清单总览，跨 family 一目了然，便于挑选用什么模型干什么活。 */
export default function ModelsPage() {
  const { registry } = useRegistry()
  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>

  const byFamily = registry.models.reduce<Record<string, typeof registry.models>>((acc, m) => {
    if (!m.enabled) return acc
    ;(acc[m.family] = acc[m.family] ?? []).push(m)
    return acc
  }, {})

  const FAMILY_LABEL: Record<string, string> = {
    chat: '对话 / LLM',
    speech: '语音合成',
    image: '图像',
    video: '视频',
    music: '音乐',
  }

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-2xl font-semibold text-slate-900">模型清单</h1>
      <p className="text-sm text-slate-600 mt-1">
        在 <code className="font-mono">backend/config/models.yaml</code> 中维护。新增模型只需追加条目并 POST /api/registry/reload。
      </p>
      {Object.entries(byFamily).map(([fam, list]) => (
        <section key={fam} className="mt-6">
          <h2 className="text-base font-semibold text-slate-800 mb-2">{FAMILY_LABEL[fam] ?? fam}</h2>
          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="text-left px-3 py-2">ID</th>
                  <th className="text-left px-3 py-2">名称</th>
                  <th className="text-left px-3 py-2">档位</th>
                  <th className="text-left px-3 py-2">计费</th>
                  <th className="text-left px-3 py-2">特性</th>
                  <th className="text-left px-3 py-2">说明</th>
                </tr>
              </thead>
              <tbody>
                {list.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{m.id}</td>
                    <td className="px-3 py-2">{m.label}</td>
                    <td className="px-3 py-2"><TierBadge tier={m.tier} /></td>
                    <td className="px-3 py-2"><QuotaBadge eligible={m.quota_eligible} /></td>
                    <td className="px-3 py-2 text-xs text-slate-600">
                      {m.multimodal && <span className="mr-2 text-indigo-600">多模态</span>}
                      {m.context && <span className="mr-2">{(m.context / 1000).toFixed(0)}k 上下文</span>}
                      {m.protocols.length > 0 && <span className="text-slate-500">协议：{m.protocols.join(' / ')}</span>}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{m.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}
