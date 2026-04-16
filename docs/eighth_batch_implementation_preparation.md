# Eighth Batch Implementation Preparation

## 批次主题

第八批不扩展第二个真实 provider，也不回头改写第七批已关闭实现；范围严格锁定为：

- `render_image` 的 smoke test 准备
- `render_image` 的 real-run checklist 准备
- `render_image` 的 failure classification 准备

本批次目标不是“把更多能力做进去”，而是把第七批已经接通的最小真实链路，推进到**可控试跑、可判错、可留痕、可验收**的状态。

---

## 一、批次定位

第七批已经完成的闭环是：

- compiler 为 `render_image` 注入最小 prompt / `provider_inputs`
- worker executor 将 `render_image` 切换到 Google Imagen 真实执行器
- provider 返回图片二进制后，走既有 materialization 主干写入对象存储
- `python -m compileall app` 已通过

但第七批仍保留一个明确缺口：

- **尚未在真实 Google API key / 真实运行环境下完成 smoke test**

因此，第八批的价值不在于新接一个 executor，而在于为第七批真实链路补上“上线前最小试跑治理层”。

---

## 二、本批次明确产物

第八批实施准备应只面向以下三类产物：

### 1. smoke test 方案

定义一个最小、低成本、低风险的 `render_image` 试跑入口，用来回答三个问题：

- 当前环境是否真的具备调用 Google Imagen 的条件
- 当前 compiler -> dispatch -> worker -> object store 链路是否真的闭合
- 当前失败能否被归类为“配置问题 / provider 问题 / 运行链路问题 / 结果落库问题”

### 2. real-run checklist

把一次真实试跑前、中、后的检查点写成可执行清单，避免试跑结果无法解释。

### 3. failure classification

为 `render_image` 的真实运行建立最小失败分类体系，使后续日志、job 状态、runtime 聚合和人工排查有共同语言。

---

## 三、严格范围边界

### 本批次覆盖

- `render_image -> google / imagen-3.0-generate-002`
- 真实运行前的环境核验
- 真实运行中的请求/响应/对象存储/DB 状态检查点
- 失败分类与验收口径
- 如有必要，只做**小范围、低风险、局部化**的 observability/错误归一增强

### 本批次不覆盖

- `render_video -> google / veo-3.1-generate-001`
- `render_voice -> google / gemini-2.5-flash`
- 大规模 worker 架构重构
- retry/backoff/dead-letter 完整体系
- 图像内容质量打分系统
- 复杂 prompt 编排升级
- 新 schema / 新 migration / 新 API 面扩张

### 约束重申

- 第七批必须保持已关闭状态
- 既有 runtime / asset path 约束不得漂移
- 既有 materialization backbone 不做推倒重来
- 继续采用安全的逐文件写入方式，不依赖批量 shell 覆盖

---

## 四、as-built 基线（第八批准备的既有前提）

### 1. Provider client 已具备最小真实调用能力

`app/providers/google/client.py` 已具备：

- `GoogleProviderError`
- `GoogleGeneratedImage`
- `GoogleProviderClient.generate_image(...)`
- `POST https://generativelanguage.googleapis.com/v1beta/models/{image_model}:predict`
- base64 图片解析与最小错误归一

### 2. Worker executor 已切换真实 render_image 执行器

`app/workers/executors.py` 已具备：

- `GoogleImagenExecutor`
- prompt 从 `job.payload` / `provider_inputs` 读取
- 成功时输出 `binary_payload` + `content_type`
- 失败时抛出 `GoogleProviderError`

### 3. Compiler 已给 render_image 注入最小 prompt

`app/compilers/orchestrator/compiler_service.py` 已具备：

- `_build_render_image_payload(project_id, runtime_version)`
- `provider_inputs.prompt`
- `provider_inputs.negative_prompt`
- `provider_inputs.sample_count = 1`
- `provider_inputs.aspect_ratio = "9:16"`
- `provider_inputs.source = "compiler_minimal_render_image_prompt_v1"`

### 4. Materialization backbone 已存在

`app/workers/tasks.py` 已具备：

- provider 结果 materialize 到 object store
- DB / object store 幂等短路
- asset 成功/失败回写
- runtime 聚合刷新

这意味着第八批不需要重新证明“代码路径存在”，而是要证明“该路径在真实环境中可解释地运行”。

---

## 五、第八批建议拆分为 3 个最小实施子项

### 子项 A：smoke test harness / entrypoint 准备

目标：建立一次最小真实 `render_image` 试跑的方法学，不要求一次性做成完整测试平台。

建议落点：

1. 明确 smoke test 的最小前置条件
2. 明确 smoke test 的触发方式
3. 明确 smoke test 成功与失败的观察点
4. 明确 smoke test 输出记录格式

