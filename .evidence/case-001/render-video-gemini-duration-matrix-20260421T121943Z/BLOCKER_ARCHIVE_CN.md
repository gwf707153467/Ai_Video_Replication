# case-001 / downstream-blocker-01 / render_video-gemini-compat 结论归档（中文最小版）

## 1. 结论摘要

当前关于历史 Google 视频 `400 INVALID_ARGUMENT: durationSeconds out of bound` 的最高可信结论已经可以收敛为：

- 历史失败**不是**由本地链路把 `durationSeconds` 传错、改写或污染导致。
- 在同账号、同 API 路径、同模型、同 prompt、同 `sampleCount=1`、且不传 `generateAudio` 的最小直调对照实验下，只有 `durationSeconds=5` 失败，而 `4/6/8` 均成功提交。
- 因此，当前 blocker 更应归因于 **Google 服务端/接口兼容性/账号能力矩阵侧的异常**，而不能回退到“本地 duration 传坏了”的旧假设。

一句话归纳：**当前 `veo-3.1-generate-preview` 在 Generative Language `v1beta` 路径下，对 `durationSeconds=5` 表现出可复现的特异性异常。**

---

## 2. 固定上下文

本结论仅覆盖以下任务边界：

- case: `case-001`
- blocker: `downstream-blocker-01`
- scope: `render_video-gemini-compat`

固定业务上下文：

- `project_id=656ac6b1-ecb8-4f45-9f45-556be5915168`
- `runtime_version=v17`
- `job_id=cd591b28-fd78-4723-95bf-33d1961bc543`
- `compiled_runtimes.runtime_payload.sequences[0].spus[0].duration_ms=5000`
- `primary_spu.duration_ms=5000`
- `provider_inputs=null`
- `provider_inputs.duration_seconds=None`
- 一次性只读 Python 验证结果：
  - `provider_inputs.duration_seconds=None`
  - `primary_spu.duration_ms=5000`
  - `generation_options.duration_seconds=5`

---

## 3. 已锁定的历史证据

历史证据目录：

- `.evidence/case-001/render-video-gemini-compat-request-capture-20260420T153612Z/`

关键文件：

- `latest_predict_long_running.json`
- `raw_http_replay.json`
- `request_events.jsonl`
- `runtime_snapshot_final.json`
- `run_summary.json`
- `BLOCKER_SUMMARY.md`

已锁定事实如下：

### 3.1 本地业务链路传到最终请求前的值是 5

已通过运行态、执行器、provider client、SDK materialization 与真实请求重建共同固定：

- runtime/job/executor 输入链路显示 `duration_seconds=5`
- provider client config 显示 `duration_seconds=5`
- SDK 最后一跳 `request_dict.parameters.durationSeconds=5`
- 真实出站 HTTP body `parameters.durationSeconds=5`
- `generateAudio` 未发送

这说明：**历史报错发生时，本地最终送出的值就是 5。**

### 3.2 历史真实失败与请求体并不一致

即使真实出站体中已经明确包含：

- `parameters.sampleCount = 1`
- `parameters.durationSeconds = 5`
- `parameters.negativePrompt = ...`
- `generateAudio` absent

Google 仍返回：

- `400 INVALID_ARGUMENT`
- `The number value for durationSeconds is out of bound. Please provide a value between 4 and 8, inclusive.`

### 3.3 同请求体 raw HTTP replay 仍复现相同失败

将同样 body 直接 POST 到：

- `https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning`

仍得到相同 `400 INVALID_ARGUMENT`。

这一步进一步降低了以下解释的可信度：

- 本地 app 组装错误
- executor 归一化错误
- SDK 序列化把 `5` 改坏

---

## 4. 新增最小对照实验

新增脚本：

- `scripts/case_001_gemini_duration_matrix.py`

真实实验执行方式：

- 在 `avr_app` 容器内运行
- SDK：`google-genai==1.73.1`
- API key：读取 `.env` 中 `GOOGLE_API_KEY`
- API 面：Generative Language `v1beta`
- endpoint：`https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning`
- model：`veo-3.1-generate-preview`
- 固定历史 prompt
- 固定历史 negative prompt
- 固定 `sampleCount=1`
- 不传 `generateAudio`
- 仅改变 `durationSeconds ∈ {4,5,6,8}`
- 采用 `--skip-poll`，只验证“请求是否被接受”

证据目录：

- `.evidence/case-001/render-video-gemini-duration-matrix-20260421T121943Z`

