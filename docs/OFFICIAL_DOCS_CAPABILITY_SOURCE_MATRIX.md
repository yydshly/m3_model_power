# Official Docs Capability Source Matrix

## Schema
| Field | Description |
|--------|-------------|
| capability_id | Local capability identifier |
| local_endpoint | Backend handler path |
| official_doc_url | Official MiniMax documentation URL |
| official_support | What official docs say about this capability |
| models_yaml_config | Current local models.yaml configuration |
| capabilities_yaml_config | Current local capabilities.yaml configuration |
| runner_status | Whether Runner supports this capability |
| riskgate_rules | RiskGate confirmation requirements |
| scope_policy | Current scope: in_scope / warning_only / out_of_scope |
| material_required | Whether this capability requires uploaded assets |
| extra_cost | Whether this may incur additional charges |
| explicit_confirm | Whether explicit confirmation is required |
| alignment_status | aligned / drift_found / pending_manual_check / out_of_scope |
| issues | Description of any alignment issues |
| fix_suggestion | Recommended fix if misaligned |

## Chat / Text Capabilities

| capability_id | chat-openai |
|---------------|-------------|
| local_endpoint | /api/invoke/chat-openai |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/text-openai-api |
| official_support | OpenAI SDK supports 8 text models |
| models_yaml_config | protocols: [openai] for all 8 models |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules beyond standard |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | chat-anthropic |
|---------------|-----------------|
| local_endpoint | /api/invoke/chat-anthropic |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/text-anthropic-api |
| official_support | Anthropic SDK supports 8 text models. M3 supports image/video; M2.x supports text and tool-related blocks only |
| models_yaml_config | protocols: [anthropic] for all 8 models (fixed P0-1) |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules beyond standard |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | chat-responses-create |
|----------------|----------------------|
| local_endpoint | /api/invoke/chat-responses-create |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/responses-create |
| official_support | Docs example uses MiniMax-M3 only |
| models_yaml_config | Only M3 has responses protocol |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | pending_manual_check |
| issues | Only M3 documented as example; other models not verified |
| fix_suggestion | Display only M3 as documented, or clearly mark other models as pending verification |

| capability_id | chat-responses-tokens |
|---------------|----------------------|
| local_endpoint | /api/invoke/chat-responses-tokens |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/responses-tokens |
| official_support | Token counting for Responses API |
| models_yaml_config | Same as responses-create |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Advanced test only |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | models-openai-list |
|----------------|--------------------|
| local_endpoint | /api/invoke/models-openai-list |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/models/openai/list-models |
| official_support | GET /v1/models returns all chat/video/speech model IDs |
| models_yaml_config | N/A (metadata only) |
| capabilities_yaml_config | billing_category: normal_token_plan_test, consumes_token_plan_quota: false |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | models-openai-retrieve |
|--------------------|------------------------|
| local_endpoint | /api/invoke/models-openai-retrieve |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/models/openai/retrieve-model |
| official_support | GET /v1/models/{model} returns per-model details |
| models_yaml_config | N/A (metadata only) |
| capabilities_yaml_config | billing_category: normal_token_plan_test, consumes_token_plan_quota: false |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | models-anthropic-list |
|--------------------|------------------------|
| local_endpoint | /api/invoke/models-anthropic-list |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/models/anthropic/list-models |
| official_support | GET /anthropic/v1/models returns all chat model IDs |
| models_yaml_config | N/A (metadata only) |
| capabilities_yaml_config | billing_category: normal_token_plan_test, consumes_token_plan_quota: false |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | models-anthropic-retrieve |
|--------------------------|---------------------------|
| local_endpoint | /api/invoke/models-anthropic-retrieve |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/models/anthropic/retrieve-model |
| official_support | GET /anthropic/v1/models/{model} returns per-model details |
| models_yaml_config | N/A (metadata only) |
| capabilities_yaml_config | billing_category: normal_token_plan_test, consumes_token_plan_quota: false |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

## Speech / Voice Capabilities

