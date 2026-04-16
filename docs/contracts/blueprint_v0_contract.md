# Blueprint v0 Contract

## 1. 文档目的

本文件定义 `P2-M1 Blueprint` 最小包的冻结契约，用于把“参考带货视频的结构化复刻意图”表达为可校验、可序列化、可最小编译的 Blueprint 文档。

本 contract 仅覆盖当前仓库已落地的最小能力：

- Blueprint constitution
- Pydantic schema v0
- field-level 语义说明
- Reference -> Blueprint 映射规范
- Blueprint -> Runtime compile 映射
- beauty/cosmetics 示例
- JSON schema 导出
- minimal compiler stub 与最小自检

本 contract **不**扩展到以下范围：

- 完整视频解析/镜头检测
- DB migration
- Blueprint 持久化表结构
- ingest pipeline
- 生产级 dispatch 集成改造
- baseline gate 逻辑变更

---

## 2. 设计定位

Blueprint v0 的定位是：

> 在不改动既有 DB compile 主链路与 baseline 语义的前提下，提供一个“脱离数据库也能表达参考创意结构、并能最小编译成 `RuntimePacket`”的中间契约。

它面向两个动作：

1. **结构表达**：把参考视频的骨架、保留元素、可替换轴、sequence / spu / vbu / bridge 编排成一个单文件 JSON 文档。
2. **最小编译**：把 Blueprint 直接编译成当前仓库可识别的 `RuntimePacket` 形状，供后续更完整的 ingest / compile 线路复用。

---

## 3. Constitution

Blueprint v0 遵循以下冻结原则：

1. **Schema-first**：以 `app/schemas/blueprint.py` 为权威结构定义。
2. **Extra forbidden**：所有 Blueprint 模型均 `extra="forbid"`，避免隐式漂移。
3. **Single-file portability**：一个 Blueprint 文档应可单独校验与编译，不依赖数据库查询。
4. **Reference-aware**：Blueprint 必须显式记录参考来源、保留轴、可替换轴与 reference beats。
5. **Compile-compatible**：编译结果必须映射到当前 `RuntimePacket` 结构，而非发明新 runtime shape。
6. **Deterministic identity**：compiler stub 对 project / sequence / spu / vbu / bridge 采用稳定 UUID 映射，保证相同 blueprint 输入得到相同标识。
7. **Minimal but useful**：只表达当前最小包所需字段，不提前引入 production-only 复杂度。
8. **No baseline impact**：Blueprint 最小包不得修改 baseline gate 逻辑、边界或判定语义。

---

## 4. 顶层结构

Blueprint v0 根对象为 `BlueprintV0`，固定：

```json
{
  "blueprint_version": "blueprint.v0",
  "blueprint_id": "beauty-lip-plumper-demo",
  "project": {"name": "..."},
  "reference": {"structural_goal": "..."},
  "global_constraints": {},
  "compile_preferences": {},
  "sequences": []
}
```

字段说明：

- `blueprint_version`：当前固定值 `blueprint.v0`
- `blueprint_id`：Blueprint 的稳定业务标识；参与 deterministic UUID 计算
- `project`：目标项目语义
- `reference`：参考创意来源与结构保留/改写规则
- `global_constraints`：全局比例、时长、风格、禁用元素
- `compile_preferences`：最小编译偏好
- `sequences`：按 sequence 粒度组织的主内容骨架

---

## 5. Field-level 语义

### 5.1 `project`

对应 `BlueprintProjectV0`：

- `name`：项目展示名
- `source_market`：目标市场，默认 `US`
- `source_language`：目标语言，默认 `en-US`
- `notes`：项目级补充说明

### 5.2 `reference`

对应 `BlueprintReferenceV0`：

- `source_kind`：参考来源类型，允许 `uploaded_video | url | manual_notes | mixed`
- `source_uri`：来源 URI；上传视频时可填相对路径或外部引用
- `structural_goal`：一句话描述要保留的创意结构
- `retained_axes`：必须保留的维度，如 hook 结构、节奏、利益点顺序
- `swappable_axes`：允许替换的维度，如产品、模特、场景、卖点文案
- `reference_beats`：参考节拍映射到 blueprint sequence 的列表
- `notes`：其他自由说明

### 5.3 `reference.reference_beats[]`

对应 `BlueprintReferenceBeatV0`：

- `beat_code`：参考 beat 唯一编码
- `sequence_code`：映射到哪个 blueprint sequence
- `structural_function`：该 beat 的结构作用，如 `hook` / `demo` / `cta`
- `summary`：该 beat 的内容摘要
- `rewrite_notes`：该 beat 改写提示

### 5.4 `global_constraints`