建议优先级：最高。

### 子项 B：real-run checklist 固化

目标：让任何一次真实试跑都能按同一套 checklist 执行和复盘。

建议优先级：高。

### 子项 C：failure classification 最小归类

目标：把“跑不通”拆成若干稳定错误域，而不是只留下一个 `google_image_generation_failed`。

建议优先级：高。

---

## 六、smoke test 设计原则

### 原则 1：先验证环境，再验证业务

先确认：

- 配置是否齐全
- 服务是否可启动
- 编译是否能生成合法 `render_image` job payload
- worker 是否真的走到 Google executor

再确认：

- provider 是否返回图片字节
- object store 是否 materialize 成功
- asset / job / runtime 是否状态一致

### 原则 2：优先走最小真实路径，不引入过多新依赖

smoke test 不追求覆盖所有情况，只回答：

- 这条链路能不能真实跑通一次
- 如果失败，失败点在哪一层

### 原则 3：试跑输入尽量稳定、低成本

建议：

- 只使用一个最小 project
- 只保证存在一个可用于 `render_image` 的 SPU prompt
- 不在本批次引入复杂的多 sequence / 多 SPU 对比试验

### 原则 4：试跑产物必须可回看

smoke test 至少应留下：

- job id
- runtime version
- provider model
- prompt 来源标识
- provider 原始摘要
- asset bucket/object key
- 最终 object 是否存在

---

## 七、建议的 smoke test 流程

### Phase 0：静态前置核验

在任何真实试跑前，先完成以下检查：

1. `python -m compileall app` 继续保持通过
2. `.env` 中至少配置：
   - `GOOGLE_API_KEY`
   - `GOOGLE_IMAGE_MODEL=imagen-3.0-generate-002`
3. PostgreSQL / Redis / MinIO / API / worker 均已启动
4. bucket 已由应用 startup 或显式初始化创建
5. 待试跑 project 至少具备：
   - 1 个 project
   - 1 个 sequence
   - 1 个带非空 `prompt_text` 的 SPU

### Phase 1：compile 入口检查

发起一次 `dispatch_jobs=true` 的 compile 后，需要确认：

1. `CompiledRuntime` 已创建
2. `runtime_version` 已生成
3. `dispatch_summary` 中包含 `render_image`
4. `render_image` 对应 `Job.payload` 中存在：
   - `prompt`
   - `negative_prompt`（可为空）
   - `provider_inputs.prompt`
   - `provider_inputs.aspect_ratio = "9:16"`
   - `provider_inputs.source = "compiler_minimal_render_image_prompt_v1"`

### Phase 2：worker 执行检查

观察 `render_image` job 从 `queued/dispatched` 进入运行态时，应确认：

1. worker 已解析到 `render_image`
2. executor registry 命中 `GoogleImagenExecutor`
3. 未因缺少 prompt 抛出 `google_image_prompt_missing`
4. 未因缺失 key / model 抛出配置类错误

### Phase 3：provider 响应检查

当 Google 接口返回后，应确认：

1. HTTP 调用成功返回 2xx
2. `predictions` 非空
3. 响应中能提取 base64 图片
4. base64 解码后得到非空二进制
5. `content_type` 已识别，未知时 fallback 到 `image/png`

### Phase 4：materialization 检查

provider 成功后，应确认：

1. worker 走入 `_materialize_generated_asset(...)`
2. runtime asset 路径符合：
   - `projects/{project_id}/runtime/{runtime_version}/render_image/{job_id}.png`
3. MinIO 对象存在
4. asset 行存在或被 upsert 成功
5. asset 状态为 `materialized`
6. `file_size`、`content_type`、`asset_metadata.materialization_status` 已回写

### Phase 5：聚合结果检查

最后应确认：

1. `Job.status` 为成功态
2. `Job.result_payload` 含 provider 执行摘要
3. `CompiledRuntime` 聚合状态已刷新
4. 不应出现“job 成功但 asset 未 materialized”且无错误说明的悬空状态

---

## 八、real-run checklist（建议固化为执行清单）

以下清单可直接作为第八批真实试跑的最小验收单。

### A. 环境准备清单

- [ ] 本地/目标环境可读取有效 `GOOGLE_API_KEY`
- [ ] `GOOGLE_IMAGE_MODEL` 明确为 `imagen-3.0-generate-002`
- [ ] PostgreSQL 已连接正常
- [ ] Redis 已连接正常
- [ ] MinIO 已连接正常
- [ ] API 服务已启动
- [ ] worker 服务已启动
- [ ] bucket 已存在
- [ ] `python -m compileall app` 再次通过

### B. 测试数据准备清单

