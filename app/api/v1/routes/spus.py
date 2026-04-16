from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import SPU
from app.db.session import get_db
from app.schemas import SPUCreate, SPURead

router = APIRouter()


@router.get("", response_model=list[SPURead])
def list_spus(db: Session = Depends(get_db)) -> list[SPU]:
    return db.query(SPU).order_by(SPU.created_at.desc()).all()


@router.post("", response_model=SPURead)
def create_spu(payload: SPUCreate, db: Session = Depends(get_db)) -> SPU:
    spu = SPU(**payload.model_dump())
    db.add(spu)
    db.commit()
    db.refresh(spu)
    return spu
