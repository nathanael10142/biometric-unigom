import csv
import io
import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.agent_cache import AgentCache
from app.models.attendance import Attendance
from app.models.scan_log import ScanLog
from app.schemas.attendance import (
    AttendanceRecordOut,
    AttendancePaginated,
    ScanLogOut,
    ScanLogPaginated,
    SyncResponse,
)
from app.services.attendance_service import sync_with_hikvision
from app.utils.time_utils import today_goma
from app.models.prod.user_prod import UserProd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["Présences"])


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _serialize_attendance(att: Attendance, db: Session) -> AttendanceRecordOut:
    # load agent relationship if not already
    agent = att.agent
    # count scans for that agent on the same date
    cnt = (
        db.query(func.count(ScanLog.id))
        .filter(
            ScanLog.agent_uuid == att.agent_uuid,
            func.date(ScanLog.scanned_at) == att.date,
        )
        .scalar()
        or 0
    )
    return AttendanceRecordOut(
        id=att.id,
        employee_id=att.agent_uuid,
        employee_name=agent.full_name,
        department=agent.department,
        date=att.date.isoformat(),
        time_in=att.time_in.isoformat() if att.time_in else None,
        time_out=att.time_out.isoformat() if att.time_out else None,
        status=att.status,
        scan_count=cnt,
        created_at=att.created_at.isoformat(),
    )


def _apply_att_filters(
    query,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    status: Optional[str],
    department: Optional[str],
    search: Optional[str],
    employee_id: Optional[str],
):
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    if status:
        query = query.filter(Attendance.status == status)
    if department:
        query = query.filter(AgentCache.department == department)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                AgentCache.full_name.ilike(term),
                AgentCache.biometric_id.ilike(term),
            )
        )
    if employee_id:
        query = query.filter(Attendance.agent_uuid == employee_id)
    return query


def _serialize_scan(scan: ScanLog) -> ScanLogOut:
    return ScanLogOut(
        id=scan.id,
        employee_id=scan.agent_uuid,
        employee_name=scan.agent.full_name,
        department=scan.agent.department,
        scanned_at=scan.scanned_at.isoformat(),
        raw_time=scan.raw_time,
        serial_no=scan.serial_no,
        created_at=scan.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@router.get("/today", response_model=List[AttendanceRecordOut], summary="Présences du jour")
def get_today(
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> List[AttendanceRecordOut]:
    today = today_goma()
    rows: List[Attendance] = (
        db.query(Attendance)
        .filter(Attendance.date == today)
        .all()
    )
    return [_serialize_attendance(r, db) for r in rows]


@router.get("/history", response_model=AttendancePaginated, summary="Historique des présences")
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> AttendancePaginated:
    query = db.query(Attendance).join(AgentCache)
    query = _apply_att_filters(query, date_from, date_to, status, department, search, employee_id)

    total: int = query.count()
    items = (
        query
        .order_by(Attendance.date.desc(), Attendance.time_in.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AttendancePaginated(
        items=[_serialize_attendance(r, db) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/scans", response_model=ScanLogPaginated, summary="Journal des scans")
def scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    employee_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> ScanLogPaginated:
    query = db.query(ScanLog).join(AgentCache)
    if date_from:
        query = query.filter(ScanLog.scanned_at >= date_from)
    if date_to:
        query = query.filter(ScanLog.scanned_at <= date_to)
    if employee_id:
        query = query.filter(ScanLog.agent_uuid == employee_id)
    if department:
        query = query.filter(AgentCache.department == department)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                AgentCache.full_name.ilike(term),
                AgentCache.biometric_id.ilike(term),
            )
        )

    total = query.count()
    items = (
        query.order_by(ScanLog.scanned_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ScanLogPaginated(
        items=[_serialize_scan(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/export", summary="Exporter l'historique CSV")
def export_csv(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> Response:
    # reuse history query but without pagination
    query = db.query(Attendance).join(AgentCache)
    query = _apply_att_filters(query, date_from, date_to, status, department, search, employee_id)
    rows = query.order_by(Attendance.date.desc(), Attendance.time_in.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "employee_id",
        "employee_name",
        "department",
        "date",
        "time_in",
        "time_out",
        "status",
        "scan_count",
        "created_at",
    ])
    for r in rows:
        rec = _serialize_attendance(r, db)
        writer.writerow([
            rec.employee_id,
            rec.employee_name,
            rec.department,
            rec.date,
            rec.time_in or "",
            rec.time_out or "",
            rec.status,
            rec.scan_count,
            rec.created_at,
        ])
    return Response(content=output.getvalue(), media_type="text/csv")


@router.post("/sync", response_model=SyncResponse, summary="Synchroniser les scans")
def sync_scans(
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> SyncResponse:
    result = sync_with_hikvision(db)
    return SyncResponse(
        message="Synchronisation effectuée",
        synced=result.new_scans,
        agents_synced=result.attendance_updated,
        total_fetched=result.total_fetched,
        skipped_no_id=result.skipped_no_id,
        skipped_duplicate=result.skipped_duplicate,
        skipped_unknown=result.skipped_unknown,
        skipped_parse_error=result.skipped_parse_error,
    )