- [ ] 目标 project 已存在
- [ ] 至少 1 个 sequence 已存在
- [ ] 至少 1 个 SPU `prompt_text` 非空
- [ ] `display_name` 合理可读
- [ ] 如有 `negative_prompt_text`，其内容已确认非垃圾值
- [ ] 项目 market/language/notes 不含明显脏数据

### C. 编译检查清单

- [ ] compile 成功返回 `runtime_version`
- [ ] `CompiledRuntime.runtime_payload` 已落库
- [ ] `dispatch_summary.jobs` 中出现 `render_image`
- [ ] `render_image` job `payload.prompt` 非空
- [ ] `render_image` job `payload.provider_inputs.prompt` 非空
- [ ] `render_image` job `payload.provider_inputs.aspect_ratio = "9:16"`
- [ ] `external_task_id` 已回写（若使用异步派发）

### D. 执行检查清单

- [ ] worker 已消费该 `render_image` job
- [ ] executor 为 `google`
- [ ] 未触发 prompt 缺失错误
- [ ] 未触发 provider 未配置错误
- [ ] `provider_payload.google.model` 可见
- [ ] `binary_payload` 实际生成

### E. 落库/落对象检查清单

- [ ] runtime asset object key 符合既定路径规范
- [ ] 对象存储内已存在对应 object
- [ ] `Asset.status = materialized`
- [ ] `Asset.file_size > 0`
- [ ] `Asset.content_type` 合理
- [ ] `asset_metadata.materialization_status` 为成功态

### F. 结果验收清单

- [ ] `Job.status` 为成功态
- [ ] `CompiledRuntime.dispatch_status / compile_status` 聚合合理
- [ ] 生成图片可被人工打开
- [ ] 本次试跑的 prompt、job_id、runtime_version、object key 已被记录
- [ ] 本次试跑是否通过，可被一句话明确判定

---

## 九、failure classification：建议的最小错误域

第八批的关键不是立刻覆盖所有错误，而是先建立可落地的最小分类体系。建议按 6 个错误域划分。

### 1. `configuration_error`

定义：环境变量缺失、模型未配置、服务端基本配置不满足运行。

典型触发：

- `google_provider_not_configured`
- `google_image_model_not_configured`

建议判定规则：

- 发生在发起 HTTP 请求之前
- 与输入业务数据无关
- 重试通常无意义，需先修配置

### 2. `input_contract_error`

定义：编译出来的 `render_image` job payload 不满足 executor 最小契约。

典型触发：

- `google_image_prompt_missing`
- `provider_inputs` 缺字段
- prompt 为纯空白或脏值

建议判定规则：

- 责任层主要在 compiler / project data
- 需要回头检查项目数据或编译注入逻辑

### 3. `provider_request_error`

定义：请求已经发出，但被 provider 以参数非法、认证失败、权限失败、配额失败等方式拒绝。

典型触发：

- HTTP 400/401/403/429
- provider error body 可解析，但请求未成功

建议细分子类：

- `provider_auth_error`
- `provider_permission_error`
- `provider_quota_error`
- `provider_bad_request_error`

即使第八批先不完全写入 DB 枚举，也建议日志和错误消息先按这一思路归一。

### 4. `provider_transport_error`

定义：请求发出过程中发生网络/超时/连接层异常。

典型触发：

- DNS/连接失败
- `httpx.HTTPError`
- provider 无响应超时

建议判定规则：

- 可能可重试
- 与业务 prompt 语义无直接关系

### 5. `provider_response_error`

定义：provider 返回 2xx 或返回体存在，但结构不符合当前解析契约。

典型触发：

- `predictions` 缺失或为空
- base64 字段缺失
- base64 无法解码
- 解码结果为空

当前已存在的代码映射：

- `google_provider_response_invalid`

建议后续可细分为：

- `provider_response_missing_predictions`
- `provider_response_missing_image_bytes`
- `provider_response_invalid_base64`
- `provider_response_empty_image`

### 6. `materialization_error`

定义：provider 已返回成功图片，但在对象存储写入、asset 更新、DB 事务回写阶段失败。

典型触发：

- MinIO put 失败
- asset upsert / commit 失败
- object exists 与 DB 状态不一致且 reconcile 失败

建议判定规则：

- 说明真实生成已发生，但系统内资产治理未完成
- 与 provider 生成质量无关
- 必须与 provider 错误区分开

---

## 十、建议的错误映射表（第八批实现时参考）

