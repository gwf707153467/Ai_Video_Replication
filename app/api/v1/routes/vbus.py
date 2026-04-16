from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import VBU
from app.db.session import get_db
from app.schemas import VBUCreate, VBURead

router = APIRouter()


@router.get("", response_model=list[VBURead])
def list_vbus(db: Session = Depends(get_db)) -> list[VBU]:
    return db.query(VBU).order_by(VBU.created_at.desc()).all()


@router.post("", response_model=VBURead)
def create_vbu(payload: VBUCreate, db: Session = Depends(get_db)) -> VBU:
    vbu = VBU(**payload.model_dump())
    db.add(vbu)
    db.commit()
    db.refresh(vbu)
    return vbu
