# Runtime terminal language-specific snippets pack v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **language-specific snippets pack**。

它不重新定义 API contract，不改动 complete / fail 的写侧语义，也不替代 caller integration guide / SDK usage snippet pack，而是把 runtime terminal 的最小调用动作拆成几组**不同语言 / 不同调用栈可直接抄用的样例**，方便以下角色快速接入：
- Python 调用方（`requests` / `httpx`）
- Shell / CI / 运维侧（`curl`）
- Node.js / TypeScript 接入方（`fetch`）
- 需要把 terminal 调用嵌入现有 worker / orchestrator / reporter 的平台开发者

本文档与以下材料配套阅读：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_faq_decision_memo_v1.md`
- `runtime_terminal_external_docs_index_v1.md`

本文档严格遵守当前 v1 冻结边界：
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰冻结测试 `tests/test_runtime_terminal_workflow.py`
- 422 继续保持 FastAPI / Pydantic 默认行为

---

## 2. 使用前先记住的 6 条规则

### 2.1 terminal 是终态回写接口，不是调度接口

本包只覆盖：
- `POST /api/v1/runtime/terminal/complete`
- `POST /api/v1/runtime/terminal/fail`
- `GET /api/v1/runtime/terminal/jobs/{job_id}`

不覆盖：
- claim
- heartbeat
- retry 调度
- worker 抢占
- 历史终态修订

### 2.2 四元身份字段必须原样来自同一次真实 attempt

所有语言样例都遵守同一条规则：
- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

这四个字段必须原样透传，不要在 SDK / adapter / helper 里二次补猜、重拼、替换。

### 2.3 409 优先当作状态冲突，不是默认自动重试

所有语言样例都默认：
- 409 -> 先读 snapshot，再做业务判定
- 不做 blind retry
- 不自动换 claim_token 重提
- 不自动把 complete 改成 fail

### 2.4 422 优先当作 payload 构造错误

所有语言样例都保留 FastAPI / Pydantic 默认 422。

因此：
- 字段缺失
- 类型不匹配
- 枚举值非法
- 结构不符合 schema

都应优先回到 caller / SDK 自己修 payload，而不是要求 terminal 再包一层自定义错误结构。

### 2.5 complete / fail 成功后，关键链路建议补一次 snapshot 核验

推荐读取：

```text
GET /api/v1/runtime/terminal/jobs/{job_id}
```

重点看：
- `job_status`
- `finished_at`
- `latest_attempt.attempt_status`
- `latest_attempt.completion_status`
- `latest_attempt.result_ref`
- `latest_attempt.error_code`
- `latest_attempt.error_message`
- `active_lease`

### 2.6 `completion_status` 不是 `job_status`

在各语言样例里都要分清：
- `completion_status`：attempt 成功完成标签
- `next_job_status`：job 下一步走向
- `attempt_terminal_status`：attempt 如何失败类收口
- `job_status`：snapshot 中 job 当前状态

这些字段不是一个维度，不能混用。

---

## 3. Base URL 与路径约定

Base prefix：

```text
/api/v1/runtime/terminal
```

3 个 endpoint：

```text
POST /api/v1/runtime/terminal/complete
POST /api/v1/runtime/terminal/fail
GET  /api/v1/runtime/terminal/jobs/{job_id}
```

以下样例统一假设：
- 服务根地址：`http://localhost:8000`
- terminal base：`http://localhost:8000/api/v1/runtime/terminal`

生产环境中请替换为真实域名或网关地址。

---

## 4. 通用 payload 模板

## 4.1 complete 最小 payload

```json
{
  "job_id": "job-123",
  "attempt_id": "attempt-5",
  "worker_id": "worker-a",
  "claim_token": "claim-xyz",
  "completion_status": "SUCCEEDED",
  "result_ref": "minio://bucket/path/output.mp4",
  "manifest_artifact_id": "manifest-123",
  "runtime_ms": 31000,
  "provider_runtime_ms": 27000,
  "upload_ms": 1800,
  "metadata_json": {
    "source": "veo_pipeline",
    "creative_id": "creative-88"
  }
}
```

## 4.2 fail 最小 payload

