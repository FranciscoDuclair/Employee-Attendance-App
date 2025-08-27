# Employee Attendance Platform with Face Recognition

A comprehensive Django-based employee attendance management system with face recognition capabilities.

## 🚀 Project Overview

This platform provides:
- **Face Recognition Attendance**: Check-in/out using facial recognition
- **User Management**: Role-based access (Employee, HR/Admin, Team Manager)
- **Payroll Management**: Automated salary calculations based on attendance
- **Leave Management**: Request and approval system
- **Shift Scheduling**: Flexible shift management
- **Notifications**: Real-time notifications system
- **Reports & Analytics**: Comprehensive reporting dashboard

## 🛠️ Technology Stack

- **Backend**: Django 5.2.5 with Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: JWT tokens with SimpleJWT
- **API Documentation**: Swagger/OpenAPI with drf-spectacular
- **Face Recognition**: OpenCV + face_recognition libraries
- **Frontend**: React Native with Expo (mobile) + React.js (web admin)

## 📁 Project Structure

```
attendance_platform/
├── attendance_platform/          # Main Django project
│   ├── settings.py              # Django settings
│   ├── urls.py                  # Main URL configuration
│   └── wsgi.py                  # WSGI configuration
├── users/                       # User management app
│   ├── models.py                # Custom User model
│   ├── urls.py                  # User-related URLs
│   └── views.py                 # User views (to be implemented)
├── attendance/                  # Attendance tracking app
│   ├── models.py                # Attendance models
│   ├── urls.py                  # Attendance URLs
│   └── views.py                 # Attendance views (to be implemented)
├── payroll/                     # Payroll management app
│   ├── models.py                # Payroll models
│   ├── urls.py                  # Payroll URLs
│   └── views.py                 # Payroll views (to be implemented)
├── leave/                       # Leave management app
│   ├── models.py                # Leave models
│   ├── urls.py                  # Leave URLs
│   └── views.py                 # Leave views (to be implemented)
├── shifts/                      # Shift scheduling app
│   ├── models.py                # Shift models
│   ├── urls.py                  # Shift URLs
│   └── views.py                 # Shift views (to be implemented)
├── notifications/               # Notifications app
│   ├── models.py                # Notification models
│   ├── urls.py                  # Notification URLs
│   └── views.py                 # Notification views (to be implemented)
├── requirements.txt             # Python dependencies
└── manage.py                    # Django management script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/FranciscoDuclair/Employee-Attendance-App.git
   cd Employee-Attendance-App
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - API Documentation: http://localhost:8000/api/docs/
   - Admin Panel: http://localhost:8000/admin/

## 📊 Database Models

### User Model
- Custom user model extending Django's AbstractUser
- Role-based permissions (Employee, HR/Admin, Team Manager)
- Face encoding storage for recognition
- Employee ID, department, position tracking

### Attendance Model
- Check-in/out tracking with timestamps
- Face recognition verification
- Manual override capabilities
- Location tracking (optional)
- Status tracking (Present, Late, Absent, Half Day)

### Payroll Model
- Monthly payroll calculations
- Hourly rate and salary tracking
- Overtime calculations
- Tax and deduction management
- Approval workflow

### Leave Management
- Leave types configuration
- Leave request workflow
- Balance tracking
- Approval system

### Shift Management
- Shift definitions
- Schedule management
- Template-based recurring shifts
- Conflict prevention

### Notifications
- Real-time notification system
- Template-based notifications
- Priority levels
- Read/unread tracking

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Face Recognition Setup
The system uses OpenCV and face_recognition libraries. For production deployment, you may need to install additional dependencies:
```bash
# For face_recognition (requires CMake on Windows)
pip install cmake
pip install dlib
pip install face_recognition
```

## 📱 API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/refresh/` - Token refresh
- `POST /api/auth/logout/` - User logout

### Attendance
- `POST /api/attendance/check-in/` - Check in with face recognition
- `POST /api/attendance/check-out/` - Check out
- `GET /api/attendance/history/` - Attendance history
- `GET /api/attendance/reports/` - Attendance reports

### Payroll
- `GET /api/payroll/` - Payroll records
- `POST /api/payroll/generate/` - Generate payroll
- `GET /api/payroll/reports/` - Payroll reports

### Leave
- `GET /api/leave/requests/` - Leave requests
- `POST /api/leave/request/` - Submit leave request
- `PUT /api/leave/approve/{id}/` - Approve leave request

### Shifts
- `GET /api/shifts/` - Shift schedules
- `POST /api/shifts/create/` - Create shift
- `PUT /api/shifts/assign/` - Assign shift to employee

### Notifications
- `GET /api/notifications/` - User notifications
- `PUT /api/notifications/{id}/read/` - Mark as read

## 🧪 Testing

Run tests with:
```bash
python manage.py test
```

## 📈 Development Status

### ✅ Completed (Step 1)
- [x] Django project setup
- [x] App structure creation
- [x] Database models design
- [x] Basic configuration
- [x] URL routing setup

### 🚧 In Progress
- [ ] Step 2: User & Role Management
- [ ] Step 3: Attendance Tracking with Face Recognition
- [ ] Step 4: Payroll Management
- [ ] Step 5: Leave Management
- [ ] Step 6: Shift Scheduling
- [ ] Step 7: Notifications System
- [ ] Step 8: Reports & Analytics
- [ ] Step 9: Frontend Development
- [ ] Step 10: Deployment & Documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support and questions, please contact the development team or create an issue in the repository.

---

**Note**: This is a development version. Face recognition features require additional setup and may need CMake and other system dependencies for full functionality.