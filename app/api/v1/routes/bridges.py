from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Bridge
from app.db.session import get_db
from app.schemas import BridgeCreate, BridgeRead

router = APIRouter()


@router.get("", response_model=list[BridgeRead])
def list_bridges(db: Session = Depends(get_db)) -> list[Bridge]:
    return db.query(Bridge).order_by(Bridge.execution_order.asc(), Bridge.created_at.asc()).all()


@router.post("", response_model=BridgeRead)
def create_bridge(payload: BridgeCreate, db: Session = Depends(get_db)) -> Bridge:
    bridge = Bridge(**payload.model_dump())
    db.add(bridge)
    db.commit()
    db.refresh(bridge)
    return bridge
