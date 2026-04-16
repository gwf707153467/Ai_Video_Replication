# Runtime terminal self-check runbook v2

## 1. 目的

该 runbook 用于固化 `Runtime terminal workflow / service 编排最小实现包 v1` 的 smoke/self-check 动作，并在 P3 增补可选 check 组合能力，让维护者既能一条命令跑完整最小回归，也能按需只跑局部检查。

默认目标仍然是：
- endpoint contract suite
- frozen workflow suite
- import self-check
- caller-side SDK regression slice

---

## 2. 脚本文件

- `scripts/runtime_terminal_self_check.py`
- `scripts/run_runtime_terminal_self_check.sh`

---

## 3. 可用检查项

脚本当前支持以下 check key：

- `endpoint`
  - 对应结果名：`endpoint_suite`
  - 对应测试：`tests/test_runtime_terminal_endpoints.py`
- `workflow`
  - 对应结果名：`workflow_suite`
  - 对应测试：`tests/test_runtime_terminal_workflow.py`
- `imports`
  - 对应结果名：`import_self_check`
  - 对应模块：
    - `app.schemas.runtime`
    - `app.schemas`
    - `app.services.runtime_terminal_facade`
    - `app.api.v1.routes.runtime_terminal`
- `sdk`
  - 对应结果名：`sdk_regression_suite`
  - 对应测试：`test_runtime_terminal_sdk*.py`
  - 语义：执行 caller-side runtime terminal SDK regression slice
- `all`
  - 语义：执行 `endpoint + workflow + imports + sdk`

默认不传 `--check` 时，等价于执行 `all`。

---

## 4. 推荐执行方式

### 4.1 跑完整最小回归

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh
```

该 wrapper 会：
- 切到固定仓库目录
- 激活 `/mnt/user-data/workspace/.venv`
- 调用 `python scripts/runtime_terminal_self_check.py`

### 4.2 只跑 endpoint

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check endpoint
```

### 4.3 只跑 workflow + imports + sdk

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check workflow --check imports --check sdk
```

### 4.4 用逗号方式组合

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --check endpoint,imports,sdk
```

### 4.5 查看可用检查项

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --list-checks
```

---

## 5. 直接执行方式

### 5.1 直接执行完整检查

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && source /mnt/user-data/workspace/.venv/bin/activate && python scripts/runtime_terminal_self_check.py
```

### 5.2 直接执行局部检查

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && source /mnt/user-data/workspace/.venv/bin/activate && python scripts/runtime_terminal_self_check.py --check imports
```

### 5.3 直接执行 caller-side SDK regression slice

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && source /mnt/user-data/workspace/.venv/bin/activate && python scripts/runtime_terminal_self_check.py --check sdk
```

---

## 6. 输出物

默认会写出 JSON 报告：

```text
/mnt/user-data/workspace/Ai_Videos_Replication/tmp_runtime_terminal_self_check.json
```

报告内容包括：
- 执行时间
- 使用的 python bin
- `report_version`
- `selected_checks`
- `selected_result_names`
- overall status
- 每个检查项的命令、返回码、stdout、stderr、耗时

对 JSON 消费方，建议把以下字段视为稳定识别键：
- 顶层 `selected_checks`
- 顶层 `selected_result_names`
- `checks[].name`

其中当选择 `sdk` 时：
- `selected_result_names` 中应出现 `sdk_regression_suite`
- `checks[]` 中应存在 `name = "sdk_regression_suite"` 的结果项

不建议通过解析 unittest 原始 stdout / stderr 来推断是否执行了 caller-side SDK regression slice；应优先依赖上述结构化字段。

`tmp_runtime_terminal_self_check.json` 只是默认落盘位置，不应被当作固定示例文件；如果该文件较早生成，内容可能落后于当前脚本版本，应以脚本当前输出为准。

如不希望落盘 JSON，可使用：

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --skip-json
```

如需指定输出路径，可使用：

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && bash scripts/run_runtime_terminal_self_check.sh --output-json /mnt/user-data/workspace/Ai_Videos_Replication/tmp_runtime_terminal_self_check.custom.json
```

---

## 7. 判定标准

- 所有已选择检查项均为 `passed` → overall status = `passed`
- 任一已选择检查项失败 → overall status = `failed`
- 脚本退出码：
  - `0` = passed
  - `1` = failed
  - `2` = 参数错误（如传入不支持的 `--check` 值）

---

## 8. Frozen 边界

本脚本包只做最小回归固化与局部组合增强，不引入以下变化：
- 不修改 `tests/test_runtime_terminal_workflow.py`
- 不修改 complete/fail 写侧语义
- 不新增 repository 写侧直连路径
- 不改变 422 validator error 默认行为

---

## 9. 建议使用场景

建议在以下时机执行：
- runtime terminal route / facade 改动后，先跑 `--check endpoint`
- terminal schema / import surface 改动后，先跑 `--check imports`
- caller-side SDK client / models / exports 改动后，先跑 `--check sdk`
- 交接前或 merge 前，跑完整默认回归
- 只想验证 frozen 行为是否保持时，跑 `--check workflow`
