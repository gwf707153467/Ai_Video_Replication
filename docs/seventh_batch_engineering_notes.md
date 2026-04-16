# Seventh Batch Engineering Notes

## 批次目标

第七批 runnable increment 的范围被明确锁定为：在不扩张系统边界的前提下，为 `render_image` 接入一个最小真实 provider executor，使 compile -> dispatch -> worker execute -> asset materialize 的链路首次具备真实外部生成能力。

本批次只覆盖：

- `render_image -> provider=google -> model=imagen-3.0-generate-002`
- 复用现有同步 executor/materialization 路径
- 复用现有 `httpx` 依赖
- 维持现有资产治理与 runtime 聚合主干
- 补齐 `render_image` job 最小 prompt / `provider_inputs` 注入

本批次显式不覆盖：

- `render_video -> google / veo-3.1-generate-001`
- `render_voice -> google / gemini-2.5-flash`
- retry/backoff/dead-letter 扩展
- provider 输出真实性校验与内容级 QA
- merge/export 治理增强

## 最小闭环缺口与解决策略

在进入第七批前，系统已经具备：

- job dispatch 与 worker write-back 主干
- provider executor registry 主干
- runtime artifact materialization 主干
- object-store 幂等短路与 DB/object reconciliation

但 `render_image` 任务仍存在一个阻塞最小可运行闭环的问题：`Job.payload` 中没有 prompt，也没有最小 `provider_inputs`，因此真实图片 provider 无法执行。

因此，本批次除了接入 Google Imagen HTTP client 本身，还必须在 compiler/dispatch 层补一个最小 prompt 来源。实现策略为：

- 不新增 schema
- 不扩大 project domain 数据模型
- 直接复用现有 `Project / Sequence / SPU` 字段
- 在 compile 阶段为 `render_image` job 注入最小 prompt 与 `provider_inputs`

prompt 来源约束为：

- `SPU.prompt_text`
- `SPU.negative_prompt_text`
- `SPU.visual_constraints`
- `Sequence.persuasive_goal`
- `Project.name / source_market / source_language / notes`

## 代码改动摘要

### 1. `app/providers/google/client.py`

将 Google provider client 从占位结构推进为最小可用 HTTP 调用器。

新增：

- `GoogleProviderError(RuntimeError)`
- `GoogleGeneratedImage` dataclass
- `GoogleProviderClient.generate_image(...)`
- `GoogleProviderClient._extract_generated_image(...)`

关键行为：

- 未配置 `GOOGLE_API_KEY` 时抛出 `google_provider_not_configured`
- 未配置 `GOOGLE_IMAGE_MODEL` 时抛出 `google_image_model_not_configured`
- 调用 endpoint：
  - `POST https://generativelanguage.googleapis.com/v1beta/models/{image_model}:predict`
- 请求头：
  - `x-goog-api-key`
  - `Content-Type: application/json`
- 请求体：
  - `instances=[{"prompt": prompt}]`
  - `parameters.sampleCount`
  - 可选 `negativePrompt`
  - 可选 `aspectRatio`
  - 可选 `safetySetting`
  - 可选 `personGeneration`

响应解析兼容以下图片字段形态：

- `predictions[0].bytesBase64Encoded`
- `predictions[0].image.bytesBase64Encoded`
- `predictions[0].inlineData.data`

content type 解析顺序：

- `mimeType`
- `image.mimeType`
- `inlineData.mimeType`
- fallback `image/png`

异常统一归一到：

- `google_image_generation_failed`
- `google_provider_response_invalid`

### 2. `app/workers/executors.py`

新增 `GoogleImagenExecutor`，并把 `render_image` 从 stub 切换为真实 executor。

关键行为：

- 仅 `render_image` 切换到 Google executor
- `compile / render_video / render_voice / merge` 继续保持 stub
- 从 `job.payload` 或 `provider_inputs` 中解析 prompt
- 若 prompt 缺失，抛出 `google_image_prompt_missing`
- 调用 `GoogleProviderClient.generate_image(...)`
- 将结果映射为 `ProviderExecutionResult(...).to_dict()`

返回结果契约重点包括：

- `status="succeeded"`
- `provider="google"`
- `binary_payload`
- `content_type`
- `provider_payload`

其中 `provider_payload` 附带：

- `job_type`
- `task_name`
- `runtime_version`
- `provider_name`
- `prompt`
- `negative_prompt`
- `generation_options`
- `google` 原始 provider 摘要