```json
{
  "job_id": "job-123",
  "attempt_id": "attempt-5",
  "worker_id": "worker-a",
  "claim_token": "claim-xyz",
  "next_job_status": "WAITING_RETRY",
  "attempt_terminal_status": "TIMED_OUT",
  "terminal_reason": "provider_timeout",
  "error_code": "PROVIDER_TIMEOUT",
  "error_message": "provider call exceeded timeout budget",
  "error_payload_json": {
    "provider": "veo",
    "timeout_s": 120,
    "phase": "render"
  },
  "expire_lease": true,
  "metadata_json": {
    "source": "veo_pipeline"
  }
}
```

## 4.3 fail 字段边界提醒

- `next_job_status` 仅允许：`FAILED` / `WAITING_RETRY` / `STALE`
- `attempt_terminal_status` 仅允许：`FAILED` / `TIMED_OUT` / `STALE`
- `error_payload_json` 不要显式传 `null`
- `expire_lease` 不能固定写死，应按真实业务语义选择

---

## 5. Python `requests` 样例

## 5.1 complete

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"

payload = {
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "completion_status": "SUCCEEDED",
    "result_ref": "minio://video-results/job-123/final.mp4",
    "manifest_artifact_id": "manifest-123",
    "runtime_ms": 31_000,
    "provider_runtime_ms": 27_000,
    "upload_ms": 1_800,
    "metadata_json": {
        "provider": "veo",
        "pipeline": "beauty_replication_v1",
    },
}

response = requests.post(
    f"{BASE_URL}/complete",
    json=payload,
    timeout=10,
)

if response.status_code == 200:
    print(response.json())
elif response.status_code == 409:
    raise RuntimeError("terminal conflict: read snapshot before next action")
elif response.status_code == 422:
    raise ValueError(response.text)
else:
    response.raise_for_status()
```

## 5.2 fail

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"

payload = {
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "next_job_status": "WAITING_RETRY",
    "attempt_terminal_status": "TIMED_OUT",
    "terminal_reason": "provider_timeout",
    "error_code": "PROVIDER_TIMEOUT",
    "error_message": "provider call exceeded timeout budget",
    "error_payload_json": {
        "provider": "veo",
        "timeout_s": 120,
        "phase": "render",
    },
    "expire_lease": true,
    "metadata_json": {
        "retry_planned": true,
    },
}

response = requests.post(
    f"{BASE_URL}/fail",
    json=payload,
    timeout=10,
)

if response.status_code == 200:
    print(response.json())
elif response.status_code == 409:
    raise RuntimeError("terminal conflict: do not blindly retry")
elif response.status_code == 422:
    raise ValueError(response.text)
else:
    response.raise_for_status()
```

## 5.3 snapshot

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"
job_id = "job-123"

response = requests.get(
    f"{BASE_URL}/jobs/{job_id}",
    timeout=10,
)
response.raise_for_status()

snapshot = response.json()
print(snapshot["job_status"])
print(snapshot.get("latest_attempt"))
print(snapshot.get("active_lease"))
```

## 5.4 `requests` 版本的接入提醒

适合场景：
- 现有 Python worker 已在用 `requests`
- 快速写最小 reporter / sidecar adapter
- 不需要 async I/O

不要在这里偷偷做：
- 自动重试 409
- 自动补猜四元身份字段
- 自动吞掉 422 并改成模糊异常

---

## 6. Python `httpx` 样例

## 6.1 同步版 complete

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"

payload = {
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "completion_status": "SUCCEEDED",
    "result_ref": "minio://video-results/job-123/final.mp4",
    "manifest_artifact_id": "manifest-123",
    "runtime_ms": 31_000,
    "provider_runtime_ms": 27_000,
    "upload_ms": 1_800,
    "metadata_json": {"provider": "veo"},
}

with httpx.Client(timeout=10.0) as client:
    response = client.post(f"{BASE_URL}/complete", json=payload)

if response.status_code == 200:
    print(response.json())
elif response.status_code == 409:
    raise RuntimeError("terminal conflict")
elif response.status_code == 422:
    raise ValueError(response.text)
else:
    response.raise_for_status()
```

## 6.2 异步版 fail

```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"

payload = {
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "next_job_status": "FAILED",
    "attempt_terminal_status": "FAILED",
    "terminal_reason": "provider_rejected_request",
    "error_code": "BAD_PROVIDER_INPUT",
    "error_message": "Provider rejected request payload.",
    "error_payload_json": {
        "provider": "veo",
        "provider_error_code": "INVALID_PROMPT",
    },
    "expire_lease": false,
    "metadata_json": {"requires_manual_fix": true},
}

async def main() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{BASE_URL}/fail", json=payload)

    if response.status_code == 200:
        print(response.json())
    elif response.status_code == 409:
        raise RuntimeError("terminal conflict")
    elif response.status_code == 422:
        raise ValueError(response.text)
    else:
        response.raise_for_status()

asyncio.run(main())
```

