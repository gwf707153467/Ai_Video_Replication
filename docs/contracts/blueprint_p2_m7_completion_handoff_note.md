# Blueprint P2-M7 Completion Handoff Note

## 1. 文档定位

本文档是 `P2-M7 Blueprint fixture evolution policy / contract change discipline` 的 completion handoff / continuity artifact。

它服务于一个非常窄的目的：

> 在不扩展 Blueprint 运行能力、不触碰 baseline 与 runtime 主链路的前提下，把 P2-M7 已完成范围、冻结结论、验收结果、后续连续推进规则固定下来，便于后续窗口直接续接。

本文档不重开以下议题：

- baseline gate 逻辑、边界、判定语义
- DB / persistence / dispatch / ingest / provider runtime 集成
- Blueprint 新 endpoint
- `blueprint.v0` breaking semantic change
- P2-M1 ~ P2-M6 已接受结论

---

## 2. P2-M7 要解决的问题

P2-M6 已经冻结了 Blueprint schema / compiler stub / API surface / artifact access / self-check 的最小一致性护栏，但仍缺少一层更明确的 **fixture 演进纪律** 与 **contract 变更联动纪律**。

P2-M7 的目标不是新增能力，而是补齐以下 repo-level guardrails：

1. canonical fixture 不是可随意编辑的示例文件，而是 contract-bearing example
2. contract 文档变更不能脱离 tests 与 self-check 单独漂移
3. public surface 若发生 breaking semantic change，必须通过 versioned surface 承载，而不是静默改写当前 `blueprint.v0`

一句话概括：

> P2-M7 的作用是把“Blueprint 相关内容如何被修改”也纳入 Blueprint contract 本身。

---

## 3. 本次完成范围

P2-M7 已完成且已验收通过的范围仅包括：

### 3.1 Fixture evolution policy

已明确 canonical fixture 为：

- `docs/examples/beauty_cosmetics_blueprint_v0.json`

并冻结以下纪律：

- `fixture_change_requires_contract_review`
- 任何影响 request / response 示例、compile-preview 预期、sequence 顺序或关键字段语义的改动，都必须同步检查并更新：
  - `docs/contracts/blueprint_v0_contract.md`
  - `docs/contracts/blueprint_api_contract.md`
  - tests
  - `scripts/blueprint_self_check.py`

### 3.2 Contract change discipline

已冻结以下纪律：

- `contract_change_requires_guardrail_updates`
- 若改动以下公共面之一，必须在同一提交中同步更新 docs / tests / self-check：
  - `app.blueprint_sdk.__all__`
  - artifact index keys
  - route path
  - response model
  - 关键 validator message
  - compile-preview 冻结示例预期

### 3.3 Breaking semantic discipline

已冻结以下规则：

- `breaking_fixture_semantics_require_versioned_surface`
- 若 Blueprint 或 API contract 发生 breaking semantic change，应通过新的 versioned surface / milestone 承载，而不是静默修改当前：
  - `blueprint.v0`
  - `/api/v1/blueprints/validate`
  - `/api/v1/blueprints/compile-preview`

### 3.4 Read-only consistency entrypoint hardening

`scripts/blueprint_self_check.py` 已补充 P2-M7 marker 校验，继续保持：

- 只读
- repo-local
- 零副作用
- 不访问 DB / Redis / MinIO
- 不触发 dispatch / persistence / baseline 逻辑

---

## 4. 已冻结的 P2-M7 落地产物

### 4.1 Contract docs

以下 contract 文档已成为 P2-M7 authoritative doc surface：

- `docs/contracts/blueprint_v0_contract.md`
- `docs/contracts/blueprint_api_contract.md`

其中必须持续保留的关键 marker 包括：

#### `blueprint_v0_contract.md`

- `# Blueprint v0 Contract`
- `bridge_requires_spu_or_vbu_binding`
- `reference_beat_sequence_missing:<beat_code>:<sequence_code>`
- `## 11. Self-check 范围`
- `### 11.1 Fixture evolution policy`
- `fixture_change_requires_contract_review`
- `### 11.2 Contract change discipline`
- `contract_change_requires_guardrail_updates`
- `breaking_fixture_semantics_require_versioned_surface`
- `## 12. 非目标与边界`

