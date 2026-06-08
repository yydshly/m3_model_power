/**
 * OverviewActionCards.tsx — "What do I want to do?" action cards.
 */
import { Link } from 'react-router-dom'

const CARDS = [
  {
    emoji: '⚡',
    title: '测试一个能力',
    desc: '表单化体验语音、图片、音乐、文件等能力',
    to: '/capability-runner',
    badge: null,
    hint: '最适合新手',
  },
  {
    emoji: '⚖️',
    title: '对比对话模型',
    desc: '用同一个问题测试不同协议 / 模型表现',
    to: '/capability-runner?capability=chat-openai',
    badge: null,
    hint: '推荐',
  },
  {
    emoji: '🖼️',
    title: '生成图片或语音',
    desc: '低成本验证资产类结果展示',
    to: '/capability-runner?capability=image-t2i',
    badge: null,
    hint: '低风险',
  },
  {
    emoji: '🔁',
    title: '设计一个应用流程',
    desc: '把歌词、音乐、图片、语音等能力串成流程',
    to: '/capability-workflows',
    badge: null,
    hint: null,
  },
  {
    emoji: '🧪',
    title: '风险与高级测试',
    desc: '开发者 raw JSON、RiskGate、调用历史',
    to: '/test-console',
    badge: '开发者',
    hint: null,
  },
]

export default function OverviewActionCards() {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">我想做什么？</h2>
      <div className="grid grid-cols-3 gap-3">
        {CARDS.map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400 hover:shadow-sm transition flex flex-col gap-1"
          >
            <div className="flex items-center gap-2">
              <span className="text-xl">{card.emoji}</span>
              <span className="font-medium text-slate-900 text-sm">{card.title}</span>
              {card.badge && (
                <span className="ml-auto text-[9px] bg-slate-200 text-slate-500 px-1 rounded">
                  {card.badge}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">{card.desc}</p>
            {card.hint && (
              <span className="text-[10px] text-sky-500 mt-1">{card.hint}</span>
            )}
          </Link>
        ))}
      </div>
    </section>
  )
}
