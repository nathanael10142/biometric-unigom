

import logging
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.agent_cache import AgentCache
from app.models.attendance import Attendance
from app.models.prod.user_prod import UserProd
from app.schemas.attendance import DashboardStats, WeeklyDataPoint
from app.utils.time_utils import today_goma

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])

_DAY_LABELS = {0: "Lun", 1: "Mar", 2: "Mer", 3: "Jeu", 4: "Ven", 5: "Sam", 6: "Dim"}


@router.get("/stats", response_model=DashboardStats, summary="Statistiques du jour")
def get_stats(
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> DashboardStats:
    today = today_goma()

    rows = (
        db.query(Attendance.status, func.count(Attendance.id).label("cnt"))
        .filter(Attendance.date == today)
        .group_by(Attendance.status)
        .all()
    )
    counts = {row.status: row.cnt for row in rows}

    # Total active agents from local cache
    total: int = (
        db.query(func.count(AgentCache.uuid))
        .filter(AgentCache.is_active == True)
        .scalar() or 0
    )
    present = counts.get("PRESENT", 0)
    late    = counts.get("LATE", 0)
    absent  = counts.get("ABSENT", 0)
    refused = counts.get("REFUSED", 0)
    rate    = round((present + late) / total * 100) if total > 0 else 0

    is_weekend = today.weekday() in (5, 6)

    return DashboardStats(
        date=today.isoformat(),
        present=present,
        late=late,
        absent=absent,
        refused=refused,
        total_employees=total,
        attendance_rate=rate,
        is_weekend=is_weekend,
    )


@router.get("/weekly", response_model=List[WeeklyDataPoint], summary="Données hebdomadaires")
def get_weekly(
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> List[WeeklyDataPoint]:
    today = today_goma()
    week_ago = today - timedelta(days=6)

    rows = (
        db.query(
            Attendance.date,
            Attendance.status,
            func.count(Attendance.id).label("cnt"),
        )
        .filter(Attendance.date >= week_ago, Attendance.date <= today)
        .group_by(Attendance.date, Attendance.status)
        .all()
    )

    data: dict = {}
    current = week_ago
    while current <= today:
        if current.weekday() not in (5, 6):
            data[current] = {
                "date": current.isoformat(),
                "day_label": _DAY_LABELS[current.weekday()],
                "present": 0,
                "late": 0,
                "absent": 0,
                "refused": 0,
            }
        current += timedelta(days=1)

    for row in rows:
        if row.date in data:
            key = row.status.lower()
            if key in ("present", "late", "absent", "refused"):
                data[row.date][key] = row.cnt

    return [
        WeeklyDataPoint(**v)
        for v in sorted(data.values(), key=lambda x: x["date"])
    ]
