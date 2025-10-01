import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .forms import *
from .models import *


def manager_home(request):
    manager = get_object_or_404(Manager, admin=request.user)
    total_employees = Employee.objects.filter(division=manager.division).count()
    total_leave = LeaveReportManager.objects.filter(manager=manager).count()
    departments = Department.objects.filter(division=manager.division)
    total_department = departments.count()
    attendance_list = Attendance.objects.filter(department__in=departments)
    total_attendance = attendance_list.count()
    attendance_list = []
    department_list = []
    for department in departments:
        attendance_count = Attendance.objects.filter(department=department).count()
        department_list.append(department.name)
        attendance_list.append(attendance_count)
    # Team leaderboard (today)
    from datetime import date
    today = date.today()
    team_staff = Employee.objects.filter(division=manager.division)
    team_scores = StaffScoresDaily.objects.filter(date=today, staff__in=team_staff).select_related('staff__admin').order_by('-points')[:10]
    leaderboard = [{
        'name': f"{s.staff.admin.first_name} {s.staff.admin.last_name}",
        'points': s.points
    } for s in team_scores]

    context = {
        'page_title': 'Manager Panel - ' + str(manager.admin.last_name) + ' (' + str(manager.division) + ')',
        'total_employees': total_employees,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_department': total_department,
        'department_list': department_list,
        'attendance_list': attendance_list,
        'leaderboard': leaderboard
    }
    return render(request, 'manager_template/home_content.html', context)


def manager_take_attendance(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'departments': departments,
        'page_title': 'Take Attendance'
    }

    return render(request, 'manager_template/manager_take_attendance.html', context)


@csrf_exempt
def get_employees(request):
    department_id = request.POST.get('department')
    try:
        department = get_object_or_404(Department, id=department_id)
        employees = Employee.objects.filter(division_id=department.division.id)
        employee_data = []
        for employee in employees:
            data = {
                "id": employee.id,
                "name": employee.admin.last_name + " " + employee.admin.first_name
            }
            employee_data.append(data)
        return JsonResponse(json.dumps(employee_data), content_type='application/json', safe=False)
    except Exception as e:
        return e



@csrf_exempt
def save_attendance(request):
    employee_data = request.POST.get('employee_ids')
    date = request.POST.get('date')
    department_id = request.POST.get('department')
    employees = json.loads(employee_data)
    try:
        department = get_object_or_404(Department, id=department_id)

        # Check if an attendance object already exists for the given date
        attendance, created = Attendance.objects.get_or_create(department=department, date=date)

        for employee_dict in employees:
            employee = get_object_or_404(Employee, id=employee_dict.get('id'))

            # Check if an attendance report already exists for the employee and the attendance object
            attendance_report, report_created = AttendanceReport.objects.get_or_create(employee=employee, attendance=attendance)

            # Update the status only if the attendance report was newly created
            if report_created:
                attendance_report.status = employee_dict.get('status')
                attendance_report.save()

    except Exception as e:
        return None

    return HttpResponse("OK")


def manager_update_attendance(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'departments': departments,
        'page_title': 'Update Attendance'
    }

    return render(request, 'manager_template/manager_update_attendance.html', context)