#### `blueprint_api_contract.md`

- `## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline`
- `fixture_change_requires_contract_review`
- `contract_change_requires_guardrail_updates`
- `breaking_fixture_semantics_require_versioned_surface`
- `## 12. 相关实现位置`
- `## 13. 非目标`

### 4.2 Self-check

`scripts/blueprint_self_check.py` 当前已冻结以下 P2-M7 相关断言：

- API contract 文件存在
- artifact index keys 精确匹配：
  - `example_payload`
  - `contract_doc`
  - `json_schema`
- example / contract / schema 路径与文件名保持冻结
- example payload 的 Blueprint version / id / runtime_version / compile_reason 保持冻结
- validated sequence order 保持 `hook, problem, demo, cta`
- contract markers 与 API contract markers 全部存在

### 4.3 Tests

本轮 P2-M7 相关测试冻结点主要位于：

- `tests/test_blueprint_sdk_artifacts.py`
- `tests/test_blueprint_contract.py`

并与既有 acceptance slice 共同构成 Blueprint line acceptance：

- `tests/test_blueprint_sdk_exports.py`
- `tests/test_blueprint_sdk_artifacts.py`
- `tests/test_blueprint_contract.py`
- `tests/test_blueprint_api_endpoints.py`

---

## 5. 当前 authoritative frozen state

### 5.1 Baseline thread

Phase 1 baseline gate 已完成并冻结；P2-M7 不得重开 baseline 工作。

authoritative PASS 仍为：

- project: `656ac6b1-ecb8-4f45-9f45-556be5915168`
- verdict file: `baseline_gate_verdict.json`
- runtime_id: `1d46d527-d090-433c-bcc7-05424e21cc0b`
- runtime_version: `v9`
- JSON verdict 仍为唯一权威结果

### 5.2 Blueprint line

P2-M1 ~ P2-M6 继续视为已完成、已接受、不可重开，除非用户显式要求。

P2-M7 完成后，Blueprint 当前工作面仍严格限定为：

- contract / fixture / schema / example / SDK export / self-check / narrow API contract consistency

明确不进入：

- DB persistence
- migration
- dispatch
- ingest parsing
- upload parsing
- provider integration
- runtime execution expansion
- 新 endpoint

### 5.3 Canonical fixture / compile preview invariants

以下结论继续冻结：

- example fixture: `docs/examples/beauty_cosmetics_blueprint_v0.json`
- `blueprint_version = "blueprint.v0"`
- `blueprint_id = "beauty-lip-plumper-demo"`
- requested runtime version: `beauty-lip-plumper-demo.v0`
- `compile_reason = "blueprint_stub"`
- `aspect_ratio = "9:16"`
- sequence order: `hook -> problem -> demo -> cta`
- counts: `4 sequences / 4 SPUs / 4 VBUs / 4 bridges / 4 reference beats`

---

## 6. P2-M7 验收结果

authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果

本轮 authoritative acceptance 已通过：

### 6.1 unittest acceptance

authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance
authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints

命令：

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && \
/mnt/user-data/workspace/.venv/bin/python -m unittest \
  tests.test_blueprint_sdk_exports \
  tests.test_blueprint_sdk_artifacts \
  tests.test_blueprint_contract \
  tests.test_blueprint_api_endpoints