对应 `BlueprintGlobalConstraintsV0`：

- `aspect_ratio`：默认 `9:16`
- `target_duration_ms`：整体目标时长
- `style_tags`：风格标签
- `banned_elements`：显式禁用元素

### 5.5 `compile_preferences`

对应 `BlueprintCompilePreferencesV0`：

- `requested_runtime_version`：若提供，则 compiler stub 使用该版本
- `compile_reason`：默认 `blueprint_stub`
- `compile_options`：附加 compile 选项，会被 merge 到 runtime `compile_options`
- `dispatch_jobs`：当前仅保留字段，stub 不做 job dispatch

### 5.6 `sequences[]`

对应 `BlueprintSequenceV0`：

- `sequence_code`：sequence 稳定业务编码
- `sequence_index`：顺序索引，必须全局唯一
- `sequence_type`：如 `hook` / `problem` / `demo` / `offer` / `cta`
- `persuasive_goal`：说服目标
- `target_duration_ms`：该段目标时长
- `structural_role`：结构职责备注
- `spus[]`：视觉单元
- `vbus[]`：文案/语音单元
- `bridges[]`：sequence 内绑定关系

### 5.7 `spus[]`

对应 `BlueprintSPUV0`：

- `spu_code`：视觉单元编码
- `display_name`：展示名
- `asset_role`：默认 `primary_visual`
- `duration_ms`：片段时长
- `generation_mode`：默认 `veo_segment`
- `prompt_text`：视觉生成主提示
- `negative_prompt_text`：负向提示
- `visual_constraints`：局部视觉约束
- `status`：默认 `draft`
- `reference_mapping`：该 SPU 来自哪些参考片段、保留什么、改写什么

### 5.8 `vbus[]`

对应 `BlueprintVBUV0`：

- `vbu_code`：语音/文案单元编码
- `persuasive_role`：默认 `benefit`
- `script_text`：文案正文
- `voice_profile`：语音配置
- `language`：为空时回退到 `project.source_language`
- `duration_ms`：可选时长
- `tts_params`：TTS 参数
- `status`：默认 `draft`
- `reference_mapping`：该 VBU 的参考映射

### 5.9 `bridges[]`

对应 `BlueprintBridgeV0`：

- `bridge_code`：绑定编码
- `bridge_type`：默认 `sequence_unit_binding`
- `execution_order`：同 sequence 内执行顺序
- `spu_code`：可选，指向本 sequence 内 SPU
- `vbu_code`：可选，指向本 sequence 内 VBU
- `transition_policy`：衔接策略
- `status`：默认 `draft`

约束：`spu_code` 与 `vbu_code` 至少要提供一个，否则报错 `bridge_requires_spu_or_vbu_binding`。

---

## 6. Validation 规则

`BlueprintV0` 在 model validator 中执行最小一致性校验：

### 6.1 sequence 级

- `sequence_code` 全局唯一，否则 `duplicate_sequence_code:<sequence_code>`
- `sequence_index` 全局唯一，否则 `duplicate_sequence_index:<sequence_index>`
- 每个 sequence 至少含一个 SPU 或 VBU，否则 `sequence_requires_spu_or_vbu:<sequence_code>`

### 6.2 SPU / VBU 唯一性

- sequence 内 SPU code 不可重复，否则 `duplicate_sequence_spu_code:<sequence_code>`
- sequence 内 VBU code 不可重复，否则 `duplicate_sequence_vbu_code:<sequence_code>`
- 全局 SPU code 不可重复，否则 `duplicate_spu_code:<spu_code>`
- 全局 VBU code 不可重复，否则 `duplicate_vbu_code:<vbu_code>`
- 全局至少存在一个 SPU，否则 `blueprint_requires_at_least_one_spu`

### 6.3 bridge 级

- `bridge_code` 全局唯一，否则 `duplicate_bridge_code:<bridge_code>`
- 同 sequence 内 `execution_order` 唯一，否则 `duplicate_bridge_execution_order:<sequence_code>:<order>`
- `bridge.spu_code` 必须引用本 sequence 内 SPU，否则 `bridge_spu_missing:<bridge_code>:<spu_code>`
- `bridge.vbu_code` 必须引用本 sequence 内 VBU，否则 `bridge_vbu_missing:<bridge_code>:<vbu_code>`

### 6.4 reference beats

- `beat_code` 唯一，否则 `duplicate_reference_beat_code:<beat_code>`
- `reference_beats[].sequence_code` 必须存在于 blueprint sequences，否则 `reference_beat_sequence_missing:<beat_code>:<sequence_code>`

---

## 7. Reference -> Blueprint 映射规范

