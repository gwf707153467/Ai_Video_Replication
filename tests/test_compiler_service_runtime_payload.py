from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from _db_test_helper import resolve_test_database_url
from app.compilers.orchestrator.compiler_service import CompilerService
from app.db.base import Base
from app.db.models import Bridge, CompiledRuntime, Job, Project, SPU, Sequence, VBU
from app.schemas.compile import CompileRequest
from app.services.asset_policy_service import AssetPolicyService


class CompilerServiceRuntimePayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(resolve_test_database_url(), future=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        try:
            self.db.rollback()
            self.db.execute(delete(Job))
            self.db.execute(delete(CompiledRuntime))
            self.db.execute(delete(Bridge))
            self.db.execute(delete(VBU))
            self.db.execute(delete(SPU))
            self.db.execute(delete(Sequence))
            self.db.execute(delete(Project))
            self.db.commit()
        finally:
            self.db.close()

    def _seed_project_fixture(self) -> dict:
        project = Project(
            name="Runtime Payload Demo",
            source_market="US",
            source_language="en-US",
            notes="multi sequence compile test",
        )
        self.db.add(project)
        self.db.flush()

        sequence_1 = Sequence(
            project_id=project.id,
            sequence_index=1,
            sequence_type="hook",
            persuasive_goal="Stop scroll with benefit-led opener.",
        )
        sequence_2 = Sequence(
            project_id=project.id,
            sequence_index=2,
            sequence_type="body",
            persuasive_goal="Demonstrate product payoff clearly.",
        )
        self.db.add(sequence_1)
        self.db.add(sequence_2)
        self.db.flush()

        spu_1 = SPU(
            project_id=project.id,
            sequence_id=sequence_1.id,
            spu_code=f"SPU-{uuid4().hex[:8]}-1",
            display_name="Primary visual 1",
            asset_role="primary_visual",
            duration_ms=4000,
            generation_mode="veo_segment",
            prompt_text="close-up hero shot",
            negative_prompt_text="no blur",
            visual_constraints={"sequence_index": 1, "style": "ugc"},
            status="draft",
        )
        spu_2 = SPU(
            project_id=project.id,
            sequence_id=sequence_2.id,
            spu_code=f"SPU-{uuid4().hex[:8]}-2",
            display_name="Primary visual 2",
            asset_role="primary_visual",
            duration_ms=6500,
            generation_mode="veo_segment",
            prompt_text="application demo",
            negative_prompt_text="no watermark",
            visual_constraints={"sequence_index": 2, "style": "ugc"},
            status="draft",
        )
        self.db.add(spu_1)
        self.db.add(spu_2)
        self.db.flush()

        vbu_1 = VBU(
            project_id=project.id,
            sequence_id=sequence_1.id,
            vbu_code=f"VBU-{uuid4().hex[:8]}-1",
            persuasive_role="hook",
            script_text="See the instant shine payoff.",
            voice_profile=None,
            language="en-US",
            duration_ms=4000,
            tts_params={"pace": 1.0},
            status="draft",
        )
        self.db.add(vbu_1)
        self.db.flush()

        bridge_1 = Bridge(
            project_id=project.id,
            sequence_id=sequence_1.id,
            spu_id=spu_1.id,
            vbu_id=vbu_1.id,
            bridge_code=f"BR-{uuid4().hex[:8]}-1",
            bridge_type="sequence_unit_binding",
            execution_order=1,
            transition_policy={"type": "cut"},
            status="draft",
        )
        bridge_2 = Bridge(
            project_id=project.id,
            sequence_id=sequence_2.id,
            spu_id=spu_2.id,
            vbu_id=None,
            bridge_code=f"BR-{uuid4().hex[:8]}-2",
            bridge_type="sequence_unit_binding",
            execution_order=2,
            transition_policy={"type": "cut"},
            status="draft",
        )
        self.db.add(bridge_1)
        self.db.add(bridge_2)
        self.db.commit()

        return {
            "project": project,
            "sequence_1": sequence_1,
            "sequence_2": sequence_2,
            "spu_1": spu_1,
            "spu_2": spu_2,
            "vbu_1": vbu_1,
            "bridge_1": bridge_1,
            "bridge_2": bridge_2,
        }

    def test_compile_project_builds_multi_sequence_runtime_payload(self) -> None:
        fixture = self._seed_project_fixture()
        project = fixture["project"]
        sequence_1 = fixture["sequence_1"]
        sequence_2 = fixture["sequence_2"]
        spu_1 = fixture["spu_1"]
        spu_2 = fixture["spu_2"]
        vbu_1 = fixture["vbu_1"]
        bridge_1 = fixture["bridge_1"]
        bridge_2 = fixture["bridge_2"]

        runtime = CompilerService(self.db).compile_project(
            CompileRequest(
                project_id=project.id,
                runtime_version="runtime.payload.v1",
                compile_reason="test_runtime_payload",
                compile_options={"source": "unit_test"},
                auto_version=False,
                dispatch_jobs=False,
            )
        )

        self.assertEqual(runtime.compile_status, "compiled")
        self.assertEqual(runtime.dispatch_status, "not_dispatched")
        self.assertEqual(runtime.dispatch_summary["job_count"], 0)
        self.assertEqual(runtime.dispatch_summary["dispatch_status"], "not_dispatched")

        persisted = self.db.execute(
            select(CompiledRuntime).where(CompiledRuntime.id == runtime.id)
        ).scalar_one()
        payload = persisted.runtime_payload

        self.assertEqual(payload["runtime_version"], "runtime.payload.v1")
        self.assertEqual(payload["compile_reason"], "test_runtime_payload")
        self.assertEqual(payload["compile_options"], {"source": "unit_test"})
        self.assertEqual(payload["sequence_count"], 2)
        self.assertEqual(payload["target_total_duration_ms"], 10500)
        self.assertEqual(payload["visual_track_count"], 2)
        self.assertEqual(payload["audio_track_count"], 1)
        self.assertEqual(payload["bridge_count"], 2)

        sequences = payload["sequences"]
        self.assertEqual([item["sequence_index"] for item in sequences], [1, 2])

        seq1 = sequences[0]
        self.assertEqual(seq1["sequence_id"], str(sequence_1.id))
        self.assertEqual(seq1["sequence_index"], 1)
        self.assertEqual(seq1["sequence_type"], "hook")
        self.assertEqual(seq1["persuasive_goal"], "Stop scroll with benefit-led opener.")
        self.assertEqual(seq1["target_duration_ms"], 4000)
        self.assertTrue(seq1["has_voice"])
        self.assertEqual(len(seq1["spus"]), 1)
        self.assertEqual(len(seq1["vbus"]), 1)
        self.assertEqual(len(seq1["bridges"]), 1)
        self.assertEqual(seq1["spus"][0]["spu_id"], str(spu_1.id))
        self.assertEqual(seq1["vbus"][0]["vbu_id"], str(vbu_1.id))
        self.assertEqual(seq1["bridges"][0]["bridge_id"], str(bridge_1.id))

        seq2 = sequences[1]
        self.assertEqual(seq2["sequence_id"], str(sequence_2.id))
        self.assertEqual(seq2["sequence_index"], 2)
        self.assertEqual(seq2["sequence_type"], "body")
        self.assertEqual(seq2["persuasive_goal"], "Demonstrate product payoff clearly.")
        self.assertEqual(seq2["target_duration_ms"], 6500)
        self.assertFalse(seq2["has_voice"])
        self.assertEqual(len(seq2["spus"]), 1)
        self.assertEqual(len(seq2["vbus"]), 0)
        self.assertEqual(len(seq2["bridges"]), 1)
        self.assertEqual(seq2["spus"][0]["spu_id"], str(spu_2.id))
        self.assertEqual(seq2["bridges"][0]["bridge_id"], str(bridge_2.id))

    def test_compile_project_dispatch_jobs_persists_primary_sequence_selector(self) -> None:
        fixture = self._seed_project_fixture()
        project = fixture["project"]
        sequence_1 = fixture["sequence_1"]

        dispatched: list[tuple[str, str]] = []

        def _fake_dispatch(job: Job, runtime_version: str) -> str:
            dispatched.append((job.job_type, runtime_version))
            return f"task-{job.job_type}"

        with patch(
            "app.compilers.orchestrator.compiler_service.JobDispatchService.dispatch",
            side_effect=_fake_dispatch,
        ):
            runtime = CompilerService(self.db).compile_project(
                CompileRequest(
                    project_id=project.id,
                    runtime_version="runtime.payload.dispatch.v1",
                    compile_reason="test_dispatch_payload",
                    compile_options={"source": "unit_test"},
                    auto_version=False,
                    dispatch_jobs=True,
                )
            )

        self.assertEqual(runtime.compile_status, "dispatched")
        self.assertEqual(runtime.dispatch_status, "fully_dispatched")
        self.assertEqual(runtime.dispatch_summary["job_count"], 3)
        self.assertEqual(runtime.dispatch_summary["dispatched_job_count"], 3)
        self.assertEqual(runtime.dispatch_summary["queued_job_count"], 0)
        self.assertEqual(
            dispatched,
            [
                ("compile", "runtime.payload.dispatch.v1"),
                ("render_image", "runtime.payload.dispatch.v1"),
                ("render_video", "runtime.payload.dispatch.v1"),
            ],
        )

        jobs = self.db.execute(
            select(Job).where(Job.project_id == project.id).order_by(Job.created_at.asc())
        ).scalars().all()
        self.assertEqual([job.job_type for job in jobs], ["compile", "render_image", "render_video"])

        expected_selector = {
            "sequence_id": str(sequence_1.id),
            "sequence_index": sequence_1.sequence_index,
            "strategy": "compiler_default_first_sequence",
        }

        jobs_by_type = {job.job_type: job for job in jobs}
        self.assertNotIn("sequence_selector", jobs_by_type["compile"].payload)

        for job_type in ("render_image", "render_video"):
            self.assertEqual(jobs_by_type[job_type].payload.get("sequence_selector"), expected_selector)
            self.assertEqual(jobs_by_type[job_type].payload["runtime_version"], "runtime.payload.dispatch.v1")
            self.assertEqual(jobs_by_type[job_type].payload["dispatch_source"], "compile_endpoint")
            self.assertEqual(jobs_by_type[job_type].status, "dispatched")
            self.assertEqual(jobs_by_type[job_type].external_task_id, f"task-{job_type}")

        render_image_payload = jobs_by_type["render_image"].payload
        self.assertIn("prompt", render_image_payload)
        self.assertIn("provider_inputs", render_image_payload)
        self.assertEqual(render_image_payload["provider_inputs"]["runtime_version"], "runtime.payload.dispatch.v1")

    def test_render_job_sequence_selector_builds_sequence_scoped_runtime_asset_key(self) -> None:
        fixture = self._seed_project_fixture()
        project = fixture["project"]
        sequence_1 = fixture["sequence_1"]

        def _fake_dispatch(job: Job, runtime_version: str) -> str:
            return f"task-{job.job_type}"

        with patch(
            "app.compilers.orchestrator.compiler_service.JobDispatchService.dispatch",
            side_effect=_fake_dispatch,
        ):
            CompilerService(self.db).compile_project(
                CompileRequest(
                    project_id=project.id,
                    runtime_version="runtime.payload.dispatch.v2",
                    compile_reason="test_selector_asset_key",
                    compile_options={"source": "unit_test"},
                    auto_version=False,
                    dispatch_jobs=True,
                )
            )

        render_video_job = self.db.execute(
            select(Job)
            .where(Job.project_id == project.id, Job.job_type == "render_video")
            .order_by(Job.created_at.asc())
        ).scalar_one()

        selector = render_video_job.payload.get("sequence_selector")
        self.assertEqual(
            selector,
            {
                "sequence_id": str(sequence_1.id),
                "sequence_index": sequence_1.sequence_index,
                "strategy": "compiler_default_first_sequence",
            },
        )

        object_key = AssetPolicyService.build_runtime_asset_object_key(
            project_id=project.id,
            runtime_version="runtime.payload.dispatch.v2",
            job_type=render_video_job.job_type,
            filename="clip final.mp4",
            sequence_id=UUID(selector["sequence_id"]),
        )
        self.assertEqual(
            object_key,
            f"projects/{project.id}/runtime/runtime.payload.dispatch.v2/"
            f"sequences/{sequence_1.id}/render_video/clip_final.mp4",
        )


if __name__ == "__main__":
    unittest.main()