### 3. `app/compilers/orchestrator/compiler_service.py`

在不破坏既有 compile/dispatch 主干的前提下，仅为 `render_image` 注入最小运行所需 payload。

新增：

- `_build_render_image_payload(project_id, runtime_version)`
- `_normalize_optional_text(...)`

调整：

- `_create_and_dispatch_jobs(...)` 中先构造一次 `render_image_payload`
- 仅 `job_type == "render_image"` 时把该 payload 注入 job `payload`
- 其余 job payload 契约保持不变

注入结果包含：

- `prompt`
- `negative_prompt`
- `provider_inputs.prompt`
- `provider_inputs.negative_prompt`
- `provider_inputs.sample_count = 1`
- `provider_inputs.aspect_ratio = "9:16"`
- `provider_inputs.source = "compiler_minimal_render_image_prompt_v1"`
- `provider_inputs.runtime_version`

最小 prompt 拼装来源：

- 项目级上下文：项目名、市场、语言、项目备注
- sequence 摘要：sequence index / type / persuasive goal
- primary SPU：首个带 `prompt_text` 的 SPU
- 视觉主体：`display_name`
- 可选视觉约束：`visual_constraints`
- 可选负向提示：`negative_prompt_text`

### 4. `.env.example`

将图片模型默认说明更新为：

- `GOOGLE_IMAGE_MODEL=imagen-3.0-generate-002`

其余 Google 变量仍保留为占位值，以避免误导用户认为视频/TTS 也已在本批次完成。

### 5. `README.md`

README 已同步更新，重点反映：

- Google provider 不再是纯占位
- 当前真实 provider 范围仅限 `render_image -> google / imagen-3.0-generate-002`
- 其余 executor 仍为 stub
- 下一步建议从“至少接一个真实 provider”更新为“扩展第二个真实 provider executor”

## 契约与边界说明

### 已保持不变的约束

- runtime asset path 仍为：
  - `projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`
- project upload registration path 仍为：
  - `projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`
- `StorageService` bucket map 不变
- `RuntimeArtifactService` 契约不变
- `Asset.status` 推进模型不变
- `RuntimeStateService` 聚合逻辑不变
- `CompilerService` 其他 job payload 契约不变

### 本批次刻意不做的事

为避免范围漂移，本批次没有：

- 引入新的 provider SDK
- 改动 worker materialization 主干
- 增加新的数据库字段或 Alembic migration
- 扩展新的 API route
- 让 `render_video` / `render_voice` 同步落地

## 已知风险与注意事项

### 1. Google endpoint 契约仍是基于最小公开线索实现

由于在线抓取官方文档时 `web_fetch` 遇到 403，本批次的 HTTP endpoint 与最小响应结构是基于已确认的搜索结果和常见 Gemini/Imagen 响应形态做兼容实现。

这意味着：

- endpoint 大概率正确，但仍需真实 API key 下的实跑验证
- 响应字段已尽量兼容多种 base64 图片承载位置
- 若 Google 后端对 `predict` 契约有细微差异，可能需要做一次小修补

### 2. Prompt 注入策略目前是“最小可运行”，不是最终提示工程

当前 prompt 构造只解决：

- `render_image` executor 能跑起来
- compile -> dispatch 合同闭合

它尚未解决：

- 多 SPU 优先级治理
- 更强的 sequence 级镜头语义编译
- visual constraints 结构化展开
- brand-safe / compliance-safe prompt layering

### 3. Provider 失败分类仍可继续细化

当前 Google 相关错误已做基础归一，但后续仍可继续拆分：

- 配置错误
- 认证错误
- 配额/频控错误
- 参数错误
- 响应结构错误
- 空图/损坏图错误

## 第七批完成定义

本批次的完成定义是：

1. `render_image` 存在最小真实 provider executor
2. compile 阶段可为 `render_image` 注入最小 prompt / `provider_inputs`
3. worker 可将 Google 图片结果经既有 materialization 主干写入对象存储
4. README / env / batch notes 与代码状态一致
5. `python -m compileall app` 通过

## 建议的下一批最小方向

推荐第八批仍维持“小闭环、低风险”原则，可优先考虑以下二选一：

1. `render_voice` 第二个真实 provider executor
2. 在 `render_image` 上补一层更明确的 provider failure classification + smoke test harness

如果继续追求 runnable closure，而不是能力堆叠，那么优先级更建议落在：

- 实跑验证
- 失败分类
- 最小 smoke test
- 文档化运行步骤
