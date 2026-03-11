from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class AttendanceRecordOut(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    department: str
    date: str
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    status: str
    scan_count: int = 0
    created_at: str


class AttendancePaginated(BaseModel):
    items: List[AttendanceRecordOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    date: str
    present: int
    late: int
    absent: int
    refused: int
    total_employees: int
    attendance_rate: int
    is_weekend: bool = False


class WeeklyDataPoint(BaseModel):
    date: str
    day_label: str
    present: int
    late: int
    absent: int
    refused: int


class SyncResponse(BaseModel):
    message: str
    synced: int
    agents_synced: int = 0
    total_fetched: int = 0
    skipped_no_id: int = 0
    skipped_duplicate: int = 0
    skipped_unknown: int = 0
    skipped_parse_error: int = 0


class AgentSyncResponse(BaseModel):
    """Response for the agent-sync endpoint."""
    message: str
    inserted: int
    updated: int
    deactivated: int
    total: int




class ScanLogOut(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    department: str
    scanned_at: str
    raw_time: str
    serial_no: Optional[int]
    created_at: str


class ScanLogPaginated(BaseModel):
    items: List[ScanLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int
