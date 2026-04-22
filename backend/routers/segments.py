from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from backend.database import get_session
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.segment import Segment
from backend.models.push_record import PushRecord
from backend.schemas.segment import SegmentRead, SegmentUpdate
from backend.schemas.push_record import PushRecordRead

router = APIRouter()


@router.get("/{segment_id}", response_model=SegmentRead)
def get_segment(
    segment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    segment = session.get(Segment, segment_id)
    if not segment or segment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.patch("/{segment_id}", response_model=SegmentRead)
def update_segment(
    segment_id: int,
    body: SegmentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    segment = session.get(Segment, segment_id)
    if not segment or segment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Segment not found")

    if body.text is not None:
        segment.text = body.text
    if body.translation is not None:
        segment.translation = body.translation

    session.add(segment)
    session.commit()
    session.refresh(segment)
    return segment


@router.get("/{segment_id}/push-records", response_model=list[PushRecordRead])
def get_push_records(
    segment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    segment = session.get(Segment, segment_id)
    if not segment or segment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Segment not found")

    records = session.exec(
        select(PushRecord)
        .where(PushRecord.segment_id == segment_id)
        .order_by(PushRecord.created_at.desc())
    ).all()
    return list(records)
