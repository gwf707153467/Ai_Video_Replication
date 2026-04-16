from app.db.models import Job
from app.workers.tasks import (
    compile_runtime_task,
    merge_runtime_task,
    render_image_task,
    render_video_task,
    render_voice_task,
)


class JobDispatchService:
    task_map = {
        "compile": compile_runtime_task,
        "render_image": render_image_task,
        "render_video": render_video_task,
        "render_voice": render_voice_task,
        "merge": merge_runtime_task,
    }

    def dispatch(self, job: Job, runtime_version: str) -> str | None:
        task = self.task_map.get(job.job_type)
        if not task:
            return None
        result = task.delay(str(job.id), str(job.project_id), runtime_version)
        return result.id
