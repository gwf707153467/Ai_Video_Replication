# Database & Migrations

## 当前目标

本阶段只建立 MVP 的最小治理型数据骨架，保证控制面可以承载：

- Project 主体
- Sequence 分镜序列
- Compiled Runtime 编译结果快照
- Job 异步任务记录

## ORM 范围

位置：`app/db/models`

- `project.py`
- `sequence.py`
- `compiled_runtime.py`
- `job.py`

## Alembic 文件

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/20260330_0001_init_schema.py`

## 常用命令

### 本地 Python

```bash
python -m pip install -e .
alembic upgrade head
```

### Docker Compose

```bash
docker compose up --build
docker compose exec app alembic upgrade head
```

## 设计说明

1. 当前 schema 只覆盖治理控制面的最小主干，不直接展开所有视觉、语音、桥接、QA、导出子表。
2. `compiled_runtimes.runtime_payload` 使用 JSONB，作为编译后 canonical runtime packet 的落盘位置。
3. `jobs` 保留 provider 执行记录，为后续 retry / validator / merge worker 提供统一异步轨迹。
4. 后续建议继续扩展：`spus`、`vbus`、`bridges`、`qa_reports`、`assets`、`exports`。
