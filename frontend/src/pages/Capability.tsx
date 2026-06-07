import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getModelsFor, riskCheck, type RiskCheckResult, type Model } from '../api'
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
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>({})
  const [riskCheckResult, setRiskCheckResult] = useState<RiskCheckResult | null>(null)
  const [riskCheckLoading, setRiskCheckLoading] = useState(false)
  const [examplePayload, setExamplePayload] = useState<Record<string, unknown>>({})

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
    if (cap) {
      setExamplePayload(cap.example ?? {})
      // Initialize confirmations state based on required confirmations
      const required = getRequiredConfirmations(cap)
      setConfirmations((prev) => {
        const next: Record<string, boolean> = {}
        for (const r of required) next[r] = prev[r] ?? false
        return next
      })
    }
    setRiskCheckResult(null)
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

      {/* Scope policy display */}
      {cap.scope_policy && (
        <div className={`mt-3 rounded border p-3 text-xs ${
          cap.scope_policy.current_scope === 'in_scope'
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : cap.scope_policy.current_scope === 'warning_only'
            ? 'border-amber-200 bg-amber-50 text-amber-800'
            : 'border-slate-200 bg-slate-50 text-slate-600'
        }`}>
          <div className="font-semibold mb-1">
            {cap.scope_policy.current_scope === 'in_scope'
              ? '✅ 当前 Token Plan 验收范围内能力'
              : cap.scope_policy.current_scope === 'warning_only'
              ? '⚠️ 仅做风险提示，不参与默认验收'
              : '🚫 当前项目范围外，不计入完成率和缺口'}
          </div>
          {cap.scope_policy.scope_reason && (
            <div className="text-xs opacity-80">{cap.scope_policy.scope_reason}</div>
          )}
          {cap.scope_policy.current_scope === 'warning_only' && (
            <div className="mt-1 text-xs">不展示默认验收入口，保留风险提示。</div>
          )}
          {cap.scope_policy.current_scope === 'out_of_scope' && (
            <div className="mt-1 text-xs">视频生成类能力，当前项目暂不考虑。</div>
          )}
        </div>
      )}

      {/* Billing policy display */}
      <section className="mt-4">
        {cap.billing_policy.requires_explicit_confirmation && (
          <div className="mb-3 flex items-start gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            <span className="text-rose-500 mt-0.5">⚠️</span>
            <div>
              <div className="font-semibold">该能力可能产生额外费用或高额度消耗，默认不会自动执行。</div>
              <div className="text-xs mt-0.5 text-rose-600">
                {cap.billing_policy.billing_note}
                {cap.billing_policy.official_pricing_note && ` ${cap.billing_policy.official_pricing_note}`}
              </div>
            </div>
          </div>
        )}

        <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
            <div>
              <span className="text-slate-500">计费类别：</span>
              <span className={`font-medium ${billingCategoryColor(cap.billing_policy.billing_category)}`}>
                {billingCategoryLabel(cap.billing_policy.billing_category)}
              </span>
            </div>
            <div>
              <span className="text-slate-500">可能额外收费：</span>
              <span className={cap.billing_policy.may_charge_extra ? 'text-rose-600 font-medium' : 'text-emerald-600'}>
                {cap.billing_policy.may_charge_extra ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">消耗 TokenPlan 额度：</span>
              <span className={cap.billing_policy.consumes_token_plan_quota ? 'text-amber-600' : 'text-slate-600'}>
                {cap.billing_policy.consumes_token_plan_quota ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">需二次确认：</span>
              <span className={cap.billing_policy.requires_explicit_confirmation ? 'text-rose-600 font-medium' : 'text-slate-600'}>
                {cap.billing_policy.requires_explicit_confirmation ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">需认证：</span>
              <span className={cap.billing_policy.requires_certification ? 'text-amber-600 font-medium' : 'text-slate-600'}>
                {cap.billing_policy.requires_certification ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">需上传素材：</span>
              <span className={cap.billing_policy.requires_uploaded_asset ? 'text-amber-600 font-medium' : 'text-slate-600'}>
                {cap.billing_policy.requires_uploaded_asset ? '是' : '否'}
              </span>
            </div>
          </div>
          {cap.billing_policy.billing_note && (
            <div className="mt-2 pt-2 border-t border-slate-200 text-slate-600">
              <span className="text-slate-500">收费说明：</span>{cap.billing_policy.billing_note}
            </div>
          )}
          {cap.billing_policy.official_pricing_note && (
            <div className="mt-1 text-slate-600">
              <span className="text-slate-500">官方价目：</span>{cap.billing_policy.official_pricing_note}
            </div>
          )}
        </div>
      </section>

      {/* Operation policy display */}
      <section className="mt-4">
        {cap.operation_policy.is_destructive && (
          <div className="mb-3 flex items-start gap-2 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
            <span className="text-red-500 mt-0.5">⚠️</span>
            <div>
              <div className="font-semibold">破坏性操作：执行前请确认资源 ID，删除后可能无法恢复。</div>
              {cap.operation_policy.operation_note && (
                <div className="text-xs mt-0.5 text-red-600">{cap.operation_policy.operation_note}</div>
              )}
            </div>
          </div>
        )}

        {cap.operation_policy.requires_uploaded_asset && !cap.operation_policy.is_destructive && (
          <div className="mb-3 flex items-start gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <span className="text-amber-500 mt-0.5">ℹ️</span>
            <div>
              <div className="font-semibold">素材要求：请确认素材来源、隐私、版权和文件大小。</div>
              {cap.operation_policy.operation_note && (
                <div className="text-xs mt-0.5 text-amber-600">{cap.operation_policy.operation_note}</div>
              )}
            </div>
          </div>
        )}

        {cap.operation_policy.requires_existing_task && (
          <div className="mb-3 flex items-start gap-2 rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
            <span className="text-blue-500 mt-0.5">ℹ️</span>
            <div>
              <div className="font-semibold">仅限已有任务：需要 task_id / file_id，不会自动创建任务。</div>
              {cap.operation_policy.operation_note && (
                <div className="text-xs mt-0.5 text-blue-600">{cap.operation_policy.operation_note}</div>
              )}
            </div>
          </div>
        )}

        {cap.operation_policy.is_long_running && !cap.operation_policy.requires_existing_task && (
          <div className="mb-3 flex items-start gap-2 rounded border border-purple-200 bg-purple-50 p-3 text-sm text-purple-800">
            <span className="text-purple-500 mt-0.5">⏱️</span>
            <div>
              <div className="font-semibold">长任务 / 高消耗：执行前请确认额度和预期成本。</div>
              {cap.operation_policy.operation_note && (
                <div className="text-xs mt-0.5 text-purple-600">{cap.operation_policy.operation_note}</div>
              )}
            </div>
          </div>
        )}

        <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
            <div>
              <span className="text-slate-500">操作风险类别：</span>
              <span className={`font-medium ${operationRiskColor(cap.operation_policy.operation_risk)}`}>
                {operationRiskLabel(cap.operation_policy.operation_risk)}
              </span>
            </div>
            <div>
              <span className="text-slate-500">破坏性操作：</span>
              <span className={cap.operation_policy.is_destructive ? 'text-red-600 font-medium' : 'text-slate-600'}>
                {cap.operation_policy.is_destructive ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">需要素材：</span>
              <span className={cap.operation_policy.requires_uploaded_asset ? 'text-amber-600 font-medium' : 'text-slate-600'}>
                {cap.operation_policy.requires_uploaded_asset ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">仅限已有任务：</span>
              <span className={cap.operation_policy.requires_existing_task ? 'text-blue-600 font-medium' : 'text-slate-600'}>
                {cap.operation_policy.requires_existing_task ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">长任务：</span>
              <span className={cap.operation_policy.is_long_running ? 'text-purple-600 font-medium' : 'text-slate-600'}>
                {cap.operation_policy.is_long_running ? '是' : '否'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">需操作确认：</span>
              <span className={cap.operation_policy.requires_operation_confirmation ? 'text-rose-600 font-medium' : 'text-slate-600'}>
                {cap.operation_policy.requires_operation_confirmation ? '是' : '否'}
              </span>
            </div>
            {cap.operation_policy.max_default_chars != null && (
              <div>
                <span className="text-slate-500">默认字符上限：</span>
                <span className="text-slate-700">{cap.operation_policy.max_default_chars} 字</span>
              </div>
            )}
            {cap.operation_policy.requires_confirmation_above_chars != null && (
              <div>
                <span className="text-slate-500">确认阈值：</span>
                <span className="text-slate-700">{cap.operation_policy.requires_confirmation_above_chars} 字以上需确认</span>
              </div>
            )}
            {cap.operation_policy.hard_block_above_chars_without_confirm != null && (
              <div>
                <span className="text-slate-500">无确认硬阻断：</span>
                <span className="text-slate-700">{cap.operation_policy.hard_block_above_chars_without_confirm} 字以上禁止执行</span>
              </div>
            )}
          </div>
          {cap.operation_policy.operation_note && (
            <div className="mt-2 pt-2 border-t border-slate-200 text-slate-600">
              <span className="text-slate-500">操作说明：</span>{cap.operation_policy.operation_note}
            </div>
          )}
        </div>
      </section>

      {/* 执行前确认门禁 */}
      {(() => {
        const required = getRequiredConfirmations(cap)
        if (required.length === 0) return null
        const allConfirmed = required.every((r) => confirmations[r])
        return (
          <section className="mt-4">
            <div className="rounded border border-rose-200 bg-rose-50 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-rose-500 text-lg">🔒</span>
                <span className="font-semibold text-rose-800">执行前需要确认</span>
              </div>
              <ul className="space-y-2 text-sm text-rose-700">
                {required.includes('confirm_paid') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_paid'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_paid: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认该能力可能产生额外费用
                    </label>
                  </li>
                )}
                {required.includes('confirm_high_cost') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_high_cost'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_high_cost: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认该能力属于高成本能力
                    </label>
                  </li>
                )}
                {required.includes('confirm_destructive') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_destructive'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_destructive: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认这是破坏性操作，资源删除后可能无法恢复
                    </label>
                  </li>
                )}
                {required.includes('confirm_asset_source') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_asset_source'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_asset_source: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认上传/引用素材来源合法，且已获得必要授权
                    </label>
                  </li>
                )}
                {required.includes('confirm_long_running') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_long_running'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_long_running: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认该能力是长任务，可能消耗较多额度
                    </label>
                  </li>
                )}
                {required.includes('confirm_existing_task') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_existing_task'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_existing_task: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认已提供已有任务 ID / 文件 ID
                    </label>
                  </li>
                )}
                {required.includes('confirm_quota') && (
                  <li>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmations['confirm_quota'] ?? false}
                        onChange={(e) => setConfirmations((p) => ({ ...p, confirm_quota: e.target.checked }))}
                        className="accent-rose-500"
                      />
                      我确认文本长度超过默认阈值，允许消耗更多额度
                    </label>
                  </li>
                )}
              </ul>
              <div className="mt-3 flex items-center gap-3">
                <button
                  className={`px-3 py-1.5 rounded text-xs font-medium ${
                    riskCheckLoading
                      ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                      : allConfirmed
                      ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                      : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  }`}
                  disabled={riskCheckLoading}
                  onClick={async () => {
                    if (!id) return
                    setRiskCheckLoading(true)
                    setRiskCheckResult(null)
                    try {
                      const result = await riskCheck(id, examplePayload, confirmations)
                      setRiskCheckResult(result)
                    } catch (err) {
                      setRiskCheckResult({
                        allowed: false,
                        blocked_reasons: [`检查失败: ${err instanceof Error ? err.message : String(err)}`],
                        required_confirmations: [],
                        warnings: [],
                      })
                    } finally {
                      setRiskCheckLoading(false)
                    }
                  }}
                >
                  {riskCheckLoading ? '检查中…' : allConfirmed ? '门禁检查 / Dry Run' : '请先完成执行前确认'}
                </button>
                {!allConfirmed && (
                  <span className="text-xs text-rose-600">请先勾选所有确认项</span>
                )}
              </div>

              {/* RiskGate 检查结果 */}
              {riskCheckResult && (
                <div className={`mt-3 rounded p-3 text-xs ${
                  riskCheckResult.allowed
                    ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                    : 'bg-red-50 border border-red-200 text-red-800'
                }`}>
                  <div className="font-semibold mb-1">
                    RiskGate 检查结果：{riskCheckResult.allowed ? '✅ 可以执行' : '❌ 已阻断'}
                  </div>
                  {riskCheckResult.blocked_reasons.length > 0 && (
                    <div className="mt-1">
                      <span className="font-medium">阻断原因：</span>
                      <ul className="list-disc list-inside mt-0.5">
                        {riskCheckResult.blocked_reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {riskCheckResult.required_confirmations.length > 0 && (
                    <div className="mt-1">
                      <span className="font-medium">需要确认项：</span>
                      {riskCheckResult.required_confirmations.join(', ')}
                    </div>
                  )}
                  {riskCheckResult.warnings.length > 0 && (
                    <div className="mt-1">
                      <span className="font-medium">警告：</span>
                      <ul className="list-disc list-inside mt-0.5">
                        {riskCheckResult.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-3 text-xs text-rose-600 bg-rose-100 rounded p-2">
                后端 RiskGate 会阻断未确认的执行请求。前端调用前请确保已在后端通过等效确认。
              </div>
            </div>
          </section>
        )
      })()}

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
          <div className="text-xs text-slate-500 mb-1">当前能力适用模型</div>
          <div className="text-[10px] text-slate-400 mb-2">这里只显示当前 capability 可用模型，不代表 Token Plan 全量模型。</div>
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
            <InvokePanel
              cap={cap}
              models={models}
              defaultPayload={cap.example}
              confirmations={confirmations}
              riskCheckResult={riskCheckResult}
              setRiskCheckResult={setRiskCheckResult}
            />
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

function billingCategoryLabel(cat: string): string {
  const map: Record<string, string> = {
    normal_token_plan_test: '正常 TokenPlan 测试',
    quota_sensitive: '配额敏感',
    paid_confirm_required: '需确认付费',
    high_cost_confirm_required: '高成本需确认',
    asset_required_confirm_required: '素材/认证待准备',
  }
  return map[cat] ?? cat
}

function billingCategoryColor(cat: string): string {
  const map: Record<string, string> = {
    normal_token_plan_test: 'text-emerald-600',
    quota_sensitive: 'text-amber-600',
    paid_confirm_required: 'text-rose-600',
    high_cost_confirm_required: 'text-red-600',
    asset_required_confirm_required: 'text-orange-600',
  }
  return map[cat] ?? 'text-slate-600'
}

function operationRiskLabel(risk: string): string {
  const map: Record<string, string> = {
    normal: '普通操作',
    destructive: '破坏性操作',
    asset_required: '素材型操作',
    existing_task_only: '仅限已有任务',
    long_running: '长任务',
    quota_guarded: '额度保护',
  }
  return map[risk] ?? risk
}

function operationRiskColor(risk: string): string {
  const map: Record<string, string> = {
    normal: 'text-emerald-600',
    destructive: 'text-red-600',
    asset_required: 'text-amber-600',
    existing_task_only: 'text-blue-600',
    long_running: 'text-purple-600',
    quota_guarded: 'text-orange-600',
  }
  return map[risk] ?? 'text-slate-600'
}

function getRequiredConfirmations(cap: import('../api').Capability): string[] {
  const required: string[] = []
  const bp = cap.billing_policy
  const op = cap.operation_policy

  if (bp.may_charge_extra) required.push('confirm_paid')
  if (bp.billing_category === 'high_cost_confirm_required') required.push('confirm_high_cost')
  if (op.is_destructive) required.push('confirm_destructive')
  if (op.requires_uploaded_asset) required.push('confirm_asset_source')
  if (op.is_long_running) required.push('confirm_long_running')
  if (op.requires_existing_task) required.push('confirm_existing_task')
  if (cap.id === 'tts-async') required.push('confirm_quota')

  return required
}
