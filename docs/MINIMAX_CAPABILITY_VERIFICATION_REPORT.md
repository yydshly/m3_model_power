# MiniMax 能力验收报告

> 生成时间：2026-06-07T00:00:00.000000+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| integration_ready_but_probe_pending_valid_image_url | 1 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| image-i2i | integration_ready_but_probe_pending_valid_image_url | - | - | - | RiskGate / Invoker / payload结构已修复；等待有效公开测试图片URL |

## 备注

### image-i2i 当前状态

**状态**：`integration_ready_but_probe_pending_valid_image_url`

**已完成的修复**：
- ✅ RiskGate 无 `confirm_asset_source` 时正确阻断
- ✅ `CapabilityInvoker` 已添加 `image-i2i` 路由
- ✅ payload 已修正为顶层 `img_url` 字段

**当前 payload 结构**：
```json
{
  "model": "image-01",
  "prompt": "将图片转换为插画风格",
  "img_url": "https://example.com/sample.jpg",
  "n": 1
}
```

**阻塞原因**：`https://example.com/sample.jpg` 不是有效图片 URL，不得继续重试。

**后续测试图片策略**：
- 不要使用 `https://example.com/sample.jpg`
- 需要一个真实可访问的安全测试图 URL，应满足：
  - 公开可访问
  - 非人脸、非隐私、非版权敏感内容
  - 能直接返回 `image/jpeg` 或 `image/png`
  - 不需要登录、不需要防盗链
- 推荐方式：由用户提供一个安全公开图片 URL
- 或：生成安全几何测试图 → 上传到用户可控公开位置 → 获取 raw 图片 URL → 再执行 image-i2i

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*