Blueprint v0 不负责自动解析视频，但规定了人工/半自动抽取得到 Blueprint 的最小映射方式。

### 7.1 输入来源

允许三类来源：

1. 上传视频
2. URL 链接
3. 人工笔记/拆解稿

### 7.2 映射步骤

#### Step 1: 提炼 reference intent

先写入：

- `reference.source_kind`
- `reference.source_uri`
- `reference.structural_goal`
- `reference.retained_axes`
- `reference.swappable_axes`

#### Step 2: 切 reference beats

把参考视频按结构节拍切成 beats，例如：

- `hook_open`
- `problem_closeup`
- `demo_texture`
- `social_proof`
- `cta_offer`

每个 beat 记录：

- 功能是什么
- 摘要是什么
- 准备映射到哪个 `sequence_code`
- 需要如何改写

#### Step 3: 落到 blueprint sequences

每个 beat 或相邻 beats 可折叠为一个 `sequence`。sequence 需要明确：

- 顺序
- 类型
- persuasive goal
- 目标时长
- structural role

#### Step 4: 拆分视觉/话术单元

- 视觉内容进入 `spus[]`
- 旁白/字幕/口播进入 `vbus[]`
- 若两者需要明确绑定，则建立 `bridges[]`

#### Step 5: 标记 reference mapping

对每个 `spu` / `vbu` 填 `reference_mapping`：

- `source_moments`：来源 beat 或片段
- `preserved_elements`：保留元素
- `rewrite_axes`：改写轴

### 7.3 v0 推荐映射粒度

推荐一个 sequence 只表达一个明确说服动作，例如：

- 抓眼 hook
- 痛点描述
- 使用演示
- 效果证明
- CTA 收口

这样后续更容易扩展到 shot planning 或 multi-asset compile。

---

## 8. Blueprint -> Runtime compile 映射

最小 compiler stub 位于：

- `app/compilers/orchestrator/blueprint_compiler.py`

入口：

- `compile_blueprint_v0_to_runtime_packet(blueprint: BlueprintV0) -> RuntimePacket`

### 8.1 编译目标

Blueprint 直接编译为当前已有 `app/schemas/compile.py::RuntimePacket`，不改 shape。

### 8.2 deterministic UUID 规则

使用：

- `BLUEPRINT_UUID_NAMESPACE = uuid5(NAMESPACE_URL, "ai-videos-replication/blueprint-v0")`
- `_stable_uuid(kind, *parts)`

映射规则：

- `project_id = uuid5(namespace, "project::<blueprint_id>")`
- `sequence_id = uuid5(namespace, "sequence::<blueprint_id>::<sequence_code>")`
- `spu_id = uuid5(namespace, "spu::<blueprint_id>::<sequence_code>::<spu_code>")`
- `vbu_id = uuid5(namespace, "vbu::<blueprint_id>::<sequence_code>::<vbu_code>")`
- `bridge_id = uuid5(namespace, "bridge::<blueprint_id>::<sequence_code>::<bridge_code>")`

### 8.3 顶层字段映射

- `RuntimePacket.project_id` <- stable project UUID
- `RuntimePacket.runtime_version` <- `requested_runtime_version` 或 `<blueprint_id>.stub`
- `RuntimePacket.compile_reason` <- `compile_preferences.compile_reason`
- `RuntimePacket.compile_options` <- `compile_preferences.compile_options` 合并以下默认值：
  - `blueprint_id`
  - `blueprint_version`
  - `aspect_ratio`
  - `style_tags`
  - `banned_elements`
  - `target_duration_ms`
  - `reference`
- `visual_track_count` <- 所有 sequence 的 `spus` 数量和
- `audio_track_count` <- 所有 sequence 的 `vbus` 数量和
- `bridge_count` <- 所有 sequence 的 `bridges` 数量和

### 8.4 sequence 映射

每个 Blueprint sequence 映射为 `RuntimeSequencePacket`：

- `sequence_id`
- `sequence_index`
- `sequence_type`
- `persuasive_goal`
- `spus`
- `vbus`
- `bridges`

sequence 在编译时按 `sequence_index` 排序。

### 8.5 SPU 映射

每个 SPU 编译后保留：

- `spu_id`
- `spu_code`
- `display_name`
- `asset_role`
- `duration_ms`
- `generation_mode`
- `prompt_text`
- `negative_prompt_text`
- `visual_constraints`
- `status`
- `reference_mapping`
- `sequence_code`

### 8.6 VBU 映射

每个 VBU 编译后保留：

- `vbu_id`
- `vbu_code`
- `persuasive_role`
- `script_text`
- `voice_profile`
- `language`
- `duration_ms`
- `tts_params`
- `status`
- `reference_mapping`
- `sequence_code`

