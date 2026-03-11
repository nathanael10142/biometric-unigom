

import csv
import io
import logging
from collections import defaultdict
from datetime import datetime, time as time_type, timedelta
from typing import Any, Dict, List, Optional

import requests as req_lib
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.dependencies import get_current_admin
from app.database import get_db, get_prod_db
from app.models.agent_cache import AgentCache
from app.models.attendance import Attendance
from app.models.prod.user_prod import UserProd
from app.models.scan_log import ScanLog
from app.schemas.attendance import (
    AttendancePaginated,
    AttendanceRecordOut,
    ScanLogOut,
    ScanLogPaginated,
    SyncResponse,
)
from app.services.agent_sync_service import sync_agents
from app.services.attendance_service import sync_with_hikvision
from app.utils.time_utils import GOMA_TZ, now_goma, today_goma

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["Présences"])

_STATUS_LABELS = {
    "PRESENT": "Présent",
    "LATE":    "Retard",
    "ABSENT":  "Absent",
    "REFUSED": "Refusé",
}


# ── Scan-count helper ─────────────────────────────────────────────────────────


def _batch_scan_counts(
    db: Session,
    agent_date_pairs: List[tuple],
) -> Dict[tuple, int]:
    if not agent_date_pairs:
        return {}

    by_date: Dict = defaultdict(list)
    for agent_uuid, d in agent_date_pairs:
        by_date[d].append(agent_uuid)

    result: Dict[tuple, int] = {}
    for d, uuids in by_date.items():
        midnight_start = GOMA_TZ.localize(datetime.combine(d, time_type(0, 0, 0)))
        midnight_end   = GOMA_TZ.localize(datetime.combine(d + timedelta(days=1), time_type(0, 0, 0)))
        rows = (
            db.query(ScanLog.agent_uuid, func.count(ScanLog.id).label("cnt"))
            .filter(
                ScanLog.agent_uuid.in_(uuids),
                ScanLog.scanned_at >= midnight_start,
                ScanLog.scanned_at < midnight_end,
            )
            .group_by(ScanLog.agent_uuid)
            .all()
        )
        for row in rows:
            result[(row.agent_uuid, d)] = row.cnt

    return result


def _record_to_dict(r: Attendance, scan_count: int = 0) -> Dict[str, Any]:
    return {
        "id":            r.id,
        "employee_id":   r.agent_uuid,
        "employee_name": r.agent.full_name,
        "department":    r.agent.department,
        "date":          r.date.isoformat(),
        "time_in":       r.time_in.isoformat()  if r.time_in  else None,
        "time_out":      r.time_out.isoformat() if r.time_out else None,
        "status":        r.status,
        "scan_count":    scan_count,
        "created_at":    r.created_at.isoformat(),
    }


# ── Today ─────────────────────────────────────────────────────────────────────


