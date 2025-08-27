# Payroll Management System API Documentation

## Overview

The Payroll Management System provides comprehensive payroll processing, automatic calculations based on attendance records, overtime tracking, and detailed reporting. The system automatically calculates salaries, handles overtime (1.5x rate), and provides comprehensive analytics.

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Core Features

- **Automatic Payroll Calculation**: Based on attendance records and hours worked
- **Overtime Management**: 1.5x rate for hours beyond 160 per month
- **Tax & Deductions**: Configurable tax rates and deduction management
- **Bulk Operations**: Mass approval, rejection, and generation
- **Comprehensive Reporting**: Multiple export formats and analytics
- **Role-Based Access**: HR/Admin full access, employees view own records

## Endpoints

### 1. Create Payroll Record

**POST** `/api/payroll/create/`

Create a new payroll record for an employee (HR/Admin only).

**Request Body:**
```json
{
  "user": 1,
  "month": 8,
  "year": 2025,
  "basic_salary": "5000.00",
  "hourly_rate": "25.00",
  "tax_deduction": "500.00",
  "other_deductions": "100.00",
  "status": "pending"
}
```

**Response:**
```json
{
  "message": "Payroll record created successfully",
  "payroll": {
    "id": 1,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "department": "Engineering",
    "position": "Software Developer",
    "month": 8,
    "year": 2025,
    "basic_salary": "5000.00",
    "hourly_rate": "25.00",
    "total_hours_worked": "160.00",
    "regular_hours": "160.00",
    "overtime_hours": "0.00",
    "regular_pay": "4000.00",
    "overtime_pay": "0.00",
    "tax_deduction": "500.00",
    "other_deductions": "100.00",
    "gross_pay": "4000.00",
    "net_pay": "3400.00",
    "status": "pending",
    "approved_by": null,
    "approved_at": null,
    "created_at": "2025-08-27T10:00:00Z",
    "updated_at": "2025-08-27T10:00:00Z"
  }
}
```

**Notes:**
- Automatically calculates hours worked from attendance records
- Calculates regular vs overtime hours (160 hours = regular, beyond = overtime)
- Overtime rate is 1.5x hourly rate
- Only HR and Managers can create payroll records

### 2. Calculate/Recalculate Payroll

**POST** `/api/payroll/calculate/`

Calculate or recalculate payroll for a specific employee and period (HR/Admin only).

**Request Body:**
```json
{
  "user": 1,
  "month": 8,
  "year": 2025,
  "recalculate": false
}
```

**Response:**
```json
{
  "message": "Payroll calculated successfully for John Doe - 8/2025",
  "payroll": {
    "id": 1,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "month": 8,
    "year": 2025,
    "total_hours_worked": "168.00",
    "regular_hours": "160.00",
    "overtime_hours": "8.00",
    "regular_pay": "4000.00",
    "overtime_pay": "300.00",
    "gross_pay": "4300.00",
    "net_pay": "3700.00"
  }
}
```

**Notes:**
- Automatically fetches attendance records for the specified month
- Calculates total hours, regular hours, and overtime hours
- Applies overtime rate (1.5x) for hours beyond 160
- Updates all calculated fields automatically

### 3. Auto-Generate Payroll

**POST** `/api/payroll/auto-generate/`

Automatically generate payroll records for all active employees for a specific month (HR/Admin only).

**Request Body:**
```json
{
  "month": 8,
  "year": 2025
}
```

**Response:**
```json
{
  "message": "Payroll generation completed. 25 records generated.",
  "generated_count": 25,
  "errors": []
}
```

**Notes:**
- Creates payroll records for all active employees
- Skips employees who already have payroll for the specified month
- Automatically calculates based on attendance records
- Returns count of generated records and any errors

### 4. List Payroll Records

**GET** `/api/payroll/list/`

List all payroll records with filtering and search capabilities (HR/Admin only).

**Query Parameters:**
- `user`: Filter by user ID
- `month`: Filter by month (1-12)
- `year`: Filter by year
- `status`: Filter by status (pending, approved, rejected)
- `department`: Filter by user department
- `search`: Search by user name, employee ID, or email
- `ordering`: Order by field (month, year, gross_pay, net_pay, created_at)

**Response:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/payroll/list/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 1,
      "user_name": "John Doe",
      "employee_id": "EMP001",
      "department": "Engineering",
      "position": "Software Developer",
      "month": 8,
      "year": 2025,
      "basic_salary": "5000.00",
      "hourly_rate": "25.00",
      "total_hours_worked": "168.00",
      "regular_hours": "160.00",
      "overtime_hours": "8.00",
      "regular_pay": "4000.00",
      "overtime_pay": "300.00",
      "tax_deduction": "500.00",
      "other_deductions": "100.00",
      "gross_pay": "4300.00",
      "net_pay": "3700.00",
      "status": "pending",
      "approved_by": null,
      "approved_at": null,
      "created_at": "2025-08-27T10:00:00Z",
      "updated_at": "2025-08-27T10:00:00Z"
    }
  ]
}
```

### 5. Payroll Detail

**GET** `/api/payroll/{id}/`

Get detailed information about a specific payroll record (HR/Admin only).

**Response:** Same as individual payroll object above.

**PUT** `/api/payroll/{id}/`

Update payroll record details (HR/Admin only).

**Request Body:**
```json
{
  "basic_salary": "5500.00",
  "hourly_rate": "27.50",
  "tax_deduction": "550.00",
  "other_deductions": "110.00",
  "status": "approved"
}
```

**DELETE** `/api/payroll/{id}/`

Delete payroll record (HR/Admin only).

### 6. Payroll Reports

**GET** `/api/payroll/reports/`

Generate comprehensive payroll reports with filtering and export options (HR/Admin only).

**Query Parameters:**
- `month`: Filter by month (1-12)
- `year`: Filter by year
- `department`: Filter by department
- `status`: Filter by status
- `export_format`: Export format (json, csv, pdf)

**Response (JSON):**
```json
{
  "summary": {
    "total_employees": 25,
    "total_payroll_amount": "87500.00",
    "total_gross_pay": "100000.00",
    "average_salary": "3500.00",
    "total_overtime_pay": "5000.00",
    "total_tax_deductions": "10000.00",
    "total_other_deductions": "2500.00"
  },
  "payroll_records": [...],
  "total_records": 25
}
```

**CSV Export:**
- Automatically downloads CSV file with all payroll data
- Includes headers for all fields
- Suitable for import into Excel or accounting software

### 7. Payroll Summary

**GET** `/api/payroll/summary/`

Get comprehensive payroll summary statistics (HR/Admin only).

**Query Parameters:**
- `month`: Filter by month (1-12)
- `year`: Filter by year
- `department`: Filter by department

**Response:**
```json
{
  "total_employees": 25,
  "total_payroll_amount": "87500.00",
  "average_salary": "3500.00",
  "total_overtime_hours": "120.00",
  "total_overtime_pay": "5000.00",
  "total_tax_deductions": "10000.00",
  "total_other_deductions": "2500.00",
  "department_breakdown": [
    {
      "user__department": "Engineering",
      "count": 10,
      "total": "40000.00",
      "avg": "4000.00"
    },
    {
      "user__department": "Sales",
      "count": 8,
      "total": "28000.00",
      "avg": "3500.00"
    }
  ],
  "status_breakdown": [
    {
      "status": "approved",
      "count": 20,
      "total": "70000.00"
    },
    {
      "status": "pending",
      "count": 5,
      "total": "17500.00"
    }
  ]
}
```

### 8. Bulk Payroll Actions

**POST** `/api/payroll/bulk-actions/`

Perform bulk actions on multiple payroll records (HR/Admin only).

**Request Body:**
```json
{
  "payroll_ids": [1, 2, 3, 4],
  "action": "approve",
  "notes": "Bulk approval for August 2025"
}
```

**Actions Available:**
- `approve`: Approve selected payroll records
- `reject`: Reject selected payroll records
- `delete`: Delete selected payroll records

**Response:**
```json
{
  "message": "4 payroll records approved successfully",
  "updated_count": 4,
  "action": "approve"
}
```

### 9. Payroll Adjustments

**POST** `/api/payroll/adjustments/`

Make adjustments to payroll records (HR/Admin only).

**Request Body:**
```json
{
  "payroll_id": 1,
  "adjustment_type": "bonus",
  "amount": "200.00",
  "reason": "Performance bonus for Q2",
  "approved_by": 2
}
```

**Adjustment Types:**
- `bonus`: Add bonus amount (reduces deductions)
- `deduction`: Add deduction amount
- `correction`: Correct previous calculation
- `other`: Other type of adjustment

**Response:**
```json
{
  "message": "Bonus adjustment applied successfully",
  "payroll": {
    "id": 1,
    "net_pay": "3900.00"
  },
  "adjustment_amount": "200.00",
  "reason": "Performance bonus for Q2"
}
```

### 10. Payroll Comparison

**POST** `/api/payroll/compare/`

Compare payroll between two periods (HR/Admin only).

**Request Body:**
```json
{
  "period1_month": 7,
  "period1_year": 2025,
  "period2_month": 8,
  "period2_year": 2025,
  "user": 1
}
```

**Response:**
```json
{
  "period1": {
    "month": 7,
    "year": 2025,
    "summary": {
      "total_employees": 25,
      "total_payroll": "85000.00",
      "total_gross": "95000.00",
      "total_overtime": "4000.00",
      "avg_salary": "3400.00"
    }
  },
  "period2": {
    "month": 8,
    "year": 2025,
    "summary": {
      "total_employees": 25,
      "total_payroll": "87500.00",
      "total_gross": "100000.00",
      "total_overtime": "5000.00",
      "avg_salary": "3500.00"
    }
  },
  "differences": {
    "total_payroll": "2500.00",
    "total_payroll_pct_change": 2.94,
    "total_overtime": "1000.00",
    "total_overtime_pct_change": 25.0,
    "avg_salary": "100.00",
    "avg_salary_pct_change": 2.94
  }
}
```

### 11. My Payroll (Employee Access)

**GET** `/api/payroll/my-payroll/`

Get current user's payroll records (Employee access).

**Query Parameters:**
- `month`: Filter by month (1-12)
- `year`: Filter by year

**Response:**
```json
{
  "payroll_records": [
    {
      "id": 1,
      "month": 8,
      "year": 2025,
      "basic_salary": "5000.00",
      "total_hours_worked": "168.00",
      "regular_pay": "4000.00",
      "overtime_pay": "300.00",
      "gross_pay": "4300.00",
      "net_pay": "3700.00",
      "status": "approved"
    }
  ],
  "total_records": 1
}
```

## Payroll Calculation Logic

### Hours Calculation
- **Regular Hours**: Up to 160 hours per month (8 hours × 20 working days)
- **Overtime Hours**: Hours beyond 160 per month
- **Total Hours**: Sum of all attendance check-in/out durations

### Pay Calculation
- **Regular Pay**: Regular hours × hourly rate
- **Overtime Pay**: Overtime hours × (hourly rate × 1.5)
- **Gross Pay**: Regular pay + overtime pay
- **Net Pay**: Gross pay - tax deductions - other deductions

### Example Calculation
```
Employee works 168 hours in a month:
- Regular hours: 160
- Overtime hours: 8
- Hourly rate: $25.00

Regular pay: 160 × $25.00 = $4,000.00
Overtime pay: 8 × ($25.00 × 1.5) = $300.00
Gross pay: $4,000.00 + $300.00 = $4,300.00

Tax deduction: $500.00
Other deductions: $100.00
Net pay: $4,300.00 - $500.00 - $100.00 = $3,700.00
```

## Status Values

- **pending**: Payroll created but not yet approved
- **approved**: Payroll approved by HR/Manager
- **rejected**: Payroll rejected (requires correction)

## Permissions

### Employee Role
- Can view own payroll records
- Cannot create, modify, or approve payroll
- Cannot access other employees' payroll

### Manager Role
- All Employee permissions
- Can view team payroll records
- Can create and approve payroll for team members
- Cannot access other departments' payroll

### HR/Admin Role
- All Manager permissions
- Can view all payroll records
- Can create, modify, and approve any payroll
- Can perform bulk operations
- Can generate reports and exports

## Export Formats

### CSV Export
- Comma-separated values format
- Includes all payroll fields
- Suitable for Excel/Google Sheets
- Automatic file download

### PDF Export
- Professional report format
- Summary statistics and detailed records
- Company branding support
- Print-friendly layout

### JSON Export
- API-friendly format
- Includes summary and detailed data
- Suitable for integration with other systems

## Error Responses

### 400 Bad Request
```json
{
  "error": "Payroll record already exists for John Doe - 8/2025. Use recalculate=True to recalculate."
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "Only HR and Managers can create payroll records"
}
```

### 404 Not Found
```json
{
  "error": "Payroll record not found"
}
```

## Example Usage

### Create and calculate payroll
```bash
curl -X POST http://localhost:8000/api/payroll/create/ \
  -H "Authorization: Bearer HR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "month": 8,
    "year": 2025,
    "basic_salary": "5000.00",
    "hourly_rate": "25.00",
    "tax_deduction": "500.00",
    "other_deductions": "100.00"
  }'
```

### Generate payroll report
```bash
curl -X GET "http://localhost:8000/api/payroll/reports/?month=8&year=2025&export_format=csv" \
  -H "Authorization: Bearer HR_ACCESS_TOKEN"
```

### Bulk approve payroll
```bash
curl -X POST http://localhost:8000/api/payroll/bulk-actions/ \
  -H "Authorization: Bearer HR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payroll_ids": [1, 2, 3, 4],
    "action": "approve",
    "notes": "Approved for August 2025"
  }'
```

### Auto-generate payroll for all employees
```bash
curl -X POST http://localhost:8000/api/payroll/auto-generate/ \
  -H "Authorization: Bearer HR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "month": 8,
    "year": 2025
  }'
```

## Testing

Run payroll tests with:
```bash
python manage.py test payroll
```

## Notes

- All monetary values use Decimal for precision
- Hours are calculated from attendance records automatically
- Overtime rate is fixed at 1.5x hourly rate
- Regular hours limit is 160 per month (configurable)
- Tax calculations support custom rates and brackets
- Bulk operations are available for efficiency
- Export formats support different business needs
- Real-time calculations ensure accuracy
- Audit trail tracks all changes and approvals
