# Leave Management API Documentation

## Overview
Leave Management provides employee leave requests, approvals, balances, and leave types.

## Endpoints

All endpoints require JWT. Use header: `Authorization: Bearer <token>`

### Leave Types (HR/Admin)
- GET `/api/leave/types/`
- POST `/api/leave/types/` { name, description?, max_days_per_year, requires_approval, is_paid, is_active }
- GET `/api/leave/types/{id}/`
- PUT/PATCH `/api/leave/types/{id}/`
- DELETE `/api/leave/types/{id}/`

### Leave Requests
- GET `/api/leave/requests/`?status=&leave_type=&user_id=
- POST `/api/leave/requests/create/` { leave_type, start_date, end_date, reason, emergency_contact?, emergency_phone? }
- GET `/api/leave/requests/{id}/`
- POST `/api/leave/requests/{id}/approve/` { status: approved|rejected, approval_notes? } (HR/Admin)
- GET `/api/leave/my/` (employee's own)

### Leave Balances
- GET `/api/leave/balances/`?user_id=&leave_type=&year=
- POST `/api/leave/balances/allocate/` { user, leave_type, year, total_allocated } (HR/Admin)

## Notes
- LeaveRequest total_days is calculated and saved by model.
- If the LeaveType requires approval, new requests default to status=pending; otherwise approved.
- Balances auto-calc remaining_days on save.
- HR/Admin or Managers (can_manage_attendance) can view all; employees only their own.
