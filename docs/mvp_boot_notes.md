# MVP Boot Notes

## 本次交付包含

- Docker Compose 基础运行时
- app / worker 双镜像，内置 FFmpeg
- FastAPI 控制面基础骨架
- PostgreSQL / Redis / MinIO 本地依赖
- SQLAlchemy + Alembic 初版
- Google provider 占位 adapter

## 当前不包含

- 真正的视频拆段与分析实现
- 真正的 Veo / Imagen / TTS 调用实现
- 完整 compiler validator QA merge pipeline
- 前端 UI

## 推荐下一步

1. 补 `spus/vbus/bridges` 的真实 ORM 表。
2. 定义 compile request / runtime packet 的 Pydantic schema。
3. 加入 bucket bootstrap 与 MinIO 初始化逻辑。
4. 加入 worker task：compile, render_image, render_video, render_voice, merge.
5. 为上传参考视频和产物导出补 API。
