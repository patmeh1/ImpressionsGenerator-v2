"""Report management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.models.report import ReportResponse, ReportUpdate
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def list_reports(
    doctor_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """List reports with pagination. Admins see all; doctors see only their own."""
    if "Admin" in user.get("roles", []):
        all_reports = await cosmos_service.list_reports(doctor_id=doctor_id)
    else:
        all_reports = await cosmos_service.list_reports(doctor_id=user["user_id"])

    # Apply filters
    if search:
        q = search.lower()
        all_reports = [r for r in all_reports if q in r.get("input_text", "").lower() or q in r.get("findings", "").lower()]
    if report_type:
        all_reports = [r for r in all_reports if r.get("report_type") == report_type]
    if status:
        all_reports = [r for r in all_reports if r.get("status") == status]

    total = len(all_reports)
    start = (page - 1) * page_size
    items = all_reports[start : start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific report."""
    report = await _find_report(report_id, user)
    return report


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    body: ReportUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update/edit a report's findings, impressions, or recommendations."""
    report = await _find_report(report_id, user)
    data = body.model_dump(exclude_unset=True)
    updated = await cosmos_service.update_report(
        report_id=report_id,
        doctor_id=report["doctor_id"],
        data=data,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return updated


@router.post("/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark a report as final/approved."""
    report = await _find_report(report_id, user)
    approved = await cosmos_service.approve_report(
        report_id=report_id,
        doctor_id=report["doctor_id"],
    )
    if not approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return approved


@router.get("/{report_id}/versions")
async def get_report_versions(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get version history for a report."""
    report = await _find_report(report_id, user)
    return report.get("versions", [])


async def _find_report(report_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """Find a report and verify access permissions."""
    # Try finding with user's doctor_id first
    doctor_id = user.get("user_id", "")
    report = await cosmos_service.get_report(report_id, doctor_id)

    if not report and "Admin" in user.get("roles", []):
        # Admin: search across all doctors
        all_reports = await cosmos_service.list_reports()
        report = next((r for r in all_reports if r["id"] == report_id), None)

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if "Admin" not in user.get("roles", []) and report.get("doctor_id") != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own reports",
        )

    return report
