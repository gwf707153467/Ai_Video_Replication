from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Sequence
from app.db.session import get_db
from app.schemas import SequenceCreate, SequenceRead

router = APIRouter()


@router.get("", response_model=list[SequenceRead])
def list_sequences(db: Session = Depends(get_db)) -> list[Sequence]:
    return db.query(Sequence).order_by(Sequence.sequence_index.asc()).all()


@router.post("", response_model=SequenceRead)
def create_sequence(payload: SequenceCreate, db: Session = Depends(get_db)) -> Sequence:
    sequence = Sequence(**payload.model_dump())
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence
