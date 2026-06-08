/**
 * workbenchNav.ts — Grouped navigation structure for the MiniMax Token Plan workbench.
 *
 * Groups:
 * - 主工作台 (Main): Core entry points for regular users
 * - 能力应用 (Applications): Scene/workflow-based navigation
 * - 能力目录 (Catalog): Browse by category
 * - 开发者 (Developer): Raw access for developers
 */

export type NavItem = {
  to: string
  emoji: string
  label: string
  hint?: string
  developerOnly?: boolean
}

export type NavGroup = {
  title: string
  items: NavItem[]
}

export const WORKBENCH_NAV: NavGroup[] = [
  {
    title: '主工作台',
    items: [
      { to: '/', emoji: '🏠', label: '总览' },
      { to: '/capability-runner', emoji: '⚡', label: '能力体验' },
      { to: '/project-overview', emoji: '📖', label: '项目说明' },
    ],
  },
  {
    title: '能力应用',
    items: [
      { to: '/capability-scenarios', emoji: '🎯', label: '场景推荐' },
      { to: '/capability-workflows', emoji: '🔁', label: '流程体验' },
      { to: '/capability-profiles', emoji: '🧭', label: '能力画像' },
    ],
  },
  {
    title: '能力目录',
    items: [], // Populated dynamically from registry.categories
  },
  {
    title: '开发者',
    items: [
      { to: '/models-all', emoji: '🧬', label: '所有模型', developerOnly: true },
      { to: '/test-console', emoji: '🧪', label: '高级测试', developerOnly: true },
    ],
  },
]

/**
 * Build category nav items from registry categories.
 */
export function buildCategoryNavItems(
  categories: Array<{ id: string; emoji: string; label: string }>,
  capabilities: Array<{ category: string; status: string }>,
): NavItem[] {
  return categories.map((cat) => {
    const total = capabilities.filter((c) => c.category === cat.id).length
    const done = capabilities.filter((c) => c.category === cat.id && c.status === 'implemented').length
    return {
      to: `/category/${cat.id}`,
      emoji: cat.emoji,
      label: cat.label,
      hint: `${done}/${total}`,
    }
  })
}
