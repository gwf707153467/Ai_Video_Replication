# Runtime terminal SDK regression slice note v1

## 1. 文档定位

本文档只固定一个很小的 caller-side SDK 回归入口，避免后续仓内改动时把 runtime terminal SDK 的最小测试切片弄丢。

它不重开 API contract，不扩展 SDK 范围，也不替代以下既有文档：
- `runtime_terminal_sdk_formal_readme_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`

---

## 2. 标准回归命令

在当前仓库中，runtime terminal caller-side SDK 的标准最小回归入口固定为：

```bash
source /mnt/user-data/workspace/.venv/bin/activate && \
cd /mnt/user-data/workspace/Ai_Videos_Replication && \
python -m unittest discover -s tests -p 'test_runtime_terminal_sdk*.py'
```

最近一次已验证结果：
- `Ran 16 tests in 0.004s`
- `OK`

---

## 3. 这个切片在保护什么

该回归切片当前由两部分组成：
- `tests/test_runtime_terminal_sdk_client.py`
- `tests/test_runtime_terminal_sdk_exports.py`

合计 16 个测试，主要锁定三类内容。

### 3.1 caller-side 行为边界
- `complete_job(...)` / `fail_job(...)` / `get_job_snapshot(...)` 成功路径
- 固定 terminal 路径：
  - `/api/v1/runtime/terminal/complete`
  - `/api/v1/runtime/terminal/fail`
  - `/api/v1/runtime/terminal/jobs/{job_id}`
- `base_url.rstrip("/")`
- strict passthrough：`metadata_json=None` / `error_payload_json=None` 原样透传

### 3.2 错误映射边界
- `404 -> RuntimeTerminalNotFoundError`
- `409 -> RuntimeTerminalConflictError`
- `422 -> RuntimeTerminalValidationError`
- `5xx -> RuntimeTerminalServerError`
- other `4xx -> RuntimeTerminalError`
- `httpx.HTTPError -> RuntimeTerminalTransportError`
- success but non-JSON -> `RuntimeTerminalServerError`

### 3.3 package public surface 边界
- `app.runtime_terminal_sdk.__all__`
- package-level imports
- `RuntimeAttemptContext` 最小四元构造顺序
- `RuntimeTerminalClient` 最小构造参数面
- `RuntimeTerminalClient` 最小公开方法集
- minimal exception tree 的 package-visible 继承关系

---

## 4. 明确不要碰的范围

当目标只是保持 caller-side SDK regression slice 稳定时，不应借此回归入口顺手扩展范围到以下方向：
- claim client
- heartbeat manager
- retry orchestration
- scheduler entrypoint
- business-state arbitration
- payload auto-repair
- automatic `claim_token` replacement

同时，本回归 note 也不要求改动以下主线或冻结文件：
- 仓库根 `README.md`
- `pyproject.toml`
- `tests/test_runtime_terminal_workflow.py`
- 服务端主线契约文件

---

## 5. 使用建议

后续只要出现以下任一情况，建议优先执行本切片：
- 修改 `app/runtime_terminal_sdk/` 下任意文件
- 调整 package export surface
- 调整 caller-side error mapping
- 调整 complete / fail payload 构造逻辑
- 调整 README / handoff 文案后需要确认没有诱导越界实现

如果这个 16-test 切片不通过，应先恢复 caller-side SDK 最小边界，再决定是否需要扩大测试范围。

---

## 6. 当前结论

截至本 note 生成时，runtime terminal SDK 的 caller-side contract 已具备一个可重复执行、范围清晰、与服务端主线解耦的最小回归切片，可作为后续增量改动的标准 smoke/regression baseline。
