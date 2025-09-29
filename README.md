## Table of Contents

1. [Introduction](#axpect-technologies-workforce-productivity-suite)
   - [What's New](#whats-new)
   - [Deployed Website](#deployed-website)
   - [Default Credentials](#default-credentials)
2. [Features](#features)
   - [CEO Features](#ceo-can)
   - [Manager Features](#manager-can)
   - [Employee Features](#employee-can)
3. [Screenshots](#screenshots)
4. [Installation](#installation)
5. [Technical Details](#technical-details)
6. [Contributions](#contributions)
7. [License](#license)

# Axpect Technologies: Workforce Productivity Suite

**Axpect Technologies** is a comprehensive Workforce Productivity Suite built with Django, designed to streamline HR and office management processes within your organization. This modern web application empowers CEOs, Managers, and Employees to efficiently manage various aspects of human resources, including employee information, attendance tracking, performance feedback, and leave management.

## What's New

🎉 **Recently Updated (September 2025)**
- ✅ **Complete System Refresh**: Fresh database and clean migrations for optimal performance
- ✅ **Enhanced Branding**: Updated to "Axpect Technologies" throughout the application
- ✅ **Improved Login System**: Streamlined authentication without reCAPTCHA complications
- ✅ **New Test Accounts**: Ready-to-use credentials for immediate testing
- ✅ **Bug Fixes**: Resolved routing and dependency issues for smoother operation
- ✅ **Better Documentation**: Updated installation and setup instructions

## Deployed Website

You can access the deployed Axpect Technologies website at [axpect_technologies.onrender.com](https://axpect_technologies.onrender.com/).

## Default Credentials

🔑 **Updated Test Accounts (September 2025)**

**CEO/Admin Access:**
- Email: `admin@axpecttech.com`
- Password: `admin123`
- Role: Full system administrator with all permissions

**Manager Access:**
- Email: `manager@axpecttech.com`
- Password: `manager123`
- Role: Department management and employee oversight

**Employee Access:**
- Email: `employee@axpecttech.com`
- Password: `employee123`
- Role: Personal dashboard with limited access

> 💡 **Note**: These are fresh test accounts created with the latest system update. All accounts are fully functional and ready for testing.

## Features

### CEO Can:

- **Manage Your Team:** CEOs have full control to add, update, and remove Managers and Employees within the organization.

- **Organize Company Structure:** CEOs can create and manage Divisions and Departments to structure the company efficiently.

- **Track Employee Attendance:** Monitor employee attendance to ensure a productive workforce.

- **Engage with Feedback:** Review and respond to feedback from both employees and managers to foster a collaborative workplace.

- **Manage Leave Requests:** Approve or reject leave requests from Managers and Employees, ensuring operational continuity.

### Manager Can:

- **Maintain Attendance:** Managers can record and update employee attendance, making it easier to track team productivity.

- **Handle Salaries:** Add or update salary information for employees, streamlining payroll processes.

- **Apply for Leave:** Managers can request time off and have it reviewed by the CEO.

- **Communicate with CEO:** Managers can share feedback and important information directly with the CEO.

### Employee Can:

- **Check Attendance:** Employees can view their attendance records to stay on top of their work hours.

- **Access Salary Information:** Check salary details for transparency and financial planning.

- **Request Leave:** Submit leave requests to the CEO, ensuring seamless time-off management.

- **Connect with CEO:** Employees can provide feedback and share important concerns with the CEO, fostering a culture of open communication.

## Screenshots

| CEO                                        | Manager                                         | Employee                                     |
|:------------------------------------------:|:-----------------------------------------------:|:--------------------------------------------:|
| ![CEO_Home](/visuals/ss/CEO_Home.png) | ![Manager_Home](/visuals/ss/Manager_Home.png) | ![Employee_Home](/visuals/ss/Employee_Home.png)   |
| DashBoard                           | DashBoard                            | DashBoard                              |
| ![CEO_ManageEmployee](/visuals/ss/CEO_ManageEmployee.png) | ![Manager_AddSalary](/visuals/ss/Manager_AddSalary.png) | ![Employee_ViewSalary](/visuals/ss/Employee_ViewSalary.png)   |
| Manage Employee                            | Add Salary                            | View Salary                             |
| ![CEO_ManageManager](/visuals/ss/CEO_ManageManager.png) | ![Manager_TakeAttendance](/visuals/ss/Manager_TakeAttendance.png) | ![Employee_EditProfile](/visuals/ss/Employee_EditProfile.png)   |
| Manage Manager                            | Take Attendance                            | Edit Profile      
| ![CEO_EmployeeLeave](/visuals/ss/CEO_EmployeeLeave.png) | ![Manager_ViewAttendance](/visuals/ss/Manager_ViewAttendance.png) | ![Employee_Attendence](/visuals/ss/Employee_Attendence.png)   |
| Leave Application Reply                           | Update Attendance                            | View Attendance                             |
| ![CEO_ManagerLeave](/visuals/ss/CEO_ManagerLeave.png) | ![Manager_ApplyForLeave](/visuals/ss/Manager_ApplyForLeave.png) | ![Employee_ApplyForLeave](/visuals/ss/Employee_ApplyForLeave.png)   |
| Leave Application Response                           | Apply For Leave                           | Apply For Leave                             |
| ![CEO_EmployeeFeedbackReply](/visuals/ss/CEO_EmployeeFeedbackReply.png) | ![Manager_Feedback](/visuals/ss/Manager_Feedback.png) | ![Employee_Feedback](/visuals/ss/Employee_Feedback.png)   |
| Feedback                            | Feedback                            | Feedback                             |
| ![CEO_NotifyManager](/visuals/ss/CEO_NotifyManager.png) | ![Manager_Notification](/visuals/ss/Manager_Notification.png) | ![Employee_Notification](/visuals/ss/Employee_Notification.png)   |
| Send Notification                            | View Notification                            | View Notification                            |

## Installation

### Prerequisites
- Python 3.8+ (tested with Python 3.13)
- Git
- Virtual environment support

### Quick Start

1. **Clone the repository:**
```bash
git clone <repository-url>
cd axpect_tech
```

2. **Create and activate virtual environment:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration:**
Create a `.env` file in the project root (or rename `.env.example`):
```env
SECRET_KEY="your-secret-key-here"
DATABASE_URL="sqlite:///db.sqlite3"  # For local development
# DATABASE_URL="postgres://USER:PASSWORD@localhost:5432/DB_NAME"  # For PostgreSQL
EMAIL_ADDRESS="your-email@gmail.com"  # Optional: for email notifications
EMAIL_PASSWORD="your-app-password"    # Optional: Gmail app password
```

5. **Database Setup:**
```bash
# Create fresh migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

6. **Create Test Users (Recommended):**
The system includes pre-configured test users. They will be created automatically on first run.

*Alternatively, create a custom superuser:*
```bash
python manage.py createsuperuser
```

7. **Start Development Server:**
```bash
python manage.py runserver
```

8. **Access the Application:**
- Open your browser to `http://127.0.0.1:8000/`
- Use the [Default Credentials](#default-credentials) to log in
- Explore different user roles and features

### Troubleshooting

**Common Issues:**
- **Login Issues**: Make sure you're using the updated credentials from the [Default Credentials](#default-credentials) section
- **Static Files**: Run `python manage.py collectstatic` if static files aren't loading
- **Database Issues**: Delete `db.sqlite3` and re-run migrations for a fresh start
- **Port Conflicts**: Use `python manage.py runserver 8001` to run on a different port

## Technical Details

### Built With
- **Backend**: Django 5.2.6
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Bootstrap 4, AdminLTE 3
- **Authentication**: Custom email-based authentication
- **Notifications**: Firebase Cloud Messaging (FCM)

### Project Structure
```
axpect_tech/
├── axpect_tech_config/     # Django project configuration
│   ├── settings.py         # Main settings file
│   ├── urls.py             # URL routing
│   └── wsgi.py             # WSGI configuration
├── main_app/               # Core application
│   ├── models.py           # Database models
│   ├── views.py            # View logic
│   ├── templates/          # HTML templates
│   └── static/             # Static files (CSS, JS, images)
├── media/                  # User uploaded files
├── requirements.txt        # Python dependencies
└── manage.py               # Django management script
```

### Key Features
- **Role-Based Access Control**: Three distinct user types with specific permissions
- **Real-Time Notifications**: Firebase integration for instant updates
- **Responsive Design**: Mobile-friendly interface
- **Email Backend**: Custom email authentication system
- **Data Export**: Attendance and salary reporting capabilities
- **User-Friendly Interface**: Intuitive navigation and clear UI design

## License

This project is licensed under the [MIT License](LICENSE.txt) - see the LICENSE file for details.

---

**Axpect Technologies** - Empowering organizations with efficient workforce management solutions. 🚀