| 当前/候选错误码 | 建议错误域 | 主要责任层 | 是否建议重试 | 备注 |
|---|---|---|---|---|
| `google_provider_not_configured` | `configuration_error` | env/config | 否 | 先修配置 |
| `google_image_model_not_configured` | `configuration_error` | env/config | 否 | 先修配置 |
| `google_image_prompt_missing` | `input_contract_error` | compiler/data | 否 | 先查 payload |
| HTTP 400 | `provider_request_error` | provider/input | 否 | 多半参数问题 |
| HTTP 401 | `provider_request_error` | auth | 否 | key 不合法 |
| HTTP 403 | `provider_request_error` | permission/policy | 否 | 权限或策略拒绝 |
| HTTP 429 | `provider_request_error` | quota/rate-limit | 可选 | 后续批次再做退避 |
| 网络超时/连接失败 | `provider_transport_error` | network/provider | 可选 | 第八批可先做归类 |
| `google_provider_response_invalid` | `provider_response_error` | provider/adapter | 视情况 | 需看 response body |
| object put / DB reconcile 失败 | `materialization_error` | storage/db | 视情况 | 必须独立记录 |

---

## 十一、建议的最小观测字段

第八批即使不大改 schema，也建议在日志、result payload、错误消息或 notes 中尽量保留以下信息：

- `job_id`
- `project_id`
- `runtime_version`
- `job_type`
- `provider_name`
- `provider_model`
- `error_code`
- `error_domain`
- `http_status`（如有）
- `object_bucket`
- `object_key`
- `content_type`
- `file_size`
- `prompt_source`

如果本批次允许做极小改动，优先建议把这些字段放进：

- `Job.error_code`
- `Job.error_message`
- `Job.result_payload`
- `Asset.asset_metadata`

而不是先改数据库结构。

---

## 十二、建议的 smoke test 通过标准

一次 `render_image` smoke test 要被判定为“通过”，建议至少满足以下条件：

1. compile 成功且生成 `render_image` job
2. worker 真实命中 Google executor
3. provider 返回非空图片字节
4. 对象存储内出现对应图片对象
5. `Asset.status = materialized`
6. `Job.status` 为成功态
7. `CompiledRuntime` 聚合状态无明显悬空
8. 能追溯本次运行的 `prompt / model / runtime_version / object key`

如果只拿到 provider 成功响应，但 object store / DB 没完成，则应判定为：

- **provider succeeded, pipeline not closed**

不能算 batch 8 smoke test 通过。

---

## 十三、建议的 smoke test 失败判定模板

后续真实试跑时，建议统一使用以下复盘模板：

### 失败记录模板

- `run_label`:
- `project_id`:
- `runtime_version`:
- `job_id`:
- `job_type`: `render_image`
- `provider`: `google`
- `model`: `imagen-3.0-generate-002`
- `result`: `passed / failed`
- `error_domain`:
- `error_code`:
- `http_status`:
- `failure_stage`: `compile / dispatch / executor / provider / materialization / runtime_aggregate`
- `object_key`:
- `notes`:
- `next_action`:

这样后续不论是 README 补充、issue 记录还是 commit note，都能直接复用。

---

## 十四、建议的第八批最小实施顺序

第八批真正开始编码/验证时，建议顺序如下：

1. **先固化 checklist**
   - 明确试跑前检查项与通过标准
2. **再补 failure classification 最小归一**
   - 不追求完美，只先把错误域分开
3. **最后做一次真实 smoke test**
   - 用最小 project 跑通一条真实 `render_image`
4. **记录 closure artifact**
   - 沉淀 real-run 结果、失败样例、已知边界

这个顺序的好处是：

- 即使第一次 smoke test 失败，也不是无序失败
- 可以直接定位是配置、输入、provider、还是 materialization 层问题
- 第八批 closure 会比第七批更接近“可运营的真实链路”

---

## 十五、建议的第八批完成定义（Definition of Done）

第八批若要正式关闭，建议完成定义为：

1. 已形成一份明确的 `render_image` real-run checklist
2. 已形成最小 failure classification 与错误域映射
3. 已进行至少一次真实 smoke test（成功或失败均可，但必须有记录）
4. 若失败，失败已被稳定归类并留存可复盘证据
5. 若成功，已证明 compile -> dispatch -> worker -> provider -> materialize -> aggregate 的真实闭环
6. 文档与 as-built 状态保持一致
7. `python -m compileall app` 继续纳入完成标准

---

## 十六、对下一步实施的明确建议

如果紧接着进入第八批开发执行，建议不要并行做太多事，优先只做下面这个窄闭环：

### 推荐第八批首个真正实施目标

- 为 `render_image` 增加最小 smoke-test-ready observability 与 failure classification
- 然后在真实凭证环境下跑一次最小 smoke test

### 不建议第八批同时做的事

- 再接 `render_voice`
- 再接 `render_video`
- 重写 prompt 编译层
- 做完整 retry 框架
- 做复杂 QA 体系

原因很简单：

第七批的问题不是“没有真实 executor”，而是“还没有被真实环境验证并归类”。第八批应优先解决验证与治理，而不是继续扩能力面。