@csrf_exempt
def get_employee_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        employee_data = []
        for attendance in attendance_data:
            data = {"id": attendance.employee.admin.id,
                    "name": attendance.employee.admin.last_name + " " + attendance.employee.admin.first_name,
                    "status": attendance.status}
            employee_data.append(data)
        return JsonResponse(json.dumps(employee_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    employee_data = request.POST.get('employee_ids')
    date = request.POST.get('date')
    employees = json.loads(employee_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for employee_dict in employees:
            employee = get_object_or_404(
                Employee, admin_id=employee_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, employee=employee, attendance=attendance)
            attendance_report.status = employee_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def manager_apply_leave(request):
    form = LeaveReportManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportManager.objects.filter(manager=manager),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('manager_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_apply_leave.html", context)


def manager_feedback(request):
    form = FeedbackManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackManager.objects.filter(manager=manager),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('manager_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_feedback.html", context)


def manager_view_profile(request):
    manager = get_object_or_404(Manager, admin=request.user)
    form = ManagerEditForm(request.POST or None, request.FILES or None,instance=manager)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = manager.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                manager.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('manager_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "manager_template/manager_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "manager_template/manager_view_profile.html", context)

    return render(request, "manager_template/manager_view_profile.html", context)


@csrf_exempt
def manager_fcmtoken(request):
    token = request.POST.get('token')
    try:
        manager_user = get_object_or_404(CustomUser, id=request.user.id)
        manager_user.fcm_token = token
        manager_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def manager_view_notification(request):
    manager = get_object_or_404(Manager, admin=request.user)
    notifications = NotificationManager.objects.filter(manager=manager)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "manager_template/manager_view_notification.html", context)


def manager_add_salary(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'page_title': 'Salary Upload',
        'departments': departments
    }
    if request.method == 'POST':
        try:
            employee_id = request.POST.get('employee_list')
            department_id = request.POST.get('department')
            base = request.POST.get('base')
            ctc = request.POST.get('ctc')
            employee = get_object_or_404(Employee, id=employee_id)
            department = get_object_or_404(Department, id=department_id)
            try:
                data = EmployeeSalary.objects.get(
                    employee=employee, department=department)
                data.ctc = ctc
                data.base = base
                data.save()
                messages.success(request, "Scores Updated")
            except:
                salary = EmployeeSalary(employee=employee, department=department, base=base, ctc=ctc)
                salary.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "manager_template/manager_add_salary.html", context)


@csrf_exempt
def fetch_employee_salary(request):
    try:
        department_id = request.POST.get('department')
        employee_id = request.POST.get('employee')
        employee = get_object_or_404(Employee, id=employee_id)
        department = get_object_or_404(Department, id=department_id)
        salary = EmployeeSalary.objects.get(employee=employee, department=department)
        salary_data = {
            'ctc': salary.ctc,
            'base': salary.base
        }
        return HttpResponse(json.dumps(salary_data))
    except Exception as e:
        return HttpResponse('False')


def manager_gps_attendance_dashboard(request):
    """GPS attendance dashboard for managers to see employee attendance"""
    if request.user.user_type != '2':  # Only managers can access
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    manager = get_object_or_404(Manager, admin=request.user)
    
    # Get today's date
    from django.utils import timezone
    today = timezone.localdate()
    
    # Get departments under this manager's division
    departments = Department.objects.filter(division=manager.division)
    
    # Get employees under manager's departments
    employees = Employee.objects.filter(department__in=departments).select_related('admin', 'department')
    
    # Get today's individual employee attendance records
    try:
        today_attendance = EmployeeGPSAttendance.objects.filter(
            employee__in=employees,
            date=today
        ).select_related('employee__admin', 'employee__department')
    except Exception:
        # Fallback if table doesn't exist yet
        today_attendance = []
    
    # Create attendance status for each employee
    employee_attendance = []
    for employee in employees:
        # Get individual employee attendance
        attendance = None
        if today_attendance:
            attendance = next((att for att in today_attendance if att.employee == employee), None)
        
        status = 'Not Marked'
        check_in_time = None
        check_out_time = None
        check_in_location = None
        check_out_location = None
        hours_worked = None
        
        if attendance:
            if attendance.checkin_time:
                status = 'Checked In'
                check_in_time = attendance.checkin_time
                check_in_location = attendance.checkin_gps
                
                if attendance.checkout_time:
                    status = 'Checked Out'
                    check_out_time = attendance.checkout_time
                    check_out_location = attendance.checkout_gps
                    
                    # Calculate hours worked
                    hours_worked = attendance.hours_worked
        
        employee_attendance.append({
            'employee': employee,
            'status': status,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'check_in_location': check_in_location,
            'check_out_location': check_out_location,
            'hours_worked': hours_worked,
            'attendance': attendance
        })
    
    # Calculate summary statistics
    total_employees = len(employee_attendance)
    checked_in = len([ea for ea in employee_attendance if ea['status'] in ['Checked In', 'Checked Out']])
    checked_out = len([ea for ea in employee_attendance if ea['status'] == 'Checked Out'])
    not_marked = total_employees - checked_in
    
    context = {
        'page_title': 'GPS Attendance Dashboard',
        'manager': manager,
        'employee_attendance': employee_attendance,
        'departments': departments,
        'today': today,
        'total_employees': total_employees,
        'checked_in': checked_in,
        'checked_out': checked_out,
        'not_marked': not_marked,
    }
    return render(request, 'manager_template/gps_attendance_dashboard.html', context)


def manager_mark_attendance(request):
    """Manager self-attendance marking page"""
    if request.user.user_type != '2':  # Only managers can access
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    try:
        # Get or create manager profile
        manager, created = Manager.objects.get_or_create(
            admin=request.user,
            defaults={'division': None}
        )
        
        # Get or create employee profile for manager
        from .views import get_or_create_employee_profile
        employee = get_or_create_employee_profile(request.user)
        
        # Get today's attendance if exists
        today = timezone.now().date()
        today_attendance = None
        
        if employee:
            try:
                # Try to get EmployeeGPSAttendance if it exists
                from .models import EmployeeGPSAttendance
                today_attendance = EmployeeGPSAttendance.objects.filter(
                    employee=employee, 
                    date=today
                ).first()
            except Exception as e:
                print(f"Error getting EmployeeGPSAttendance: {e}")
                # Fallback to regular Attendance model
                try:
                    from .models import Attendance
                    today_attendance = Attendance.objects.filter(
                        employee=employee,
                        attendance_date=today
                    ).first()
                except Exception as e2:
                    print(f"Error getting Attendance: {e2}")
                    today_attendance = None
        
        context = {
            'page_title': 'Mark My Attendance',
            'manager': manager,
            'today_attendance': today_attendance,
            'today': today,
            'employee': employee,
        }
        
        return render(request, 'manager_template/manager_mark_attendance.html', context)
        
    except Exception as e:
        print(f"Error in manager_mark_attendance: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('login_page')


def manager_checkin(request):
    """Handle manager check-in using form submission with success messages"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('manager_mark_attendance')
    
    if not request.user.is_authenticated:
        messages.error(request, "User not authenticated.")
        return redirect('login_page')
    
    if request.user.user_type != '2':
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    try:
        # Get GPS data from POST
        gps_location = request.POST.get('gps', '')
        
        # Get or create employee profile
        from .views import get_or_create_employee_profile
        employee = get_or_create_employee_profile(request.user)
        
        if not employee:
            messages.error(request, "Could not create employee profile. Please contact system administrator.")
            return redirect('manager_mark_attendance')
        
        # Create attendance record directly
        today = timezone.now().date()
        current_time = timezone.now()
        
        from .models import EmployeeGPSAttendance
        
        # Check if already checked in today
        existing_attendance = EmployeeGPSAttendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if existing_attendance and existing_attendance.checkin_time:
            messages.warning(request, f"You have already checked in today at {existing_attendance.checkin_time.strftime('%H:%M:%S')}!")
            return redirect('manager_mark_attendance')
        
        # Create or update attendance record
        if existing_attendance:
            existing_attendance.checkin_time = current_time
            existing_attendance.checkin_gps = gps_location
            existing_attendance.save()
        else:
            EmployeeGPSAttendance.objects.create(
                employee=employee,
                date=today,
                checkin_time=current_time,
                checkin_gps=gps_location
            )
        
        messages.success(request, f"Successfully checked in at {current_time.strftime('%H:%M:%S')} with GPS location!")
        
    except Exception as e:
        print(f"Manager checkin error: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Check-in failed: {str(e)}")
    
    return redirect('manager_mark_attendance')


def manager_checkout(request):
    """Handle manager check-out using form submission with success messages"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('manager_mark_attendance')
    
    if not request.user.is_authenticated:
        messages.error(request, "User not authenticated.")
        return redirect('login_page')
    
    if request.user.user_type != '2':
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    try:
        # Get data from POST
        gps_location = request.POST.get('gps', '')
        work_notes = request.POST.get('notes', '')
        
        # Get or create employee profile
        from .views import get_or_create_employee_profile
        employee = get_or_create_employee_profile(request.user)
        
        if not employee:
            messages.error(request, "Could not create employee profile. Please contact system administrator.")
            return redirect('manager_mark_attendance')
        
        # Update attendance record directly
        today = timezone.now().date()
        current_time = timezone.now()
        
        from .models import EmployeeGPSAttendance
        
        # Get today's attendance
        attendance = EmployeeGPSAttendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if not attendance or not attendance.checkin_time:
            messages.error(request, "You must check in first before checking out.")
            return redirect('manager_mark_attendance')
        
        if attendance.checkout_time:
            messages.warning(request, f"You have already checked out today at {attendance.checkout_time.strftime('%H:%M:%S')}!")
            return redirect('manager_mark_attendance')
        
        # Update checkout details
        attendance.checkout_time = current_time
        attendance.checkout_gps = gps_location
        attendance.work_notes = work_notes
        attendance.save()
        
        messages.success(request, f"Successfully checked out at {current_time.strftime('%H:%M:%S')}! Total hours worked: {attendance.hours_worked:.2f}")
        
    except Exception as e:
        print(f"Manager checkout error: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Check-out failed: {str(e)}")
    
    return redirect('manager_mark_attendance')


def manager_live_gps_map(request):
    """Manager Live GPS Map - Shows their direct reports and themselves"""
    if request.user.user_type != '2':  # Only Manager can access
        messages.error(request, "Access denied. Manager access required.")
        return redirect('manager_home')
    
    context = {
        'page_title': 'Live GPS Map - My Team'
    }
    return render(request, 'manager_template/live_gps_map.html', context)


@csrf_exempt
def manager_gps_data_api(request):
    """API endpoint for Manager to fetch GPS data of their team"""
    if request.user.user_type != '2':  # Only Manager can access
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from datetime import date
        today = date.today()
        
        # Get manager's department
        manager = Manager.objects.get(admin=request.user)
        manager_department = manager.admin.employee.department if hasattr(manager.admin, 'employee') else None
        
        gps_data = []
        
        # Add manager's own location if they have GPS attendance
        try:
            if hasattr(manager.admin, 'employee'):
                manager_attendance = EmployeeGPSAttendance.objects.filter(
                    employee=manager.admin.employee,
                    date=today,
                    checkin_gps__isnull=False
                ).order_by('-checkin_time').first()
                
                if manager_attendance and manager_attendance.checkin_gps:
                    coords = manager_attendance.checkin_gps.split(',')
                    if len(coords) == 2:
                        lat = float(coords[0].strip())
                        lng = float(coords[1].strip())
                        
                        gps_data.append({
                            'user_id': manager.admin.id,
                            'name': f"{manager.admin.first_name} {manager.admin.last_name}",
                            'role': 'Manager',
                            'lat': lat,
                            'lng': lng,
                            'marker_color': 'yellow',
                            'last_seen': manager.admin.last_seen.isoformat() if manager.admin.last_seen else None,
                            'checkin_time': manager_attendance.checkin_time.isoformat() if manager_attendance.checkin_time else None,
                            'is_online': manager.admin.is_online
                        })
        except Exception as e:
            print(f"Error getting manager GPS data: {e}")
        
        # Get employees in manager's department who are online and recently active
        if manager_department:
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(minutes=10)
            
            employees = Employee.objects.filter(
                department=manager_department,
                admin__is_online=True,
                admin__last_seen__gte=recent_threshold  # Only users active within last 10 minutes
            ).select_related('admin')
            
            for employee in employees:
                try:
                    latest_attendance = EmployeeGPSAttendance.objects.filter(
                        employee=employee,
                        date=today,
                        checkin_gps__isnull=False
                    ).order_by('-checkin_time').first()
                    
                    if latest_attendance and latest_attendance.checkin_gps:
                        coords = latest_attendance.checkin_gps.split(',')
                        if len(coords) == 2:
                            lat = float(coords[0].strip())
                            lng = float(coords[1].strip())
                            
                            gps_data.append({
                                'user_id': employee.admin.id,
                                'name': f"{employee.admin.first_name} {employee.admin.last_name}",
                                'role': 'Employee',
                                'lat': lat,
                                'lng': lng,
                                'marker_color': 'green',
                                'last_seen': employee.admin.last_seen.isoformat() if employee.admin.last_seen else None,
                                'checkin_time': latest_attendance.checkin_time.isoformat() if latest_attendance.checkin_time else None,
                                'is_online': employee.admin.is_online
                            })
                except (ValueError, IndexError) as e:
                    print(f"Error parsing GPS coordinates for employee {employee.id}: {e}")
                    continue
        
        return JsonResponse({
            'success': True,
            'data': gps_data,
            'count': len(gps_data)
        })
        
    except Exception as e:
        print(f"Error in manager_gps_data_api: {e}")
        return JsonResponse({'error': 'Failed to fetch GPS data'}, status=500)
