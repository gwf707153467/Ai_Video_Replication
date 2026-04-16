# Runtime terminal operator troubleshooting matrix v1

## 1. 文档目的

本文档面向 runtime terminal v1 的值班人员、维护者、排障执行者，目标不是重写 contract，而是把**常见症状 → 可能原因 → 优先检查点 → self-check 动作 → 升级建议**整理成一份可直接使用的 troubleshooting matrix。

适用前提：
- runtime terminal v1 已封板
- complete / fail 写侧语义不重开
- facade 写侧不绕过 service 直写 repository
- 422 继续保持 FastAPI / Pydantic 默认行为

本文档与以下材料配套使用：
- `runtime_terminal_api_contract_pack_v1.md`
- `runtime_terminal_orchestration_explainer_v1.md`
- `runtime_terminal_self_check_pack_v2.md`
- `runtime_terminal_self_check_runbook.md`

---

## 2. 使用方法

值班排障建议按固定顺序执行：

1. 先识别症状属于哪一类
2. 先看是否是 **404 / 409 / 422 / 结果异常 / 状态异常** 之一
3. 用 `GET /api/v1/runtime/terminal/jobs/{job_id}` 读取 terminal snapshot
4. 对照本矩阵检查 job / latest attempt / active lease 三层字段
5. 再决定：
   - 是否跑 self-check
   - 是否可以安全重试
   - 是否需要人工介入

一个原则：
- **先确认是不是调用参数/claim 上下文问题，再怀疑服务实现问题**

---

## 3. 排障检查总原则

## 3.1 优先看的 4 组身份字段

无论是 complete 还是 fail，先核对以下 4 个字段是否来自同一次真实 attempt：
- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

如果这 4 个字段中任意一个来自旧 attempt、旧 worker、旧 lease，很多问题都会表现成 409，而不是系统 bug。

## 3.2 优先看的 3 层快照

读取 `GET /jobs/{job_id}` 后，优先拆成 3 层看：

### job 层
重点字段：
- `job_status`
- `claimed_by_worker_id`
- `active_claim_token`
- `attempt_count`
- `finished_at`
- `lease_expires_at`
- `terminal_reason_code`
- `terminal_reason_message`

### latest attempt 层
重点字段：
- `attempt_id`
- `attempt_status`
- `worker_id`
- `claim_token`
- `completion_status`
- `error_code`
- `error_message`
- `error_payload_json`
- `result_ref`
- `manifest_artifact_id`
- `runtime_ms`
- `provider_runtime_ms`
- `upload_ms`

### active lease 层
重点字段：
- `lease_id`
- `lease_status`
- `worker_id`
- `claim_token`
- `lease_started_at`
- `lease_expires_at`
- `last_heartbeat_at`
- `heartbeat_count`
- `extension_count`
- `revoked_at`
- `revoked_reason`

## 3.3 先区分“请求错误”还是“状态冲突”

优先按下面方式分类：
- 404：目标 job 不存在或读取对象不存在
- 409：lease / state 冲突，通常是并发、重复提交、上下文不一致
- 422：请求模型不合法，属于调用参数问题
- 200 但业务结果不符合预期：进入状态/语义排障

---

## 4. Troubleshooting matrix

## 4.1 症状：`GET /jobs/{job_id}` 返回 404

| 维度 | 说明 |
|---|---|
| symptom | snapshot 查询返回 `runtime_job_not_found` |
| probable cause | `job_id` 填错；调用方保存的是外部业务 ID 而不是 runtime `job_id`；job 尚未创建成功；读的是错误环境/错误库 |
| first checks | 核对 `job_id` 来源；确认当前访问的是 `/api/v1/runtime/terminal/jobs/{job_id}`；确认环境与数据库实例没有切错 |
| snapshot check points | 无法读取 snapshot 时，优先回到 job 创建来源核对真实 `job_id` |
| self-check action | 如怀疑服务路由异常，可跑 `--check endpoint` |
| safe retry? | 仅在确认 `job_id` 录入错误时可重试查询；不要盲目重复查同一个无效 ID |
| escalation guidance | 若同批次多个已知 job 全部 404，升级为环境/路由/数据初始化排查 |