@router.get("/today", summary="Pointages du jour")
def get_today_attendance(
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> List[Dict[str, Any]]:
    today = today_goma()
    records = (
        db.query(Attendance)
        .options(joinedload(Attendance.agent))
        .filter(Attendance.date == today)
        .order_by(Attendance.time_in.nullslast())
        .all()
    )

    pairs = [(r.agent_uuid, r.date) for r in records]
    scan_counts = _batch_scan_counts(db, pairs)

    return [
        _record_to_dict(r, scan_counts.get((r.agent_uuid, r.date), 0))
        for r in records
    ]


# ── History ───────────────────────────────────────────────────────────────────


def _build_history_query(
    db: Session,
    date_from: Optional[str],
    date_to: Optional[str],
    att_status: Optional[str],
    department: Optional[str],
    search: Optional[str],
):
    query = db.query(Attendance).join(AgentCache)
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    if att_status:
        query = query.filter(Attendance.status == att_status.upper())
    if department:
        query = query.filter(AgentCache.department == department)
    if search:
        term = f"%{search}%"
        query = query.filter(
            AgentCache.full_name.ilike(term) | AgentCache.biometric_id.ilike(term)
        )
    return query


@router.get(
    "/history",
    response_model=AttendancePaginated,
    summary="Historique des présences",
)
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="PRESENT|LATE|ABSENT|REFUSED"),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> AttendancePaginated:
    query = _build_history_query(db, date_from, date_to, status, department, search)
    total = query.count()
    records = (
        query.options(joinedload(Attendance.agent))
        .order_by(Attendance.date.desc(), Attendance.time_in.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    pairs = [(r.agent_uuid, r.date) for r in records]
    scan_counts = _batch_scan_counts(db, pairs)

    return AttendancePaginated(
        items=[
            AttendanceRecordOut(
                **_record_to_dict(r, scan_counts.get((r.agent_uuid, r.date), 0))
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


# ── Raw scan-log journal ──────────────────────────────────────────────────────


@router.get(
    "/scans",
    response_model=ScanLogPaginated,
    summary="Journal complet des scans biométriques",
)
def get_scan_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    agent_uuid: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> ScanLogPaginated:
    query = db.query(ScanLog).join(AgentCache, ScanLog.agent_uuid == AgentCache.uuid)

    if date_from:
        midnight = GOMA_TZ.localize(
            datetime.combine(datetime.strptime(date_from, "%Y-%m-%d").date(), time_type(0, 0, 0))
        )
        query = query.filter(ScanLog.scanned_at >= midnight)
    if date_to:
        midnight_next = GOMA_TZ.localize(
            datetime.combine(
                datetime.strptime(date_to, "%Y-%m-%d").date() + timedelta(days=1),
                time_type(0, 0, 0),
            )
        )
        query = query.filter(ScanLog.scanned_at < midnight_next)
    if agent_uuid:
        query = query.filter(ScanLog.agent_uuid == agent_uuid)
    if department:
        query = query.filter(AgentCache.department == department)
    if search:
        term = f"%{search}%"
        query = query.filter(
            AgentCache.full_name.ilike(term) | AgentCache.biometric_id.ilike(term)
        )

    total = query.count()
    logs = (
        query.options(joinedload(ScanLog.agent))
        .order_by(ScanLog.scanned_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ScanLogPaginated(
        items=[
            ScanLogOut(
                id=s.id,
                employee_id=s.agent_uuid,
                employee_name=s.agent.full_name,
                department=s.agent.department,
                scanned_at=s.scanned_at.isoformat(),
                raw_time=s.raw_time,
                serial_no=s.serial_no,
                created_at=s.created_at.isoformat(),
            )
            for s in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


# ── CSV Export ────────────────────────────────────────────────────────────────


@router.get("/export", summary="Export CSV des présences")
def export_csv(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> StreamingResponse:
    query = _build_history_query(db, date_from, date_to, status, department, search)
    records = (
        query.options(joinedload(Attendance.agent))
        .order_by(Attendance.date.desc())
        .all()
    )

    pairs = [(r.agent_uuid, r.date) for r in records]
    scan_counts = _batch_scan_counts(db, pairs)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Date", "Matricule", "Nom Complet", "Direction/Service", "Poste",
        "ID Biométrique", "Heure Entrée", "Heure Sortie", "Statut", "Nb Scans",
    ])

    for r in records:
        cnt = scan_counts.get((r.agent_uuid, r.date), 0)
        writer.writerow([
            r.date.strftime("%d/%m/%Y"),
            r.agent.matricule,
            r.agent.full_name,
            r.agent.department,
            r.agent.position,
            r.agent.biometric_id or "",
            r.time_in.strftime("%H:%M")  if r.time_in  else "",
            r.time_out.strftime("%H:%M") if r.time_out else "",
            _STATUS_LABELS.get(r.status, r.status),
            cnt,
        ])

    output.seek(0)
    filename = f"presence_unigom_{now_goma().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── On-demand sync ────────────────────────────────────────────────────────────


@router.get("/sync/raw-events", summary="Diagnostic: événements bruts vs base de données")
def raw_events_diagnostic(
    last_n: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> Dict[str, Any]:
    from app.services.hikvision import hikvision_client
    from app.utils.time_utils import parse_hikvision_time
    from sqlalchemy import func as sqlfunc

    last_serial: Optional[int] = db.query(sqlfunc.max(ScanLog.serial_no)).scalar()
    start_position = max((last_serial or 0) - last_n, 0)

    try:
        events, _final_pos = hikvision_client.fetch_all_events(
            start_time=None, end_time=None, start_position=start_position,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de contacter le terminal Hikvision: {exc}",
        )

    agents = db.query(AgentCache).filter(AgentCache.is_active == True).all()
    known_ids = {a.biometric_id: a.full_name for a in agents if a.biometric_id}

    known_events, parse_errors = [], []
    unknown_ids: set = set()

    for e in events:
        bio_id = (e.get("employeeNoString") or e.get("cardNo") or "").strip()
        raw_time = e.get("time", "")
        parsed_dt = parse_hikvision_time(raw_time)

        if not bio_id:
            continue
        if parsed_dt is None and raw_time:
            parse_errors.append({"biometric_id": bio_id, "raw_time": raw_time})
        if bio_id in known_ids:
            known_events.append({
                "biometric_id":  bio_id,
                "agent_name":    known_ids[bio_id],
                "raw_time":      raw_time,
                "goma_time":     parsed_dt.isoformat() if parsed_dt else None,
            })
        else:
            unknown_ids.add(bio_id)

    return {
        "cursor": {"last_serial": last_serial, "start_position": start_position},
        "device": {
            "total_events_fetched": len(events),
            "unique_biometric_ids": sorted({
                (e.get("employeeNoString") or e.get("cardNo") or "").strip()
                for e in events
                if (e.get("employeeNoString") or e.get("cardNo") or "").strip()
            }),
        },
        "db": {
            "known_agent_ids": sorted(known_ids.keys()),
            "total_active_agents": len(known_ids),
        },
        "analysis": {
            "matched_events": len(known_events),
            "unknown_biometric_ids": sorted(unknown_ids),
            "parse_errors": parse_errors,
            "events": known_events,
        },
        "status": "ok" if not unknown_ids and not parse_errors else "warnings",
    }


@router.get("/sync/test", summary="Tester la connexion au terminal Hikvision")
def test_hikvision_connection(
    _: UserProd = Depends(get_current_admin),
) -> Dict[str, Any]:
    from app.services.hikvision import hikvision_client

    ok = hikvision_client.test_connection()
    return {
        "reachable": ok,
        "device_ip": settings.HIKVISION_IP,
        "message": (
            f"Terminal {settings.HIKVISION_IP} joignable et authentifié."
            if ok
            else f"Terminal {settings.HIKVISION_IP} INJOIGNABLE — vérifiez le réseau."
        ),
    }


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Synchroniser avec le terminal Hikvision (+ refresh agents)",
)
def sync_attendance(
    prod_db: Session = Depends(get_prod_db),
    db: Session = Depends(get_db),
    admin: UserProd = Depends(get_current_admin),
) -> SyncResponse:
    # ── 1. Refresh agent cache from production DB ─────────────────────────────
    try:
        agent_summary = sync_agents(prod_db, db)
        agents_synced = agent_summary["total"]
    except Exception as exc:
        logger.error("[SYNC] Agent cache refresh failed: %s", exc)
        agents_synced = 0

    # ── 2. Sync Hikvision events ──────────────────────────────────────────────
    try:
        r = sync_with_hikvision(db)
        logger.info(
            "[SYNC] Admin %r triggered manual sync — %d new scans | agents_synced=%d",
            admin.email, r.new_scans, agents_synced,
        )
        return SyncResponse(
            message=f"Synchronisation réussie — {r.new_scans} nouveau(x) scan(s) enregistré(s).",
            synced=r.new_scans,
            agents_synced=agents_synced,
            total_fetched=r.total_fetched,
            skipped_no_id=r.skipped_no_id,
            skipped_duplicate=r.skipped_duplicate,
            skipped_unknown=r.skipped_unknown,
            skipped_parse_error=r.skipped_parse_error,
        )
    except req_lib.exceptions.ConnectionError as exc:
        logger.error("[SYNC] Cannot reach Hikvision device: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de joindre le terminal Hikvision ({settings.HIKVISION_IP}).",
        )
    except req_lib.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Délai d'attente dépassé en contactant le terminal ({settings.HIKVISION_IP}).",
        )
    except Exception as exc:
        logger.error("[SYNC] Unexpected sync error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erreur inattendue: {type(exc).__name__}: {exc}",
        )
