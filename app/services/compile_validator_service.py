from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Bridge, Project, Sequence, SPU, VBU


class CompileValidatorService:
    def __init__(self, db: Session):
        self.db = db

    def validate_project(self, project_id: UUID) -> dict:
        project = self.db.get(Project, project_id)
        if not project:
            raise ValueError("project_not_found")

        sequences = self.db.query(Sequence).filter(Sequence.project_id == project_id).all()
        spus = self.db.query(SPU).filter(SPU.project_id == project_id).all()
        vbus = self.db.query(VBU).filter(VBU.project_id == project_id).all()
        bridges = self.db.query(Bridge).filter(Bridge.project_id == project_id).all()

        errors: list[str] = []
        warnings: list[str] = []

        if not sequences:
            errors.append("missing_sequences")
        if not spus:
            errors.append("missing_spus")
        if not vbus:
            warnings.append("missing_vbus")
        if not bridges:
            warnings.append("missing_bridges")

        sequence_ids = {sequence.id for sequence in sequences}
        for spu in spus:
            if spu.sequence_id and spu.sequence_id not in sequence_ids:
                errors.append(f"spu_sequence_missing:{spu.spu_code}")
        for vbu in vbus:
            if vbu.sequence_id and vbu.sequence_id not in sequence_ids:
                errors.append(f"vbu_sequence_missing:{vbu.vbu_code}")
        for bridge in bridges:
            if bridge.sequence_id not in sequence_ids:
                errors.append(f"bridge_sequence_missing:{bridge.bridge_code}")

        return {
            "project_id": str(project_id),
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "counts": {
                "sequences": len(sequences),
                "spus": len(spus),
                "vbus": len(vbus),
                "bridges": len(bridges),
            },
        }