---

## 4.2 症状：`POST /complete` 或 `POST /fail` 返回 409 且 `error_type=runtime_lease_conflict`

| 维度 | 说明 |
|---|---|
| symptom | terminal 写入返回 lease conflict |
| probable cause | `worker_id` 不匹配；`claim_token` 来自旧 lease；`attempt_id` 不属于当前 worker；lease 已被释放/过期/切换 |
| first checks | 先核对 `job_id + attempt_id + worker_id + claim_token` 是否来自同一运行上下文 |
| snapshot check points | 看 `active_lease.worker_id`、`active_lease.claim_token`、`latest_attempt.worker_id`、`latest_attempt.attempt_id` 是否与请求一致 |
| self-check action | 一般无需先跑全量；若怀疑接口回归可跑 `--check endpoint`；若怀疑冻结编排被破坏可加跑 `--check workflow` |
| safe retry? | **通常不建议直接原样重试**；先修正 claim 上下文再决定是否重发 |
| escalation guidance | 若同一 worker 大量出现 lease conflict，升级检查 claim/heartbeat/lease 生命周期管理 |

排障判断要点：
- `runtime_lease_conflict` 优先怀疑“谁在写”不对，而不是“写逻辑坏了”
- 如果 snapshot 显示 active lease 已属于别人，原调用方不应再继续提交 terminal 写入

---

## 4.3 症状：`POST /complete` 或 `POST /fail` 返回 409 且 `error_type=runtime_state_conflict`

| 维度 | 说明 |
|---|---|
| symptom | terminal 写入返回 state conflict |
| probable cause | job 已经 terminal；同一 attempt 被重复提交；先前请求已成功收口；调用方重放了旧 terminal 请求 |
| first checks | 看 job 是否已是 `SUCCEEDED / FAILED / STALE` 等终态；看 `finished_at` 是否已有值 |
| snapshot check points | 重点看 `job_status`、`finished_at`、`terminal_reason_code`、`latest_attempt.attempt_status` |
| self-check action | 一般先不跑；若怀疑路由错误映射，再跑 `--check endpoint` |
| safe retry? | **通常不安全**；需先确认是否已经成功收口，避免重复回写 |
| escalation guidance | 若出现“实际未收口但持续 state conflict”，升级检查 job terminal state 判定链路 |

排障判断要点：
- 若 snapshot 显示 job 已 terminal，这类 409 往往是幂等/重复提交问题
- 先判断是否其实已经成功或失败写入过，再决定是否需要人工修复

---

## 4.4 症状：请求返回 422 validation error

| 维度 | 说明 |
|---|---|
| symptom | FastAPI/Pydantic 默认 422 结构返回 |
| probable cause | 字段缺失；字段类型错误；`next_job_status` / `attempt_terminal_status` 非允许值；显式传了 `error_payload_json=null` |
| first checks | 直接查看 422 body，定位字段级报错；检查请求 JSON 是否符合 schema |
| snapshot check points | 通常不需要先看 snapshot，因为请求在进入 service 前就已被拒绝 |
| self-check action | 若怀疑 schema 导入面异常，可跑 `--check imports`；一般不需要跑 workflow |
| safe retry? | 可以，在修正 payload 后重试 |
| escalation guidance | 若调用方频繁 422，升级为接入文档/调用 SDK 侧修正，而不是服务排障 |

排障判断要点：
- 422 不是 terminal 顶层统一错误模型的一部分
- 这类问题优先交给调用方修 payload，不应当作 runtime terminal 状态异常处理

---

## 4.5 症状：`POST /complete` 返回 200，但 snapshot 看起来不像成功收口

