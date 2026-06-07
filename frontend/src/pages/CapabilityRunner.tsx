import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { invoke, riskCheck, type InvokeResult, type RiskCheckResult } from '../api'
import AssetResultPreview from '../components/AssetResultPreview'

// ── Types ───────────────────────────────────────────────────────────────────

type FormField = {
  type: 'input' | 'textarea' | 'select'
  label: string
  default: string
  placeholder?: string
  max_chars?: number
  options?: Array<{ value: string; label: string }>
}

type FormSchema = Record<string, FormField>

type NextStep = {
  capability_id: string
  label: string
  note: string
  blocked: boolean
}

type RunnerTemplate = {
  capability_id: string
  label: string
  description: string
  suitable_for: string[]
  risk_level: string
  form_schema: FormSchema
  payload_template: Record<string, unknown>
  next_steps: NextStep[]
}

// ── InvokeResult type guard ─────────────────────────────────────────────────────

function isOk(result: InvokeResult): result is { ok: true; data: unknown } {
  return 'ok' in result && result.ok === true
}

// ── Risk level badge ─────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, { text: string; cls: string }> = {
  safe: { text: '低风险', cls: 'bg-emerald-100 text-emerald-700' },
  low: { text: '低风险', cls: 'bg-emerald-100 text-emerald-700' },
  medium: { text: '中等风险', cls: 'bg-amber-100 text-amber-700' },
  guarded: { text: '需确认', cls: 'bg-amber-100 text-amber-700' },
}

