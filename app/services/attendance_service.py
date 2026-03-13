

import logging
from datetime import datetime, time as time_type
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_cache import AgentCache
from app.models.attendance import Attendance
from app.models.scan_log import ScanLog
from app.models.sync_cursor import SyncCursor
from app.services.hikvision import hikvision_client
from app.utils.time_utils import (
    determine_arrival_status,
    now_goma,
    parse_hikvision_time,
    today_goma,
)

logger = logging.getLogger(__name__)

_MORNING_START = time_type(6, 0, 0)
_MORNING_END   = time_type(12, 0, 0)
_EVENING_START = time_type(16, 0, 0)
_ABSENT_CUTOFF = time_type(8, 21, 0)

_CURSOR_KEY = "hikvision"


# ── Scan audit log ────────────────────────────────────────────────────────────


def _log_scan(
    db: Session,
    agent: AgentCache,
    event_dt: datetime,
    raw_time: str,
    serial_no: Optional[int] = None,
    device_id: str = None,
    campus_id: str = None,
) -> bool:
    scan = ScanLog(
        agent_uuid=agent.uuid,
        scanned_at=event_dt,
        raw_time=raw_time,
        serial_no=serial_no,
        device_id=device_id or "UNKNOWN",
        campus_id=campus_id or "UNKNOWN",
    )
    db.add(scan)
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


# ── Core event processor ──────────────────────────────────────────────────────