## 6.3 异步版 snapshot

```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1/runtime/terminal"
job_id = "job-123"

async def main() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{BASE_URL}/jobs/{job_id}")
        response.raise_for_status()
        snapshot = response.json()

    print(snapshot["job_status"])
    print(snapshot.get("latest_attempt"))
    print(snapshot.get("active_lease"))

asyncio.run(main())
```

## 6.4 `httpx` 版本的接入提醒

适合场景：
- async worker / orchestrator
- FastAPI 内部调用其他 runtime 服务
- 需要统一 sync / async 风格的 Python adapter

仍然不要做：
- 409 自动重放
- 自行替换 claim_token
- 从缓存回填一个“看起来像能用”的 attempt_id

---

## 7. Shell / `curl` 样例

## 7.1 complete

```bash
curl -sS -X POST "http://localhost:8000/api/v1/runtime/terminal/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "completion_status": "SUCCEEDED",
    "result_ref": "minio://video-results/job-123/final.mp4",
    "manifest_artifact_id": "manifest-123",
    "runtime_ms": 31000,
    "provider_runtime_ms": 27000,
    "upload_ms": 1800,
    "metadata_json": {
      "provider": "veo",
      "pipeline": "beauty_replication_v1"
    }
  }'
```

## 7.2 fail

```bash
curl -sS -X POST "http://localhost:8000/api/v1/runtime/terminal/fail" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "attempt_id": "attempt-5",
    "worker_id": "worker-a",
    "claim_token": "claim-xyz",
    "next_job_status": "WAITING_RETRY",
    "attempt_terminal_status": "TIMED_OUT",
    "terminal_reason": "provider_timeout",
    "error_code": "PROVIDER_TIMEOUT",
    "error_message": "provider call exceeded timeout budget",
    "error_payload_json": {
      "provider": "veo",
      "timeout_s": 120,
      "phase": "render"
    },
    "expire_lease": true,
    "metadata_json": {
      "retry_planned": true
    }
  }'
```

## 7.3 snapshot

```bash
curl -sS "http://localhost:8000/api/v1/runtime/terminal/jobs/job-123"
```

## 7.4 `curl` 版本的接入提醒

适合场景：
- operator 现场排障
- CI smoke test
- 文档示例 / Postman 前的快速验证
- shell wrapper / sidecar reporter

特别注意：
- shell 中最容易手抖输错四元字段
- 不要为了排错手工换 claim_token 硬提请求
- `error_payload_json` 没有内容时，直接删字段，不要写成 `null`

---

## 8. TypeScript 样例

以下示例使用平台原生 `fetch` 风格，适用于 Node.js 18+ 或带 fetch polyfill 的环境。

## 8.1 类型定义

```ts
type RuntimeAttemptContext = {
  job_id: string;
  attempt_id: string;
  worker_id: string;
  claim_token: string;
};

type CompletePayload = RuntimeAttemptContext & {
  completion_status: "SUCCEEDED";
  result_ref: string;
  manifest_artifact_id?: string | null;
  runtime_ms?: number;
  provider_runtime_ms?: number;
  upload_ms?: number;
  metadata_json?: Record<string, unknown>;
};

type FailPayload = RuntimeAttemptContext & {
  next_job_status: "FAILED" | "WAITING_RETRY" | "STALE";
  attempt_terminal_status: "FAILED" | "TIMED_OUT" | "STALE";
  terminal_reason: string;
  error_code: string;
  error_message: string;
  error_payload_json?: Record<string, unknown>;
  expire_lease: boolean;
  metadata_json?: Record<string, unknown>;
};
```

## 8.2 最小 request helper

```ts
const BASE_URL = "http://localhost:8000/api/v1/runtime/terminal";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 404) {
    throw new Error(`not found: ${await response.text()}`);
  }
  if (response.status === 409) {
    throw new Error(`terminal conflict: ${await response.text()}`);
  }
  if (response.status === 422) {
    throw new Error(`validation error: ${await response.text()}`);
  }
  if (!response.ok) {
    throw new Error(`http error ${response.status}: ${await response.text()}`);
  }

  return response.json() as Promise<T>;
}
```

## 8.3 complete