关键输出：

- `experiment_plan.json`
- `run_log.txt`
- `sdk_duration_4.json`
- `sdk_duration_5.json`
- `sdk_duration_6.json`
- `sdk_duration_8.json`
- `duration_matrix_summary.json`
- `FINAL_ASSESSMENT.md`
- `container_google_genai_version.txt`
- `container_stdout.json`

---

## 5. 对照实验结果

矩阵摘要：

- `model=veo-3.1-generate-preview`
- `api_surface=generative-language-v1beta-via-google-genai`
- `sdk_version=1.73.1`
- `durations_tested=[4,5,6,8]`
- `pattern=only_5_failed`

逐项结果：

- `duration=4`：成功提交
  - operation: `models/veo-3.1-generate-preview/operations/0o9t01gurlcn`
- `duration=5`：失败
  - error_type: `ClientError`
  - error_message: `400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'The number value for \`durationSeconds\` is out of bound. Please provide a value between 4 and 8, inclusive.', 'status': 'INVALID_ARGUMENT'}}`
- `duration=6`：成功提交
  - operation: `models/veo-3.1-generate-preview/operations/98ch47v9ayib`
- `duration=8`：成功提交
  - operation: `models/veo-3.1-generate-preview/operations/8spsno6hbwtg`

其中 `sdk_duration_5.json` 还固定了以下事实：

- `config_dump.duration_seconds = 5`
- `request_body_expected.parameters.durationSeconds = 5`
- 返回仍为同一条 `out of bound` 错误

因此，这次实验回答了一个关键问题：

**不是所有合法区间值都失败，而是只有 5 失败。**

---

## 6. 最终判断

基于“历史真实请求捕获 + raw HTTP replay + 当前最小 matrix 直调实验”三层证据，当前最稳妥的判断是：

### 6.1 可以排除或显著降级的方向

以下方向不再应作为主根因假设：

- 本地把 `durationSeconds` 传错
- 本地把 `5` 改写成别的值
- `generateAudio` 连带污染视频请求
- SDK 在本地把 `durationSeconds=5` 错序列化为非法值

### 6.2 当前最高可信根因方向

更高可信的解释是：

- Google 服务端校验缺陷
- preview 模型在当前 Generative Language `v1beta` 集成下存在兼容性异常
- 当前账号/区域/模型能力矩阵对 `durationSeconds=5` 存在未文档化限制或异常
- 文档表述与真实后端行为不一致

### 6.3 可提交表述

建议对 blocker 采用如下归档说法：

> 历史 Google `durationSeconds out of bound` 失败并非由本地 duration 传播错误导致。历史证据已确认真实出站请求体中 `parameters.durationSeconds=5` 且未发送 `generateAudio`；相同 body 的 raw HTTP replay 仍返回同一 400。进一步地，在同账号、同模型、同 Generative Language `v1beta` 路径、同 prompt/negative prompt、仅切换 `durationSeconds=4/5/6/8` 的最小直调实验中，`4/6/8` 均成功提交，仅 `5` 单独失败。故当前 blocker 更应归因于 Google 服务端/接口兼容性/能力矩阵侧的特异性异常，而非本地链路错误。

---

## 7. 判断边界

本结论的边界必须明确保留：

- 本结论仅覆盖 **当前账号 + 当前模型 `veo-3.1-generate-preview` + 当前 API 面 `Generative Language v1beta` + 当前 prompt 条件** 下的请求接收行为。
- 本结论**不等于**证明 Vertex AI 路径也有同样问题。
- 本结论**不等于**证明 preview 模型整体不可用，而是证明当前组合下 `durationSeconds=5` 存在可复现异常。
- 本结论已经足够否定“本地把 duration 传坏了”的旧假设，但并不自动给出 Google 上游的内部实现原因。

---

## 8. 建议的 blocker 状态更新

建议将该 blocker 的状态说明更新为：

- blocker 仍存在，但定位方向已从“本地请求组装问题”转为“Google 上游行为异常/兼容性问题”
- 当前本地侧无新增证据支持继续投入在 duration 组装、executor 归一化或 SDK payload 重建上
- 后续若要继续推进，高价值方向应是：
  - 面向上游/平台差异（Generative Language vs Vertex AI）的兼容性核实
  - 或在产品侧采用规避策略（例如避免 `durationSeconds=5`），前提是该策略被明确接受为 workaround 而非根因修复