def process_event(db: Session, agent: AgentCache, event_dt: datetime) -> bool:
    """
    Apply attendance business rules to one timestamped scan event.

    Morning  (06:00–12:00) → create/update Attendance (PRESENT / LATE / REFUSED).
    Evening  (16:00–24:00) → update time_out. Requires a confirmed time_in.
    Mid-day  (12:00–16:00) → scan log only; no attendance action.
    """
    event_date = event_dt.date()
    clock_time = event_dt.time()

    existing: Optional[Attendance] = (
        db.query(Attendance)
        .filter(
            Attendance.agent_uuid == agent.uuid,
            Attendance.date == event_date,
        )
        .first()
    )

    # ── Morning arrival ───────────────────────────────────────────────────────
    if _MORNING_START <= clock_time < _MORNING_END:
        if existing and existing.time_in is not None:
            return False  # first scan wins

        status = determine_arrival_status(clock_time)
        
        # Logs de debug détaillés pour comprendre le problème
        logger.info(
            "[ARRIVAL] Agent=%s | Date=%s | Time=%s | Status=%s | Existing=%s",
            agent.full_name, event_date, clock_time, status, existing.status if existing else "NEW"
        )

        if existing:
            existing.time_in = event_dt
            existing.status = status
            logger.info(
                "[ARRIVAL] UPDATED: Agent=%s | New Status=%s | Time=%s",
                agent.full_name, status, event_dt
            )
        else:
            db.add(Attendance(
                agent_uuid=agent.uuid,
                date=event_date,
                time_in=event_dt,
                status=status,
            ))
            logger.info(
                "[ARRIVAL] CREATED: Agent=%s | Status=%s | Time=%s",
                agent.full_name, status, event_dt
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.error("[ARRIVAL] ERROR: Failed to save attendance for %s", agent.full_name)
            return False
        return True

    # ── Evening departure ─────────────────────────────────────────────────────
    elif clock_time >= _EVENING_START:
        if not existing:
            logger.info(
                "[ATTEND] Evening scan without arrival ignored — "
                "agent=%r date=%s",
                agent.full_name, event_date,
            )
            return False

        if existing.time_in is None:
            logger.info(
                "[ATTEND] Departure ignored — agent=%r date=%s status=%s has no time_in",
                agent.full_name, event_date, existing.status,
            )
            return False

        if existing.time_out is None or event_dt > existing.time_out:
            existing.time_out = event_dt
            db.commit()
            return True
        return False

    # ── Mid-day (12:00–16:00) — audit log only ────────────────────────────────
    return False

# ── Push‑mode event helper ─────────────────────────────────────────────────────

def process_pushed_event(
    db: Session,
    biometric_id: str,
    serial_no: Optional[int],
    raw_time: str,
    device_id: str = None,
    campus_id: str = None,
) -> bool:
    if not biometric_id:
        return False

    agent: Optional[AgentCache] = (
        db.query(AgentCache)
        .filter(
            AgentCache.biometric_id == biometric_id,
            AgentCache.is_active == True,
        )
        .first()
    )
    if agent is None:
        logger.debug("[PUSH] Unknown biometric_id %r — skipped", biometric_id)
        return False

    event_dt = parse_hikvision_time(raw_time)
    if event_dt is None:
        logger.warning("[PUSH] Unparseable time %r for %r — skipped", raw_time, agent.full_name)
        return False

    is_new = _log_scan(db, agent, event_dt, raw_time, serial_no, device_id, campus_id)
    if not is_new:
        return False

    if serial_no is not None:
        cursor = _get_cursor(db)
        if cursor.last_serial is None or serial_no > cursor.last_serial:
            _update_cursor(db, cursor, cursor.last_position, serial_no)

    if process_event(db, agent, event_dt):
        return True

    return False

# ── Cursor helpers ────────────────────────────────────────────────────────────


def _get_cursor(db: Session) -> SyncCursor:
    cursor = (
        db.query(SyncCursor)
        .filter(SyncCursor.key == _CURSOR_KEY)
        .first()
    )
    if cursor is None:
        cursor = SyncCursor(key=_CURSOR_KEY, last_position=0, last_serial=None)
        try:
            db.add(cursor)
            db.flush()
        except IntegrityError:
            # Another process created it, query again
            db.rollback()
            cursor = (
                db.query(SyncCursor)
                .filter(SyncCursor.key == _CURSOR_KEY)
                .first()
            )
            if cursor is None:
                raise RuntimeError("Failed to get or create sync cursor")
    return cursor


def _update_cursor(
    db: Session,
    cursor: SyncCursor,
    final_position: int,
    max_serial: Optional[int],
) -> None:
    cursor.last_position = final_position
    if max_serial is not None:
        cursor.last_serial = max_serial
    db.commit()


# ── Sync result ───────────────────────────────────────────────────────────────


class SyncResult:
    """Counters returned by sync_with_hikvision."""
    __slots__ = (
        "new_scans", "attendance_updated",
        "total_fetched", "skipped_no_id",
        "skipped_duplicate", "skipped_unknown", "skipped_parse_error",
    )

    def __init__(self) -> None:
        self.new_scans           = 0
        self.attendance_updated  = 0
        self.total_fetched       = 0
        self.skipped_no_id       = 0
        self.skipped_duplicate   = 0
        self.skipped_unknown     = 0
        self.skipped_parse_error = 0


# ── Main sync entry point ─────────────────────────────────────────────────────


def sync_with_hikvision(db: Session) -> SyncResult:
    """
    Pull new events from the Hikvision terminal using the dual-cursor strategy.

    Agent resolution uses the local agent_cache table (presence DB).
    The agent_cache must be synced from production before calling this function.

    Parameters
    ----------
    db : Session
        Presence DB session (read-write).
        The production DB session is NOT needed here — agent_cache is used.
    """
    result = SyncResult()

    # ── 1. Read cursor ────────────────────────────────────────────────────────
    cursor        = _get_cursor(db)
    last_position = cursor.last_position
    last_serial   = cursor.last_serial

    logger.info(
        "[SYNC] Starting — last_position=%d last_serial=%s",
        last_position, last_serial,
    )

    # ── 2. Fetch events from terminal (NO date filter) ────────────────────────
    events, final_position = hikvision_client.fetch_all_events(
        start_time=None,
        end_time=None,
        start_position=last_position,
    )

    result.total_fetched = len(events)
    logger.info("[SYNC] Fetched %d events | next_position=%d", result.total_fetched, final_position)

    max_serial: Optional[int] = last_serial

    # ── 3. Process each event ─────────────────────────────────────────────────
    for event in events:

        # a. Must have a biometric ID
        biometric_id: str = (
            event.get("employeeNoString") or event.get("cardNo") or ""
        ).strip()
        if not biometric_id:
            result.skipped_no_id += 1
            continue

        serial_no: Optional[int] = event.get("serialNo")

        # b. Deduplication safety net
        if (
            last_serial is not None
            and serial_no is not None
            and serial_no <= last_serial
        ):
            result.skipped_duplicate += 1
            continue

        # c. Resolve agent from local agent_cache (no cross-DB needed)
        agent: Optional[AgentCache] = (
            db.query(AgentCache)
            .filter(
                AgentCache.biometric_id == biometric_id,
                AgentCache.is_active == True,
            )
            .first()
        )
        if agent is None:
            logger.debug("[SYNC] Unknown biometric_id %r — skipped", biometric_id)
            result.skipped_unknown += 1
            continue

        # d. Parse Hikvision timestamp
        raw_time: str = event.get("time", "")
        event_dt = parse_hikvision_time(raw_time)
        if event_dt is None:
            logger.warning("[SYNC] Unparseable time %r for %r — skipped", raw_time, agent.full_name)
            result.skipped_parse_error += 1
            continue

        # e. Store in scan_logs
        is_new = _log_scan(db, agent, event_dt, raw_time, serial_no, device_id=settings.DEVICE_ID, campus_id=settings.CAMPUS_ID)
        if not is_new:
            result.skipped_duplicate += 1
            continue

        result.new_scans += 1
        logger.debug(
            "[SCAN] ✅ serial=%s agent=%r time=%s",
            serial_no, agent.full_name, event_dt.strftime("%H:%M:%S"),
        )

        if serial_no is not None:
            if max_serial is None or serial_no > max_serial:
                max_serial = serial_no

        # f. Apply attendance business rules
        if process_event(db, agent, event_dt):
            result.attendance_updated += 1

    # ── 4. Persist cursor ─────────────────────────────────────────────────────
    _update_cursor(db, cursor, final_position, max_serial)

    logger.info(
        "[SYNC] Done — new=%d attend=%d | fetched=%d | "
        "skip: %d anon %d dup %d unknown %d parse_err | "
        "cursor: pos=%d serial=%s",
        result.new_scans, result.attendance_updated,
        result.total_fetched,
        result.skipped_no_id, result.skipped_duplicate,
        result.skipped_unknown, result.skipped_parse_error,
        final_position, max_serial,
    )

    # ── 5. Catch-up absent ────────────────────────────────────────────────────
    now = now_goma()
    if now.weekday() < 5 and now.time() >= _ABSENT_CUTOFF:
        _catchup_absent(db, today_goma())

    return result


def _catchup_absent(db: Session, today) -> None:
    """Mark ABSENT any active agent without an attendance record today."""
    active_agents: List[AgentCache] = (
        db.query(AgentCache).filter(AgentCache.is_active == True).all()
    )
    existing_uuids = {
        row.agent_uuid
        for row in db.query(Attendance.agent_uuid)
        .filter(Attendance.date == today)
        .all()
    }
    new_absent = [
        Attendance(agent_uuid=a.uuid, date=today, status="ABSENT")
        for a in active_agents
        if a.uuid not in existing_uuids
    ]
    if new_absent:
        db.add_all(new_absent)
        db.commit()
        logger.info(
            "[SYNC] Catch-up absent: marked %d agent(s) ABSENT for %s",
            len(new_absent), today,
        )


def mark_absent_employees(db: Session) -> int:
    """
    Called at 08:21 Goma time by APScheduler.
    Marks ABSENT every active agent without an Attendance record for today.
    """
    today = today_goma()
    active_agents: List[AgentCache] = (
        db.query(AgentCache).filter(AgentCache.is_active == True).all()
    )
    existing_uuids = {
        row.agent_uuid
        for row in db.query(Attendance.agent_uuid)
        .filter(Attendance.date == today)
        .all()
    }

    count = 0
    for agent in active_agents:
        if agent.uuid not in existing_uuids:
            db.add(Attendance(agent_uuid=agent.uuid, date=today, status="ABSENT"))
            count += 1

    if count:
        db.commit()

    logger.info("[ABSENT] Marked %d agents as ABSENT for %s", count, today)
    return count