```ts
async function completeJob(payload: CompletePayload) {
  return request("/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

const completePayload: CompletePayload = {
  job_id: "job-123",
  attempt_id: "attempt-5",
  worker_id: "worker-a",
  claim_token: "claim-xyz",
  completion_status: "SUCCEEDED",
  result_ref: "minio://video-results/job-123/final.mp4",
  manifest_artifact_id: "manifest-123",
  runtime_ms: 31000,
  provider_runtime_ms: 27000,
  upload_ms: 1800,
  metadata_json: {
    provider: "veo",
    pipeline: "beauty_replication_v1",
  },
};

await completeJob(completePayload);
```

## 8.4 fail

```ts
async function failJob(payload: FailPayload) {
  return request("/fail", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

const failPayload: FailPayload = {
  job_id: "job-123",
  attempt_id: "attempt-5",
  worker_id: "worker-a",
  claim_token: "claim-xyz",
  next_job_status: "WAITING_RETRY",
  attempt_terminal_status: "TIMED_OUT",
  terminal_reason: "provider_timeout",
  error_code: "PROVIDER_TIMEOUT",
  error_message: "provider call exceeded timeout budget",
  error_payload_json: {
    provider: "veo",
    timeout_s: 120,
    phase: "render",
  },
  expire_lease: true,
  metadata_json: {
    retry_planned: true,
  },
};

await failJob(failPayload);
```

## 8.5 snapshot

```ts
async function getJobSnapshot(jobId: string) {
  return request(`/jobs/${jobId}`, {
    method: "GET",
  });
}

const snapshot = await getJobSnapshot("job-123");
console.log(snapshot);
```

## 8.6 TypeScript 版本的接入提醒

适合场景：
- Node.js orchestrator
- BFF / gateway 辅助调用
- 内部平台 SDK
- workflow engine adapter

特别注意：
- 类型约束只能减少低级错误，不能替代真实上下文一致性
- 即使 TS 编译通过，也不代表 claim_token / attempt_id 一定来自同一次真实 attempt
- 仍然不要自动重试 409

---

## 9. 成功后建议统一补的 snapshot 核验模板

不论你用哪一种语言，关键链路建议都统一成：

1. 先记录 complete / fail 的 200 返回
2. 立刻读取 `GET /jobs/{job_id}`
3. 至少核验以下 3 层：
   - job 层：`job_status`、`finished_at`
   - latest attempt 层：成功看 `completion_status` / `result_ref`；失败看 `error_code` / `error_message`
   - lease 层：`active_lease` 是否已按预期释放或过期
4. 核验无误后，清理本地 attempt 上下文
5. 不再对同一 attempt 重复提交终态

---

## 10. 各语言统一的不要做清单

以下动作在所有语言样例中都不建议做：

- 自动重试 409
- 自动补猜 `job_id / attempt_id / worker_id / claim_token`
- 自动替换 `claim_token`
- 自动把 complete 改成 fail
- 自动把 fail 改成 complete
- 把 422 吞掉后包装成模糊异常
- 对同一 attempt 成功收口后再次补提另一种终态

这些动作看似“更智能”，实则会把真实冲突和上下文错配隐藏掉。

---

## 11. 推荐与现有文档包的衔接方式

建议对外阅读顺序：

1. `runtime_terminal_external_docs_index_v1.md`
2. `runtime_terminal_package_index_v1.md`
3. `runtime_terminal_caller_integration_guide_v1.md`
4. `runtime_terminal_sdk_usage_snippet_pack_v1.md`
5. `runtime_terminal_language_specific_snippets_pack_v1.md`
6. `runtime_terminal_faq_decision_memo_v1.md`
7. `runtime_terminal_operator_troubleshooting_matrix_v1.md`
8. `runtime_terminal_self_check_runbook.md`

这样分层最清楚：
- integration guide 解释“该怎么接”
- SDK pack 解释“推荐怎样封装”
- language-specific pack 提供“按语言直接抄用的最小样例”
- FAQ memo 解释“为什么这样冻结”

---

## 12. 默认结论

runtime terminal v1 的 language-specific snippets pack 只服务一个目标：

**让不同语言、不同调用栈的 caller 能在不突破 v1 冻结边界的前提下，稳定、直接、低歧义地完成 complete / fail / snapshot 三个动作。**

如果后续要继续扩展，更自然的下一层不是重改 terminal 语义，而是补：
- language-specific error mapping appendix
- caller FAQ / operator FAQ 拆分版
- TypeScript / Python 最小 SDK package scaffold
