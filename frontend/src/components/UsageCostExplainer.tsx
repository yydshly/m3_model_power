/**
 * UsageCostExplainer — explains Token/Quota/Charge relationship for a capability.
 *
 * Shows:
 * - Whether this capability consumes Token Plan quota
 * - Whether it may charge extra
 * - Confirmation requirements
 * - Plain-language explanation of what "Token" means
 */
import type { BillingPolicy } from '../api'

type Props = {
  billingPolicy: BillingPolicy
  /** Cost level from capability.cost_level */
  costLevel?: string
}

const BILLING_CATEGORY_LABELS: Record<string, string> = {
  normal_token_plan_test: '套餐内能力（测试）',
  quota_sensitive: '配额敏感',
  paid_confirm_required: '付费确认',
  high_cost_confirm_required: '高成本确认',
  asset_required_confirm_required: '素材确认',
}

export default function UsageCostExplainer({ billingPolicy, costLevel }: Props) {
  const { billing_category, consumes_token_plan_quota, may_charge_extra, requires_explicit_confirmation } = billingPolicy

  const categoryLabel = BILLING_CATEGORY_LABELS[billing_category] ?? billing_category
  const isHighCost = billing_category === 'high_cost_confirm_required' || costLevel === 'high'
  const isQuotaSensitive = billing_category === 'quota_sensitive'
  const mayCharge = may_charge_extra

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-1.5">
      <div className="font-semibold text-slate-700 flex items-center gap-1.5">
        <span>💰</span>
        <span>费用/额度说明</span>
      </div>

      {/* Quick status pills */}
      <div className="flex flex-wrap gap-1.5">
        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
          consumes_token_plan_quota
            ? 'bg-blue-100 text-blue-700'
            : 'bg-slate-100 text-slate-600'
        }`}>
          {consumes_token_plan_quota ? '消耗套餐额度' : '不消耗套餐额度'}
        </span>
        {mayCharge && (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700">
            ⚠ 可能额外收费
          </span>
        )}
        {isHighCost && (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700">
            🔴 高成本
          </span>
        )}
        {isQuotaSensitive && (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700">
            ⏳ 配额敏感
          </span>
        )}
        {requires_explicit_confirmation && (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-orange-100 text-orange-700">
            ⚠ 需确认
          </span>
        )}
      </div>

      {/* Capability billing category */}
      <div className="text-slate-600">
        <span className="font-medium">当前能力：</span>
        {categoryLabel}
      </div>

      {/* Plain-language explanation */}
      <div className="bg-white rounded border border-slate-100 p-2 space-y-1 text-slate-600">
        <div className="font-medium text-slate-700">怎么理解？</div>
        <div>
          <strong>Token</strong> 是模型处理文本的计量单位，不是直接等于人民币。
        </div>
        {consumes_token_plan_quota ? (
          <div>
            在 Token Plan 中，本次调用通常<strong>消耗套餐额度</strong>，而不是单独扣费。
          </div>
        ) : (
          <div>本次调用<strong>不消耗套餐额度</strong>。</div>
        )}
        {mayCharge && (
          <div className="text-red-600">
            但该能力<strong>可能产生额外费用</strong>，请确认后再执行。
          </div>
        )}
        {(isHighCost || isQuotaSensitive) && (
          <div className="text-amber-600">
            {isHighCost
              ? '该能力成本较高，请勿随意执行。'
              : '该能力消耗配额较多，请确认后再执行。'}
          </div>
        )}
        <div className="text-slate-400 text-[10px] pt-0.5">
          最终消耗以 MiniMax 控制台为准。
        </div>
      </div>
    </div>
  )
}