其中 `language` 为空时自动回退到 `blueprint.project.source_language`。

### 8.7 Bridge 映射

每个 bridge 编译后保留：

- `bridge_id`
- `bridge_code`
- `bridge_type`
- `execution_order`
- `spu_id`
- `vbu_id`
- `spu_code`
- `vbu_code`
- `transition_policy`
- `status`
- `sequence_code`

bridge 在 sequence 内按 `execution_order` 排序。

---

## 9. JSON schema 导出

权威模型：

- `app/schemas/blueprint.py::BlueprintV0`

导出脚本：

- `scripts/export_blueprint_schema.py`

导出产物：

- `docs/contracts/schemas/blueprint_v0.schema.json`

该产物由 `BlueprintV0.model_json_schema()` 生成，用于：

- 静态契约审查
- 外部工具消费
- CI / 自检中的 schema 快速比对

---

## 10. 示例文件

beauty / cosmetics 示例 Blueprint 位于：

- `docs/examples/beauty_cosmetics_blueprint_v0.json`

它展示一个最小但完整的美妆带货结构：

1. Hook 开场
2. Problem 痛点
3. Demo 使用演示
4. CTA 收口

并显式记录：

- reference beats
- retained vs swappable axes
- spu / vbu 的 reference mapping
- bridge 绑定

---

## 11. Self-check 范围

最小自检覆盖：

1. 示例 Blueprint 可被 `BlueprintV0` 成功校验
2. 导出的 JSON schema 可生成
3. compiler stub 能把示例 Blueprint 编译成 `RuntimePacket`
4. 关键 compile surface 保持稳定：
   - runtime version
   - track counts
   - compile options 默认注入
   - sequence 排序
   - language fallback
   - deterministic UUID 稳定
5. Blueprint SDK artifact discovery surface 保持稳定：
   - artifact index keys 固定为 `example_payload` / `contract_doc` / `json_schema`
   - contract doc accessor 可读取冻结文档正文
6. contract doc 关键 marker 保持存在：
   - `# Blueprint v0 Contract`
   - `bridge_requires_spu_or_vbu_binding`
   - `reference_beat_sequence_missing:<beat_code>:<sequence_code>`
   - `## 11. Self-check 范围`
   - `## 12. 非目标与边界`

### 11.1 Fixture evolution policy

`docs/examples/beauty_cosmetics_blueprint_v0.json` 是 Blueprint v0 的 canonical fixture。

为避免 silent drift，以下约束冻结：

- `canonical_fixture_path:docs/examples/beauty_cosmetics_blueprint_v0.json`
- 示例 fixture 的 `blueprint_version`、`blueprint_id`、sequence 顺序（`hook -> problem -> demo -> cta`）、`requested_runtime_version` 与 `compile_reason` 属于 guardrail 范围
- `fixture_change_requires_contract_review`：任何改动 canonical fixture 语义、顺序、命名、计数或 compiler 期望的提交，都必须同步审查 contract doc、schema export、tests 与 self-check
- `breaking_fixture_semantics_require_versioned_surface`：若示例不再表达同一 Blueprint v0 语义，不可静默覆盖；必须通过新版本 surface、并行示例或显式 contract 版本升级承载

### 11.2 Contract change discipline

Blueprint v0 contract change 必须遵循以下 discipline：

- `contract_change_requires_guardrail_updates`：只要改动 public contract、artifact discovery keys、schema title/version literal、关键 validator message 或 compile preview 冻结结果，就必须在同一提交中同步更新 contract docs、tests 与 self-check
- 仅文案澄清且不影响 exported behavior 的修改，可作为 doc-only change，但不得删除冻结 marker
- 不允许在未更新 guardrail 的情况下静默改变 SDK export surface、artifact index keys、示例 fixture 语义或 compile output contract

对应文件：

- `docs/contracts/blueprint_v0_contract.md`
- `docs/contracts/blueprint_api_contract.md`
- `tests/test_blueprint_contract.py`
- `tests/test_blueprint_sdk_artifacts.py`
- `scripts/blueprint_self_check.py`
- `contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md`

---

## 12. 非目标与边界

以下内容不属于 Blueprint v0 最小包：

- 从 mp4 自动抽取 beats
- Blueprint 直接创建 DB `Project/Sequence/SPU/VBU/Bridge`
- Blueprint compile 后自动创建 runtime 记录
- Blueprint compile 后自动 dispatch 五类 jobs
- 修改 compile API / baseline gate / object store probe 逻辑

因此当前 Blueprint v0 应理解为：

> “仓库内已落地的、可独立校验与最小编译的中间契约层”，而不是完整生产流水线替代品。
