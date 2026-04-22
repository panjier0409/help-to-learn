import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.database import get_session
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.segment import Segment
from backend.models.material import Material
from backend.models.push_record import PushRecord, Platform, PushStatus
from backend.schemas.push_record import PushRequest, PushRecordRead
from backend.services import anki_service, telegram_service
from backend.config import settings

router = APIRouter()


def _do_push(segment: Segment, user: User, platform: Platform, session: Session) -> PushRecord:
    from backend.config import settings as cfg

    record = PushRecord(
        segment_id=segment.id,
        user_id=user.id,
        platform=platform,
        status=PushStatus.pending,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    try:
        if platform == Platform.anki:
            if not anki_service.check_connection(cfg.ANKI_CONNECT_URL):
                raise RuntimeError(
                    "Cannot connect to Anki. Make sure Anki is open with AnkiConnect installed."
                )
            audio_filename = os.path.basename(segment.audio_file_path)
            anki_service.store_media_file(cfg.ANKI_CONNECT_URL, audio_filename, segment.audio_file_path)
            note_id = anki_service.add_note(
                cfg.ANKI_CONNECT_URL,
                user.anki_deck_name,
                front_text=segment.text,
                back_text=segment.text,
                audio_filename=audio_filename,
                translation=segment.translation,
            )
            record.anki_card_id = note_id

        elif platform == Platform.telegram:
            if not user.telegram_chat_id:
                raise RuntimeError("Telegram chat ID not set. Update it in Settings.")
            if not cfg.TELEGRAM_BOT_TOKEN:
                raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured on the server.")
            caption = segment.text
            if segment.translation:
                caption += f"\n\n{segment.translation}"
            telegram_service.send_audio(
                bot_token=cfg.TELEGRAM_BOT_TOKEN,
                chat_id=user.telegram_chat_id,
                audio_path=segment.audio_file_path,
                caption=caption,
            )

        record.status = PushStatus.sent
        record.sent_at = datetime.utcnow()

    except Exception as e:
        record.status = PushStatus.failed
        record.error_msg = str(e)

    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.post("/segments/{segment_id}/push", response_model=PushRecordRead)
def push_segment(
    segment_id: int,
    body: PushRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    segment = session.get(Segment, segment_id)
    if not segment or segment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Segment not found")

    record = _do_push(segment, current_user, body.platform, session)
    if record.status == PushStatus.failed:
        raise HTTPException(status_code=502, detail=record.error_msg)
    return record


@router.post("/materials/{material_id}/push", response_model=list[PushRecordRead])
def push_material(
    material_id: int,
    body: PushRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bulk push all segments of a material."""
    material = session.get(Material, material_id)
    if not material or material.user_id != current_user.id or material.is_deleted:
        raise HTTPException(status_code=404, detail="Material not found")

    segments = session.exec(
        select(Segment)
        .where(Segment.material_id == material_id)
        .order_by(Segment.index)
    ).all()

    if not segments:
        raise HTTPException(status_code=400, detail="No segments found for this material")

    results = []
    for segment in segments:
        record = _do_push(segment, current_user, body.platform, session)
        results.append(record)

    return results
