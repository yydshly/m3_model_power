/**
 * ProjectOverview.tsx — Project documentation page.
 *
 * Answers:
 * 1. What is this project?
 * 2. What can it do?
 * 3. What are the core modules?
 * 4. Why RiskGate / History / Trace?
 * 5. What can be extended?
 */
import { Link } from 'react-router-dom'

const POSITIONING_CARDS = [
  {
    emoji: '🧪',
    title: '能力验收工具',
    desc: '将 Token Plan 实际可用能力整理成可验证、可追踪的验收工作台。',
  },
  {
    emoji: '⚡',
    title: '真实调用工作台',
    desc: '不对接 mock，所有请求发往真实 MiniMax API，可观察真实输出。',
  },
  {
    emoji: '🏗️',
    title: '应用开发底座',
    desc: 'minimax_core 可独立复用到 Voice Lab、数字人、图片音乐等工具开发。',
  },
]

const CAPABILITY_GROUPS = [
  {
    emoji: '💬',
    label: '对话',
    items: ['OpenAI 兼容接口', 'Anthropic 兼容接口', 'Responses API', 'Token 估算'],
  },
  {
    emoji: '🗣️',
    label: '语音',
    items: ['TTS 同步合成', 'WebSocket 实时合成', '异步合成', '音色列表查询'],
  },
  {
    emoji: '🖼️',
    label: '视觉',
    items: ['图片生成 (T2I)', '图生图 (I2I)'],
  },
  {
    emoji: '🎵',
    label: '音乐',
    items: ['歌词生成', '音乐生成'],
  },
  {
    emoji: '📁',
    label: '资产',
    items: ['文件上传', '资产列表', '资产详情', '资产内容读取'],
  },
  {
    emoji: '🧬',
    label: '模型',
    items: ['模型列表', '模型详情查询'],
  },
]

const WORKBENCH_ENTRIES = [
  {
    to: '/',
    emoji: '🏠',
    label: '总览',
    desc: '验收进度、最近调用、风险说明',
  },
  {
    to: '/capability-runner',
    emoji: '⚡',
    label: '能力体验',
    desc: '低门槛能力调用入口，按能力分类快速测试',
  },
  {
    to: '/test-console',
    emoji: '🧪',
    label: '高级测试',
    desc: 'Raw JSON、RiskGate、开发者测试模式',
  },
  {
    to: '/capability-scenarios',
    emoji: '🎯',
    label: '场景推荐',
    desc: '按使用场景组织能力，直接选用',
  },
  {
    to: '/capability-workflows',
    emoji: '🔁',
    label: '流程体验',
    desc: '按任务流程串联多个能力',
  },
  {
    to: '/capability-profiles',
    emoji: '🧭',
    label: '能力画像',
    desc: '能力适用模型、风险等级、输出说明',
  },
  {
    to: '/models-all',
    emoji: '🧬',
    label: '所有模型',
    desc: '项目已建模和可测试模型一览',
  },
]

const ARCH_LAYERS = [
  {
    layer: 'Frontend Workbench',
    desc: 'React + TypeScript 单页应用，路由驱动',
    color: 'bg-sky-50 border-sky-200',
  },
  {
    layer: 'FastAPI Backend',
    desc: '统一路由、鉴权、参数校验',
    color: 'bg-violet-50 border-violet-200',
  },
  {
    layer: 'minimax_core',
    desc: '核心逻辑层',
    color: 'bg-indigo-50 border-indigo-200',
  },
  {
    layer: 'MiniMax Token Plan API',
    desc: '真实上游',
    color: 'bg-slate-50 border-slate-200',
  },
]

const CORE_COMPONENTS = [
  { name: 'CapabilityRegistry', desc: '统一登记能力定义与元数据' },
  { name: 'ModelRegistry', desc: '统一登记模型规格与可用性' },
  { name: 'CapabilityInvoker', desc: '统一调用入口，封装协议差异' },
  { name: 'RiskGate', desc: '风险门禁，拦截高风险操作' },
  { name: 'History Store', desc: '调用历史持久化，可追溯' },
  { name: 'Diagnostics Trace', desc: 'trace_id 链路追踪，完整诊断链' },
  { name: 'Result Summary', desc: '结果摘要抽取，资产 + 文本 + Token' },
  { name: 'Demo Payload Builder', desc: 'demo payload 自动生成，降低门槛' },
  { name: 'Payload Validation', desc: '参数校验与模型能力匹配' },
  { name: 'CI Guard Scripts', desc: '自动化 guard，确保合入质量' },
]