| 维度 | 说明 |
|---|---|
| symptom | complete 已成功返回，但调用方观察到状态/结果字段不符合预期 |
| probable cause | 读取时机过早；误读 job/attempt 字段；关注了旧 attempt；对 `completion_status` 与 `job_status` 的语义理解混淆 |
| first checks | 先确认读取的是同一个 `job_id`；确认关注的是 latest attempt；区分 job terminal 状态与 attempt 完成状态 |
| snapshot check points | 看 `job_status` 是否为成功终态；看 `latest_attempt.completion_status`、`result_ref`、`manifest_artifact_id`、`finished_at` |
| self-check action | 若怀疑 endpoint contract 回归可跑 `--check endpoint`；若怀疑 workflow 收口顺序异常可跑 `--check workflow` |
| safe retry? | 不建议先重提 complete；先确认是否已成功收口 |
| escalation guidance | 若 200 返回与 snapshot 长期不一致，升级检查读侧聚合与写后读取链路 |

排障判断要点：
- `completion_status` 是 attempt 成功补充字段，不等于 job status 本身
- `active_lease = null` 在成功释放后可能是正常结果，不代表异常

---

## 4.6 症状：`POST /fail` 返回 200，但 job 没有进入期望的后续走向

| 维度 | 说明 |
|---|---|
| symptom | fail 已成功返回，但调用方认为 job 状态“错了” |
| probable cause | `next_job_status` 选择错误；把 attempt terminal status 与 job status 混淆；对 `WAITING_RETRY / FAILED / STALE` 解释不一致 |
| first checks | 回看 fail 请求中的 `next_job_status` 和 `attempt_terminal_status`；确认调用方设计意图 |
| snapshot check points | 看 `job_status`、`terminal_reason_code`、`terminal_reason_message`、`latest_attempt.attempt_status` |
| self-check action | 如怀疑 fail 编排被破坏，跑 `--check workflow` |
| safe retry? | 谨慎；若已成功写入 terminal，不应直接用另一次 fail 覆盖语义 |
| escalation guidance | 若问题本质是“调用策略选错终态”，升级为调用方流程治理，而不是服务缺陷 |

排障判断要点：
- `attempt_terminal_status=TIMED_OUT` 不自动意味着 job 一定 `FAILED`
- job 走向由 `next_job_status` 决定，应与重试策略一起解读

---

## 4.7 症状：job 卡住，调用方怀疑 lease 没有正确释放

| 维度 | 说明 |
|---|---|
| symptom | job 看似已处理完，但后续观察仍怀疑被 lease 占用 |
| probable cause | 误读 active lease 视图；lease 仍在有效期内；fail 时使用了 `expire_lease=False` 走 release 分支；或调用方读取到的并非预期 job |
| first checks | 先看 `active_lease` 是否存在；存在时看 `lease_status`、`lease_expires_at`、`revoked_at`、`revoked_reason` |
| snapshot check points | `active_lease` 是否为 `null`；若非空，`worker_id` / `claim_token` 是否与期望一致 |
| self-check action | 若怀疑 release/expire 逻辑回归，跑 `--check workflow` |
| safe retry? | 不建议在 lease 状态不明时贸然补提 terminal 写入 |
| escalation guidance | 若 lease 长时间残留且不符合预期，升级检查 lease 生命周期与 heartbeat 扩展链路 |

排障判断要点：
- `expire_lease=True` 与 `release_lease()` 不是同一语义
- 先确认期望的是“立即过期”还是“正常释放”

---

## 4.8 症状：latest attempt 的错误信息不完整或不符合预期

| 维度 | 说明 |
|---|---|
| symptom | `error_code` / `error_message` / `error_payload_json` 看起来缺失或与调用方预期不同 |
| probable cause | 请求未传对应字段；`terminal_reason` 与 `error_message` 被不同层用于不同用途；调用方误传空结构；期待“继承 existing payload”却显式传了 `null` |
| first checks | 回看 fail 请求体；确认是否省略了 `error_payload_json` 还是传了空 dict；确认 `terminal_reason` 与 `error_message` 的使用意图 |
| snapshot check points | 看 `latest_attempt.error_code`、`error_message`、`error_payload_json`；看 job 层 `terminal_reason_code` / `terminal_reason_message` |
| self-check action | 一般无需 workflow；如怀疑 schema/export 侧问题可跑 `--check imports` |
| safe retry? | 若 terminal 已成功写入，通常不建议仅为补错误文本而直接重发 |
| escalation guidance | 若错误信息不足以支持排障，升级为调用方失败回写规范治理 |