```

结果：

- `Ran 28 tests in 0.121s`
- `OK`

authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s
authoritative_acceptance_unittest_ok:OK

### 6.2 self-check acceptance

authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance
authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py

命令：

```bash
cd /mnt/user-data/workspace/Ai_Videos_Replication && \
/mnt/user-data/workspace/.venv/bin/python scripts/blueprint_self_check.py
```

结果：

- `blueprint self-check ok`

authoritative_acceptance_self_check_result:blueprint self-check ok

并打印冻结摘要：

- `blueprint_id=beauty-lip-plumper-demo`
- `runtime_version=beauty-lip-plumper-demo.v0`
- `sequence_count=4`
- `visual_track_count=4`
- `audio_track_count=4`
- `bridge_count=4`
- `artifact_index_keys=['contract_doc', 'example_payload', 'json_schema']`

### 6.3 Inventory section-anchor hardening completion

- section_anchor_hardening_completion_status:completed
- section_anchor_hardening_completion_scope:docs/tests/self-check_only
- section_anchor_hardening_inventory_entrypoint:docs/contracts/blueprint_contract_inventory.md
- section_anchor_hardening_inventory_role:authoritative_navigation_entrypoint_for_key_section_and_boundary_anchors
- section_anchor_hardening_guardrail_surfaces:tests/test_blueprint_contract.py,scripts/blueprint_self_check.py
- section_anchor_hardening_no_runtime_surface_change
- section_anchor_hardening_no_baseline_reopen

这一步不是新增 Blueprint capability，而是把 `docs/contracts/blueprint_contract_inventory.md` 从文档级 hub 进一步固定为 frozen contract docs 的关键 section / boundary anchor 导航入口，并要求 tests 与 self-check 同步把这层定位视为 guardrail。

---

## 7. 后续窗口的连续推进规则

如果后续窗口继续沿 Blueprint 方向推进，必须遵守以下规则：

1. 不重复确认已冻结方向；直接基于当前 frozen state 续做最小包
2. 若仅做文档 / self-check / tests / SDK export consistency 强化，应保持只读、零副作用、repo-local
3. 若提议修改 canonical fixture、route surface、schema 关键语义、compile-preview 预期，必须先判断是否已触发：
   - `fixture_change_requires_contract_review`
   - `contract_change_requires_guardrail_updates`
   - `breaking_fixture_semantics_require_versioned_surface`
4. 不得借 P2-M7 后续工作把范围扩展到 DB / dispatch / ingest / provider runtime 集成
5. 继续优先使用 `/mnt/user-data/workspace/.venv/bin/python` 运行本仓测试与脚本

---

## 8. 对下一最小包的建议

P2-M7 完成后，下一步应优先选择仍然满足以下条件的最小包：

- schema-first
- read-only
- zero side effects
- contract-strengthening
- 不扩大运行能力

推荐方向应优先落在以下类型之一：

1. 新增更窄的 Blueprint continuity / governance artifact
2. 对 Blueprint public surface 增加更严格但非 breaking 的 acceptance guardrail
3. 对现有 contract / fixture / self-check / exports 之间的联动关系做更细颗粒冻结

不建议立即进入：

- Blueprint persistence
- provider execution wiring
- dispatch integration
- baseline 相关再加工

---

## 9. 交接结论

P2-M7 已完成。

它没有新增运行能力，也没有改变 Blueprint v0 / compile-preview / baseline 的既有边界；它做的是把 fixture 演进纪律与 contract 联动纪律正式写入 contract docs、tests 与 self-check，使 Blueprint 线从“有最小能力”进一步提升为“有最小治理护栏”。

对后续窗口而言，这份 note 的核心价值不是描述代码细节，而是固定一句话：

> 从 P2-M7 开始，Blueprint 的 example、contract、SDK export、API doc 与 self-check 必须被视为一个协同演进的冻结面，而不是可以各自独立漂移的零散文件。

### 9.1 只读交叉引用定位

- governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md
- contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- 本 handoff note 的职责是固定 P2-M7 的完成结论、authoritative acceptance 与后续连续推进规则
- frozen surface matrix 的职责是固定 Blueprint line 的 frozen public surface、guardrail 联动关系与显式 contract review 纪律
- 两者都属于 read-only / repo-local / zero-side-effect 文档面，但不应互相替代
- 若后续窗口继续推进 Blueprint governance，应同时检查这两份文档是否仍保持职责边界清晰且 marker 同步
