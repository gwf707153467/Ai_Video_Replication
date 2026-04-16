# Second Batch Engineering Notes

## 本轮新增范围

本轮将治理骨架从 `projects / sequences / compiled_runtimes / jobs` 扩展到：

- `spus`：视觉生产单元
- `vbus`：文案与语音说服单元
- `bridges`：sequence 与 spu/vbu 的桥接编排层
- `compile`：从控制面实体编译出 canonical runtime packet 并落 `compiled_runtimes`

## 领域职责

### SPU

SPU 是镜头级视觉生产单元，负责承载：
- 单段 Veo/图生视频生成的 prompt 与约束
- 时长、资产角色、模式等执行控制字段
- 后续 validator / retry 的最小视觉治理对象

### VBU

VBU 是语义与音频说服单元，负责承载：
- script_text
- persuasive_role
- voice_profile
- tts_params

### Bridge

Bridge 是真正的编排粘合层，用于把 sequence、SPU、VBU 显式绑定起来，并记录：
- execution_order
- bridge_type
- transition_policy

### Compile Runtime Packet

compile 接口当前不直接调 provider，而是：
1. 拉取项目下 sequence / spu / vbu / bridge
2. 组装 canonical runtime packet
3. 落盘到 `compiled_runtimes.runtime_payload`

这使后续 worker、validator、merge 都可以围绕同一个 runtime packet 工作。

## 新增 API

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `POST /api/v1/sequences`
- `GET /api/v1/sequences`
- `POST /api/v1/spus`
- `GET /api/v1/spus`
- `POST /api/v1/vbus`
- `GET /api/v1/vbus`
- `POST /api/v1/bridges`
- `GET /api/v1/bridges`
- `POST /api/v1/compile`

## 建议下一步

1. 补 `upload/export/assets` API
2. 加 `compile validation` 与 runtime schema versioning 规则
3. 把 compile 后续拆到 Celery tasks：`render_image` / `render_video` / `render_voice` / `merge`
4. 接 MinIO bucket bootstrap 与 asset manifest