| capability_id | tts-sync |
|---------------|----------|
| local_endpoint | /api/invoke/tts-sync |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/speech-t2a |
| official_support | T2A models for speech synthesis |
| models_yaml_config | Various speech models configured |
| capabilities_yaml_config | billing_category: quota_sensitive |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | May be |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | tts-async |
|---------------|-----------|
| local_endpoint | /api/invoke/tts-async |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/speech-t2a-async |
| official_support | Async T2A for longer audio |
| models_yaml_config | Various speech models |
| capabilities_yaml_config | billing_category: quota_sensitive, requires_explicit_confirmation |
| runner_status | Supported |
| riskgate_rules | Character count thresholds: 300 default, 1000 confirm, 5000 hard block |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | tts-ws |
|---------------|--------|
| local_endpoint | /api/invoke/tts-ws |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/speech-t2a-ws |
| official_support | WebSocket T2A |
| models_yaml_config | speech-02-hd, speech-02-turbo |
| capabilities_yaml_config | billing_category: quota_sensitive |
| runner_status | Special UI |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-clone-upload-audio |
|---------------|--------------------------|
| local_endpoint | /api/invoke/voice-clone-upload-audio |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-cloning-uploadcloneaudio |
| official_support | Upload reference audio for voice cloning |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: paid_confirm_required, requires_uploaded_asset: true |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source |
| scope_policy | warning_only |
| material_required | Yes (audio) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-clone-upload-prompt |
|-------------------------|---------------------------|
| local_endpoint | /api/invoke/voice-clone-upload-prompt |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-cloning-uploadprompt |
| official_support | Upload aligned prompt text for voice cloning |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: paid_confirm_required, requires_uploaded_asset: true |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source |
| scope_policy | warning_only |
| material_required | Yes (text) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-clone-do |
|----------------|-----------------|
| local_endpoint | /api/invoke/voice-clone-do |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-cloning-clone |
| official_support | Trigger voice cloning with file_id |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: paid_confirm_required, cost_level: high, requires_certification: true |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source, confirm_certification |
| scope_policy | warning_only |
| material_required | Yes (file_id from upload steps) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-list |
|---------------|------------|
| local_endpoint | /api/invoke/voice-list |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-management-get |
| official_support | List system/cloned/designed voices |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-design |
|---------------|--------------|
| local_endpoint | /api/invoke/voice-design |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-design |
| official_support | Voice design capability |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: paid_confirm_required |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source |
| scope_policy | in_scope |
| material_required | Yes |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | voice-delete |
|---------------|-------------|
| local_endpoint | /api/invoke/voice-delete |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/voice-delete |
| official_support | Delete voice resource |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.is_destructive: true |
| runner_status | Supported |
| riskgate_rules | confirm_destructive |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

## Vision / Image Capabilities

| capability_id | image-t2i |
|---------------|-----------|
| local_endpoint | /api/invoke/image-t2i |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/image-generation |
| official_support | Text-to-image generation |
| models_yaml_config | image-01, image-01-live, image-01-krea |
| capabilities_yaml_config | billing_category: quota_sensitive |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | image-i2i |
|---------------|-----------|
| local_endpoint | /api/invoke/image-i2i |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/image-generation |
| official_support | Image-to-image with reference |
| models_yaml_config | image-01, image-01-live |
| capabilities_yaml_config | billing_category: quota_sensitive, requires_uploaded_asset |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source |
| scope_policy | in_scope |
| material_required | Yes (image) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

## Video Capabilities

| capability_id | video-t2v |
|---------------|----------|
| local_endpoint | /api/invoke/video-t2v |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/video-generation |
| official_support | Text-to-video |
| models_yaml_config | video-01 |
| capabilities_yaml_config | billing_category: high_cost_confirm_required |
| runner_status | Not supported |
| riskgate_rules | confirm_high_cost |
| scope_policy | warning_only |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | Marked as warning_only, not default execution |
| fix_suggestion | - |