function RiskBadge({ level }: { level: string }) {
  const { text, cls } = RISK_BADGE[level] ?? { text: level, cls: 'bg-slate-100 text-slate-600' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${cls}`}>{text}</span>
}

// ── Status indicators ──────────────────────────────────────────────────────────

type RunState = 'idle' | 'checking' | 'running' | 'done' | 'error'

function RunButton({ state, label, onClick }: { state: RunState; label: string; onClick?: () => void }) {
  if (state === 'checking' || state === 'running') {
    return (
      <button disabled className="px-4 py-2 rounded-lg bg-slate-400 text-white cursor-not-allowed text-sm">
        {state === 'checking' ? '安全检查中…' : '执行中…'}
      </button>
    )
  }
  return (
    <button onClick={onClick} className="px-4 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-700 transition text-sm">
      {label}
    </button>
  )
}

// ── Form renderer ─────────────────────────────────────────────────────────────

function RunnerForm({
  schema,
  values,
  onChange,
}: {
  schema: FormSchema
  values: Record<string, string>
  onChange: (key: string, val: string) => void
}) {
  return (
    <div className="space-y-3">
      {Object.entries(schema).map(([key, field]) => (
        <div key={key}>
          <label className="block text-xs font-medium text-slate-600 mb-1">{field.label}</label>
          {field.type === 'textarea' && (
            <textarea
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-y"
              rows={4}
              value={values[key] ?? field.default}
              placeholder={field.placeholder}
              maxLength={field.max_chars}
              onChange={(e) => onChange(key, e.target.value)}
            />
          )}
          {field.type === 'select' && (
            <select
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
              value={values[key] ?? field.default}
              onChange={(e) => onChange(key, e.target.value)}
            >
              {(field.options ?? []).map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          )}
          {field.type === 'input' && (
            <input
              type="text"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={values[key] ?? field.default}
              placeholder={field.placeholder}
              onChange={(e) => onChange(key, e.target.value)}
            />
          )}
          {field.max_chars && (
            <div className="text-[10px] text-slate-400 mt-0.5">
              {(values[key] ?? field.default).length} / {field.max_chars}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Payload builder ───────────────────────────────────────────────────────────

function buildPayload(template: Record<string, unknown>, values: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const [key, val] of Object.entries(template)) {
    if (typeof val === 'string') {
      result[key] = val.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? '')
    } else if (Array.isArray(val)) {
      result[key] = val.map((item) => {
        if (typeof item === 'string') return item.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? '')
        if (typeof item === 'object' && item !== null) {
          const copy: Record<string, unknown> = {}
          for (const [mk, mv] of Object.entries(item)) {
            if (typeof mv === 'string') copy[mk] = mv.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? '')
            else copy[mk] = mv
          }
          return copy
        }
        return item
      })
    } else if (typeof val === 'object' && val !== null) {
      const copy: Record<string, unknown> = {}
      for (const [mk, mv] of Object.entries(val)) {
        if (typeof mv === 'string') copy[mk] = mv.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? '')
        else copy[mk] = mv
      }
      result[key] = copy
    } else {
      result[key] = val
    }
  }
  return result
}

// ── Result renderer ───────────────────────────────────────────────────────────

function InvokeResultView({ result }: { result: InvokeResult }) {
  if (!isOk(result)) {
    return (
      <div className="mt-3 p-3 rounded bg-red-50 border border-red-200 text-xs text-red-700">
        <strong>调用失败：</strong> {result.message}
        {result.blocked_reasons && result.blocked_reasons.length > 0 && (
          <div className="mt-1">阻断原因：{result.blocked_reasons.join('；')}</div>
        )}
        {result.required_confirmations && result.required_confirmations.length > 0 && (
          <div className="mt-1">需要确认：{result.required_confirmations.join('、')}</div>
        )}
      </div>
    )
  }
  return (
    <div className="mt-4">
      <AssetResultPreview data={result.data} />
    </div>
  )
}

// ── Lyrics-gen card ───────────────────────────────────────────────────────────

function LyricsGenCard() {
  const template = LYRICS_TEMPLATE
  const [values, setValues] = useState<Record<string, string>>({})
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)

  const handleChange = (key: string, val: string) => setValues((v) => ({ ...v, [key]: val }))

  const handleRun = async () => {
    const payload = buildPayload(template.payload_template as Record<string, unknown>, values)
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    try {
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, payload, {})
      setResult(res)
      setRunState('done')
    } catch {
      setRunState('error')
    }
  }

  return (
    <CapabilityCard template={template} runState={runState} onRun={handleRun}>
      <RunnerForm schema={template.form_schema as FormSchema} values={values} onChange={handleChange} />
      {riskResult && !riskResult.allowed && (
        <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
          {riskResult.required_confirmations.length > 0 && (
            <div className="mt-1">需要确认：{riskResult.required_confirmations.join('、')}</div>
          )}
        </div>
      )}
      {result && <InvokeResultView result={result} />}
    </CapabilityCard>
  )
}

// ── TTS card ─────────────────────────────────────────────────────────────────

function TtsSyncCard() {
  const template = TTS_SYNC_TEMPLATE
  const [values, setValues] = useState<Record<string, string>>({})
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)

  const handleChange = (key: string, val: string) => setValues((v) => ({ ...v, [key]: val }))

  const handleRun = async () => {
    const payload = buildPayload(template.payload_template as Record<string, unknown>, values)
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    try {
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, payload, {})
      setResult(res)
      setRunState('done')
    } catch {
      setRunState('error')
    }
  }

  return (
    <CapabilityCard template={template} runState={runState} onRun={handleRun}>
      <RunnerForm schema={template.form_schema as FormSchema} values={values} onChange={handleChange} />
      {riskResult && !riskResult.allowed && (
        <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
        </div>
      )}
      {result && <InvokeResultView result={result} />}
    </CapabilityCard>
  )
}

// ── Voice-list card ───────────────────────────────────────────────────────────

function VoiceListCard() {
  const template = VOICE_LIST_TEMPLATE
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)

  const handleRun = async () => {
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    try {
      const risk = await riskCheck(template.capability_id, {}, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, {}, {})
      setResult(res)
      setRunState('done')
    } catch {
      setRunState('error')
    }
  }

  return (
    <CapabilityCard template={template} runState={runState} onRun={handleRun}>
      <div className="text-xs text-slate-500 mb-2">此能力无需参数，直接查询可用音色列表。</div>
      {riskResult && !riskResult.allowed && (
        <div className="p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
        </div>
      )}
      {result && <InvokeResultView result={result} />}
    </CapabilityCard>
  )
}

// ── Image-t2i card ────────────────────────────────────────────────────────────

function ImageT2iCard() {
  const template = IMAGE_T2I_TEMPLATE
  const [values, setValues] = useState<Record<string, string>>({})
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)

  const handleChange = (key: string, val: string) => setValues((v) => ({ ...v, [key]: val }))

  const handleRun = async () => {
    const payload = buildPayload(template.payload_template as Record<string, unknown>, values)
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    try {
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, payload, {})
      setResult(res)
      setRunState('done')
    } catch {
      setRunState('error')
    }
  }

  return (
    <CapabilityCard template={template} runState={runState} onRun={handleRun}>
      <RunnerForm schema={template.form_schema as FormSchema} values={values} onChange={handleChange} />
      {riskResult && !riskResult.allowed && (
        <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
        </div>
      )}
      {result && <InvokeResultView result={result} />}
    </CapabilityCard>
  )
}

// ── Chat-openai card ──────────────────────────────────────────────────────────

function ChatOpenaiCard() {
  const template = CHAT_OPENAI_TEMPLATE
  const [values, setValues] = useState<Record<string, string>>({})
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)

  const handleChange = (key: string, val: string) => setValues((v) => ({ ...v, [key]: val }))

  const handleRun = async () => {
    const payload = buildPayload(template.payload_template as Record<string, unknown>, values)
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    try {
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, payload, {})
      setResult(res)
      setRunState('done')
    } catch {
      setRunState('error')
    }
  }

  return (
    <CapabilityCard template={template} runState={runState} onRun={handleRun}>
      <RunnerForm schema={template.form_schema as FormSchema} values={values} onChange={handleChange} />
      {riskResult && !riskResult.allowed && (
        <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
        </div>
      )}
      {result && <InvokeResultView result={result} />}
    </CapabilityCard>
  )
}

// ── Shared card wrapper ────────────────────────────────────────────────────────

function CapabilityCard({
  template,
  runState,
  onRun,
  children,
}: {
  template: RunnerTemplate
  runState: RunState
  onRun: () => void
  children: React.ReactNode
}) {
  const RUN_LABELS: Record<string, string> = {
    'lyrics-gen': '生成歌词',
    'tts-sync': '生成语音',
    'voice-list': '查询音色',
    'image-t2i': '生成图片',
    'chat-openai': '发送',
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h2 className="text-base font-semibold text-slate-900">{template.label}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{template.description}</p>
          </div>
          <RiskBadge level={template.risk_level} />
        </div>
        {template.suitable_for.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {template.suitable_for.map((s) => (
              <span key={s} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{s}</span>
            ))}
          </div>
        )}
      </div>
      <div className="px-5 py-4">
        <div className="mb-4">{children}</div>
        <div className="flex items-center gap-3">
          <RunButton state={runState} label={RUN_LABELS[template.capability_id] ?? '执行'} onClick={onRun} />
          <span className="text-xs text-slate-400">执行前会先进行安全检查</span>
        </div>
        {runState === 'done' && (
          <div className="mt-3 text-xs text-emerald-600">✓ 执行完成</div>
        )}
        {runState === 'error' && (
          <div className="mt-3 text-xs text-red-600">✗ 执行失败（被安全检查阻断或发生错误）</div>
        )}
        {template.next_steps.length > 0 && runState === 'done' && (
          <div className="mt-4 pt-3 border-t border-slate-100">
            <p className="text-xs text-slate-500 mb-2">下一步：</p>
            <div className="space-y-1">
              {template.next_steps.map((ns) => (
                <div key={ns.capability_id} className="flex items-center gap-2">
                  {ns.blocked ? (
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <span>{ns.label}</span>
                      <span className="text-orange-400">（需确认）</span>
                    </span>
                  ) : (
                    <Link
                      to={`/capability-runner?capability=${ns.capability_id}`}
                      className="text-xs text-sky-600 hover:underline"
                    >
                      → {ns.label}
                    </Link>
                  )}
                  <span className="text-[10px] text-slate-400">{ns.note}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="mt-3 pt-3 border-t border-slate-100">
          <Link
            to={`/test-console?capability=${template.capability_id}`}
            className="text-[10px] text-slate-400 hover:text-slate-600"
          >
            高级测试 →
          </Link>
        </div>
      </div>
    </div>
  )
}

// ── Inline templates ─────────────────────────────────────────────────────────

const LYRICS_TEMPLATE: RunnerTemplate = {
  capability_id: 'lyrics-gen',
  label: '歌词生成',
  description: '根据主题、风格、情绪生成结构化歌词，可继续用于 music-gen。',
  suitable_for: ['情绪 MV', 'AI 歌曲草稿', '短视频 BGM', '音乐灵感'],
  risk_level: 'safe',
  form_schema: {
    theme: { type: 'input', label: '主题', default: '夏天傍晚的乡村小路', placeholder: '描述想要的歌曲主题' },
    style: { type: 'input', label: '风格', default: '温柔、怀旧，民谣', placeholder: '如：流行、摇滚、温柔、怀旧' },
    language: { type: 'select', label: '语言', default: '中文', options: ['中文', '英文', '日文', '韩文', '其他'].map(v => ({ value: v, label: v })) },
  },
  payload_template: { mode: 'write_full_song', prompt: '{theme}，风格：{style}', title: '' },
  next_steps: [
    { capability_id: 'music-gen', label: '生成音乐', note: 'music-gen 属于额度敏感能力，需要确认后执行', blocked: true },
  ],
}

const TTS_SYNC_TEMPLATE: RunnerTemplate = {
  capability_id: 'tts-sync',
  label: '短文本语音合成',
  description: '输入文本，选择模型和音色，生成可播放音频。',
  suitable_for: ['短视频旁白', '语音助手', '情绪对话', '有声书片段'],
  risk_level: 'safe',
  form_schema: {
    text: { type: 'textarea', label: '文本', default: '你好，这是 MiniMax Token Plan 语音合成能力测试。', placeholder: '输入要合成的文本，建议 300 字以内', max_chars: 10000 },
    model: {
      type: 'select', label: '模型', default: 'speech-2.8-hd',
      options: [
        { value: 'speech-2.8-hd', label: 'speech-2.8-hd 官方当前·高质量' },
        { value: 'speech-2.8-turbo', label: 'speech-2.8-turbo 官方当前·低延迟' },
        { value: 'speech-02-hd', label: 'speech-02-hd 已验收稳定' },
        { value: 'speech-02-turbo', label: 'speech-02-turbo 已验收稳定' },
      ],
    },
    voice_id: { type: 'input', label: '音色 ID', default: '', placeholder: '先在「音色列表」查询可用 voice_id' },
    speed: { type: 'input', label: '语速', default: '1.0', placeholder: '范围 0.5~2.0' },
  },
  payload_template: { model: '{model}', text: '{text}', voice_setting: { voice_id: '{voice_id}', speed: '{speed}' } },
  next_steps: [],
}

const VOICE_LIST_TEMPLATE: RunnerTemplate = {
  capability_id: 'voice-list',
  label: '查询音色列表',
  description: '查询当前可用 voice_id，用于 TTS 语音合成。',
  suitable_for: ['查询可用音色', '选择 TTS 音色'],
  risk_level: 'safe',
  form_schema: {},
  payload_template: {},
  next_steps: [
    { capability_id: 'tts-sync', label: '语音合成', note: '获取 voice_id 后可进入语音合成', blocked: false },
  ],
}

const IMAGE_T2I_TEMPLATE: RunnerTemplate = {
  capability_id: 'image-t2i',
  label: '文生图',
  description: '输入 prompt，选择图片模型，生成图片。',
  suitable_for: ['封面', '海报', '情绪 MV 分镜', '产品配图', '设计灵感'],
  risk_level: 'safe',
  form_schema: {
    prompt: { type: 'textarea', label: '图片描述', default: '一只橘猫坐在窗边，清晨阳光，真实摄影风格', placeholder: '描述想要的图片内容', max_chars: 1500 },
    model: {
      type: 'select', label: '模型', default: 'image-01',
      options: [
        { value: 'image-01', label: 'image-01 官方主力·支持尺寸控制' },
        { value: 'image-01-live', label: 'image-01-live 官方当前·画风控制' },
      ],
    },
    aspect_ratio: {
      type: 'select', label: '尺寸/比例', default: '1:1',
      options: [
        { value: '1:1', label: '1:1 方形' },
        { value: '16:9', label: '16:9 宽屏' },
        { value: '9:16', label: '9:16 竖屏' },
      ],
    },
  },
  payload_template: { model: '{model}', prompt: '{prompt}', aspect_ratio: '{aspect_ratio}' },
  next_steps: [
    { capability_id: 'image-i2i', label: '图生图', note: 'image-i2i 需要参考图和 confirm_asset_source，后续版本支持', blocked: true },
  ],
}

const CHAT_OPENAI_TEMPLATE: RunnerTemplate = {
  capability_id: 'chat-openai',
  label: '文本对话',
  description: '使用 OpenAI 兼容协议测试 MiniMax 对话模型。',
  suitable_for: ['问答', '对话测试', 'SDK 接入验证'],
  risk_level: 'safe',
  form_schema: {
    model: {
      type: 'select', label: '模型', default: 'MiniMax-M2.7-highspeed',
      options: [
        { value: 'MiniMax-M3', label: 'MiniMax-M3 官方主推·多模态旗舰' },
        { value: 'MiniMax-M2.7-highspeed', label: 'MiniMax-M2.7-highspeed Token Plan 高频' },
        { value: 'MiniMax-M2.7', label: 'MiniMax-M2.7 标准档' },
      ],
    },
    prompt: { type: 'textarea', label: '问题', default: '请用一句话介绍 MiniMax Token Plan 的能力。', placeholder: '输入你想问的问题' },
  },
  payload_template: { model: '{model}', messages: [{ role: 'user', content: '{prompt}' }], max_tokens: 1024, temperature: 0.7 },
  next_steps: [],
}

// ── Capability selector ────────────────────────────────────────────────────────

const CAPABILITY_LIST = [
  { id: 'lyrics-gen', label: '歌词生成', emoji: '🎵', family: 'music' },
  { id: 'tts-sync', label: '语音合成', emoji: '🎙️', family: 'voice' },
  { id: 'voice-list', label: '音色列表', emoji: '🎙️', family: 'voice' },
  { id: 'image-t2i', label: '图片生成', emoji: '🖼️', family: 'vision' },
  { id: 'chat-openai', label: '文本对话', emoji: '💬', family: 'chat' },
]

function CapabilitySelector({ onSelect }: { onSelect: (id: string) => void }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {CAPABILITY_LIST.map((cap) => (
        <button
          key={cap.id}
          onClick={() => onSelect(cap.id)}
          className="rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm p-4 text-left transition"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{cap.emoji}</span>
            <span className="font-semibold text-slate-900 text-sm">{cap.label}</span>
          </div>
          <div className="text-xs text-slate-500">{cap.family}</div>
        </button>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CapabilityRunnerPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selected = searchParams.get('capability')

  const handleSelect = (id: string) => {
    setSearchParams({ capability: id })
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">能力体验</h1>
        <p className="text-sm text-slate-600 mt-1">
          选择一个能力，使用默认输入直接体验 MiniMax Token Plan 的实际效果。
        </p>
      </div>

      {!selected ? (
        <CapabilitySelector onSelect={handleSelect} />
      ) : (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSearchParams({})}
              className="text-sm text-sky-600 hover:underline"
            >
              ← 重新选择
            </button>
            <span className="text-sm text-slate-400">|</span>
            <span className="text-sm text-slate-600">
              当前：{CAPABILITY_LIST.find((c) => c.id === selected)?.label ?? selected}
            </span>
          </div>

          {selected === 'lyrics-gen' && <LyricsGenCard />}
          {selected === 'tts-sync' && <TtsSyncCard />}
          {selected === 'voice-list' && <VoiceListCard />}
          {selected === 'image-t2i' && <ImageT2iCard />}
          {selected === 'chat-openai' && <ChatOpenaiCard />}

          {!CAPABILITY_LIST.find((c) => c.id === selected) && (
            <div className="text-sm text-slate-500">
              不支持的能力：{selected}（Runner v1 支持 lyrics-gen / tts-sync / voice-list / image-t2i / chat-openai）
            </div>
          )}
        </div>
      )}
    </div>
  )
}