const TECH_HIGHLIGHTS = [
  '能力注册中心：能力定义与运行时绑定',
  '模型与能力匹配：能力选择模型，模型约束能力',
  'RiskGate 风险门禁：高成本/删除/资产类操作需确认',
  '真实调用历史：每条调用写入 history.jsonl',
  'trace_id 链路诊断：从请求到响应的完整追踪',
  'Token usage 展示：输入 / 输出 / 总计 Token',
  '资产结果抽取：图片 / 音频 / 文件 URL 自动识别',
  'demo payload 自动生成：零配置即可体验能力',
  'payload validation：参数类型、必填、范围校验',
  'CI guard scripts：20+ 自动化检查脚本',
]

const ROADMAP = {
  '短期增强': [
    '历史搜索、导出、清理',
    '能力调用报告生成',
    'diagnostics trace 自动裁剪',
  ],
  '产品化增强': [
    '普通用户模式 / 开发者模式切换',
    '资产库管理界面',
    '后端 payload validation 产品化',
  ],
  '架构复用': [
    'minimax_core 独立化发布 npm 包',
    '复用到 Voice Lab 工具',
    '复用到数字人语音工具',
    '复用到图片 / 音乐工具',
  ],
}

export default function ProjectOverview() {
  return (
    <div className="p-8 max-w-5xl space-y-10">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">项目说明</h1>
        <p className="text-sm text-slate-500 mt-1">
          MiniMax Token Plan 能力验收、调用工作台与可复用开发底座
        </p>
      </div>

      {/* ── 1. Project positioning ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">项目定位</h2>
        <p className="text-sm text-slate-600 mb-4">
          m3_model_power 是一个 MiniMax Token Plan 能力验收、真实调用和可复用开发底座项目。它不是简单罗列 API，而是把当前 Token Plan 实际可用能力整理成可验证、可追踪、可复用的工作台。
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {POSITIONING_CARDS.map((card) => (
            <div key={card.title} className="border border-slate-200 rounded-lg p-4 bg-white">
              <div className="text-2xl mb-2">{card.emoji}</div>
              <div className="text-sm font-medium text-slate-800 mb-1">{card.title}</div>
              <div className="text-xs text-slate-500">{card.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 2. Current capabilities ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">当前已有能力</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CAPABILITY_GROUPS.map((group) => (
            <div key={group.label} className="border border-slate-200 rounded-lg p-3 bg-white">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-base">{group.emoji}</span>
                <span className="text-sm font-medium text-slate-800">{group.label}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {group.items.map((item) => (
                  <span key={item} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 3. Workbench entries ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">工作台入口</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {WORKBENCH_ENTRIES.map((entry) => (
            <Link
              key={entry.to}
              to={entry.to}
              className="border border-slate-200 rounded-lg p-3 bg-white hover:border-slate-300 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base">{entry.emoji}</span>
                <span className="text-sm font-medium text-slate-800">{entry.label}</span>
              </div>
              <div className="text-xs text-slate-500">{entry.desc}</div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 4. Core architecture ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">核心架构</h2>
        <div className="space-y-2">
          {ARCH_LAYERS.map((l, i) => (
            <div key={l.layer} className={`flex items-center gap-3 border rounded-lg p-3 ${l.color}`}>
              <div className="text-xs font-mono text-slate-500 w-4 text-center">{i + 1}</div>
              <div className="flex-1">
                <div className="text-sm font-medium text-slate-800">{l.layer}</div>
                <div className="text-xs text-slate-500">{l.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* minimax_core sub-components */}
        <div className="mt-3 border border-indigo-200 rounded-lg p-4 bg-indigo-50/50">
          <div className="text-sm font-medium text-indigo-700 mb-3">minimax_core 核心模块</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {CORE_COMPONENTS.map((c) => (
              <div key={c.name} className="flex items-start gap-2">
                <code className="text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded shrink-0 font-mono">
                  {c.name}
                </code>
                <span className="text-xs text-slate-600">{c.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. Technical highlights ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">技术要点</h2>
        <div className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {TECH_HIGHLIGHTS.map((t) => (
              <div key={t} className="flex items-start gap-2 text-xs text-slate-600">
                <span className="text-sky-500 mt-0.5">✓</span>
                {t}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. Future roadmap ── */}
      <section>
        <h2 className="text-base font-medium text-slate-700 mb-3">后续扩展路线</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Object.entries(ROADMAP).map(([phase, items]) => (
            <div key={phase} className="border border-slate-200 rounded-lg p-4 bg-white">
              <div className="text-sm font-medium text-slate-700 mb-3">{phase}</div>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-slate-600">
                    <span className="text-slate-400 mt-0.5">·</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