| capability_id | video-i2v |
|---------------|----------|
| local_endpoint | /api/invoke/video-i2v |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/video-generation |
| official_support | Image-to-video |
| models_yaml_config | MiniMax-Hailuo-02, MiniMax-Hailuo-2.0 |
| capabilities_yaml_config | billing_category: high_cost_confirm_required |
| runner_status | Not supported |
| riskgate_rules | confirm_high_cost |
| scope_policy | out_of_scope |
| material_required | Yes (image) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | video-s2v |
|---------------|----------|
| local_endpoint | /api/invoke/video-s2v |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/video-generation |
| official_support | Subject-to-video |
| models_yaml_config | video-01 |
| capabilities_yaml_config | billing_category: high_cost_confirm_required, requires_uploaded_asset |
| runner_status | Not supported |
| riskgate_rules | confirm_high_cost, confirm_asset_source |
| scope_policy | out_of_scope |
| material_required | Yes |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | Video capabilities generally out_of_scope |
| fix_suggestion | - |

| capability_id | video-query |
|---------------|------------|
| local_endpoint | /api/invoke/video-query |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/video-query |
| official_support | Query existing video task |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.requires_existing_task: true |
| runner_status | Advanced test only |
| riskgate_rules | confirm_existing_task |
| scope_policy | in_scope |
| material_required | No (existing task only) |
| extra_cost | No |
| explicit_confirm | Yes (existing task) |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | video-download |
|---------------|--------------|
| local_endpoint | /api/invoke/video-download |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/video-download |
| official_support | Download video file |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.requires_existing_task: true |
| runner_status | Advanced test only |
| riskgate_rules | confirm_existing_task |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

## Music Capabilities

| capability_id | music-gen |
|---------------|----------|
| local_endpoint | /api/invoke/music-gen |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/music-generation |
| official_support | Full music generation |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: quota_sensitive, requires_explicit_confirmation |
| runner_status | Supported |
| riskgate_rules | confirm_quota |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | music-cover-prep |
|---------------|-----------------|
| local_endpoint | /api/invoke/music-cover-prep |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/music-cover |
| official_support | Cover song preprocessing |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: quota_sensitive, requires_uploaded_asset |
| runner_status | Supported |
| riskgate_rules | confirm_quota, confirm_asset_source |
| scope_policy | in_scope |
| material_required | Yes (audio) |
| extra_cost | Yes |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | lyrics-gen |
|---------------|------------|
| local_endpoint | /api/invoke/lyrics-gen |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/lyrics-generation |
| official_support | Lyrics generation |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: quota_sensitive |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | Yes |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

## File Capabilities

| capability_id | file-upload |
|---------------|------------|
| local_endpoint | /api/invoke/file-upload |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/file-upload |
| official_support | Upload file for capability use |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.requires_uploaded_asset: true |
| runner_status | Supported |
| riskgate_rules | confirm_asset_source |
| scope_policy | in_scope |
| material_required | Yes |
| extra_cost | No |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | file-list |
|---------------|-----------|
| local_endpoint | /api/invoke/file-list |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/file-list |
| official_support | List uploaded files |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | file-retrieve |
|---------------|--------------|
| local_endpoint | /api/invoke/file-retrieve |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/file-retrieve |
| official_support | Retrieve file metadata |
| models_yaml_config | N/A |
| capabilities_yaml_config | billing_category: normal_token_plan_test |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | file-content |
|---------------|--------------|
| local_endpoint | /api/invoke/file-content |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/file-content |
| official_support | Download file content |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.is_destructive: false |
| runner_status | Supported |
| riskgate_rules | No special rules |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | No |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |

| capability_id | file-delete |
|---------------|------------|
| local_endpoint | /api/invoke/file-delete |
| official_doc_url | https://platform.minimaxi.com/docs/api-reference/file-delete |
| official_support | Delete uploaded file |
| models_yaml_config | N/A |
| capabilities_yaml_config | operation_policy.is_destructive: true |
| runner_status | Supported |
| riskgate_rules | confirm_destructive |
| scope_policy | in_scope |
| material_required | No |
| extra_cost | No |
| explicit_confirm | Yes |
| alignment_status | aligned |
| issues | - |
| fix_suggestion | - |