排障判断要点：
- job 层 reason 字段与 attempt 层 error 字段不是完全同义字段
- `error_payload_json` 若要走“继承 existing payload”语义，应省略字段，不能显式传 `null`

---

## 4.9 症状：self-check 失败，怀疑 runtime terminal 已回归

| 维度 | 说明 |
|---|---|
| symptom | endpoint/workflow/imports 自检项失败 |
| probable cause | 最近改动影响 route contract、schema export、workflow 编排或执行环境；也可能是未激活 `.venv` |
| first checks | 确认在 `/mnt/user-data/workspace/.venv` 中执行；确认命令从仓库根目录发起 |
| snapshot check points | self-check 失败时不一定先看 snapshot；先看失败的是哪一个 check |
| self-check action | 按失败类型重跑：`--check endpoint`、`--check workflow`、`--check imports`；必要时跑默认全量 |
| safe retry? | 可以先定向重跑；但不要在未定位失败种类前宣称服务已损坏 |
| escalation guidance | 若 workflow check 失败且近期触及 service/lease/job 语义，升级为冻结边界破坏风险 |

建议命令：

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check endpoint
```

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check workflow
```

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check imports
```

---

## 5. 快速分流表

| 观察到的现象 | 第一判断 | 第一动作 | 通常归属 |
|---|---|---|---|
| GET 404 | job 不存在 / ID 错误 / 环境错 | 核对 job_id 与环境 | 调用上下文 / 环境问题 |
| POST 409 lease conflict | claim/worker/attempt 不一致 | 对照 snapshot 核 claim | 调用上下文问题 |
| POST 409 state conflict | 已 terminal / 重复提交 | 看 job_status 与 finished_at | 幂等/重复回写问题 |
| POST 422 | payload 不合法 | 看 validator 报错 | 调用请求问题 |
| POST 200 但状态不符预期 | 语义理解错或读取错对象 | 看 job/attempt/lease 三层字段 | 调用理解/排障问题 |
| self-check fail | 回归或执行环境问题 | 先定向跑对应 check | 实现/环境问题 |

---

## 6. 什么时候可以重试，什么时候不要重试

## 6.1 可以优先考虑重试的情况
- 422 已明确是 payload 可修复问题
- 404 已确认只是 job_id 输入错误，且真实 job_id 已找到
- self-check 某项失败但首先发现是 `.venv` / 路径使用错误

## 6.2 不要直接重试的情况
- 409 lease conflict，且尚未确认当前 active lease 归属
- 409 state conflict，且尚未确认 job 是否已经 terminal
- `POST /complete` 或 `POST /fail` 已返回 200，只是调用方“感觉不对”
- lease 生命周期仍不清楚，可能存在并发 writer

## 6.3 更适合人工介入的情况
- job/attempt/lease 三层信息彼此矛盾
- terminal 已写入，但业务方要求“纠正历史终态”
- 同类 conflict 在多个 worker / 多个 job 批量出现
- workflow self-check 失败且近期存在 service 语义修改痕迹

---

## 7. 推荐升级路径

建议按以下层级升级：

### L1：调用方自检
- 核 payload
- 核 `job_id + attempt_id + worker_id + claim_token`
- 核 422/409 body

### L2：operator 快照排障
- 查 `GET /jobs/{job_id}`
- 比对 job / latest attempt / active lease
- 跑定向 self-check

### L3：维护者介入
- 对照 contract pack / orchestration explainer 判断是否属于语义误用
- 判断是否存在冻结边界被破坏的迹象

### L4：实现层排查
- 仅在前面层级无法解释时，才进入代码/实现层
- 且仍需遵守 runtime terminal v1 封板边界

---

## 8. 最小结论

runtime terminal v1 的 operator 排障，优先不是“重新读代码”，而是：
1. 先按错误类型分流
2. 再用 terminal snapshot 拆 job / attempt / lease 三层
3. 最后用 self-check 判断是 contract/环境/编排哪一层出现问题

只要沿着这个矩阵执行，大多数 404 / 409 / 422 / 状态误读问题都能在不破坏 v1 冻结边界的前提下快速定位。