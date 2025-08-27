# Employee Attendance Platform - API Endpoints

## Authentication Endpoints

### 1. User Registration
- **POST** `/api/auth/register/`
- **Description**: Register a new user
- **Body**:
  ```json
  {
    "email": "user@company.com",
    "username": "username",
    "employee_id": "EMP001",
    "first_name": "John",
    "last_name": "Doe",
    "role": "employee",
    "phone_number": "+1234567890",
    "department": "IT",
    "position": "Developer",
    "password": "securepassword",
    "password_confirm": "securepassword"
  }
  ```
- **Response**: User data + JWT tokens

### 2. User Login
- **POST** `/api/auth/login/`
- **Description**: Login user and get JWT tokens
- **Body**:
  ```json
  {
    "email": "user@company.com",
    "password": "securepassword"
  }
  ```
- **Response**: JWT tokens + user data

### 3. Token Refresh
- **POST** `/api/auth/refresh/`
- **Description**: Refresh JWT access token
- **Body**:
  ```json
  {
    "refresh": "refresh_token_here"
  }
  ```

## User Profile Endpoints

### 4. Get User Profile
- **GET** `/api/auth/profile/`
- **Description**: Get current user profile
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**: Complete user profile data

### 5. Update User Profile
- **PUT** `/api/auth/profile/`
- **Description**: Update current user profile
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "department": "IT",
    "position": "Senior Developer",
    "profile_picture": "file_upload"
  }
  ```

### 6. Change Password
- **POST** `/api/auth/change-password/`
- **Description**: Change user password
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "old_password": "oldpassword",
    "new_password": "newpassword",
    "new_password_confirm": "newpassword"
  }
  ```

## User Management Endpoints (HR/Admin Only)

### 7. List Users
- **GET** `/api/auth/users/`
- **Description**: List all users (HR/Admin) or self (Employee)
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `role`: Filter by role (employee, hr, manager)
  - `department`: Filter by department
  - `is_active`: Filter by active status
  - `search`: Search by name, employee_id, or email
  - `ordering`: Order by field (created_at, employee_id, first_name)

### 8. Create User
- **POST** `/api/auth/users/create/`
- **Description**: Create new user (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**: Same as registration

### 9. Get User Detail
- **GET** `/api/auth/users/{id}/`
- **Description**: Get specific user details
- **Headers**: `Authorization: Bearer <access_token>`

### 10. Update User
- **PUT** `/api/auth/users/{id}/`
- **Description**: Update user details (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`

### 11. Delete User
- **DELETE** `/api/auth/users/{id}/`
- **Description**: Delete user (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`

### 12. Assign Manager
- **POST** `/api/auth/users/{user_id}/assign-manager/`
- **Description**: Assign manager to user (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "manager_id": 123
  }
  ```

### 13. Toggle User Status
- **POST** `/api/auth/users/{user_id}/toggle-status/`
- **Description**: Activate/deactivate user (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`

### 14. User Statistics
- **GET** `/api/auth/stats/`
- **Description**: Get user statistics (HR/Admin only)
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**:
  ```json
  {
    "total_users": 50,
    "active_users": 48,
    "employees": 45,
    "managers": 3,
    "hr_users": 2
  }
  ```

## User Roles and Permissions

### Employee Role
- Can view and update own profile
- Can change own password
- Can view own data only

### Manager Role
- All Employee permissions
- Can view team members
- Can assign shifts
- Can approve leave requests
- Can manage attendance for team

### HR/Admin Role
- All Manager permissions
- Can create/edit/delete users
- Can view all users and statistics
- Can assign managers
- Can toggle user status
- Full system access

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
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
  "error": "Only HR and Managers can perform this action."
}
```

### 404 Not Found
```json
{
  "error": "User not found."
}
```

## Example Usage

### 1. Register a new user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@company.com",
    "username": "john",
    "employee_id": "EMP001",
    "first_name": "John",
    "last_name": "Doe",
    "role": "employee",
    "password": "securepass123",
    "password_confirm": "securepass123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@company.com",
    "password": "securepass123"
  }'
```

### 3. Get profile (with token)
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. List users (HR only)
```bash
curl -X GET http://localhost:8000/api/auth/users/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## API Documentation

For interactive API documentation, visit:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Schema**: http://localhost:8000/api/schema/
