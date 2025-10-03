import json
from datetime import datetime, date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .forms import *
from .models import *
from .utils import get_attendance_stats


def manager_home(request):
    manager = get_object_or_404(Manager, admin=request.user)
    total_employees = Employee.objects.filter(division=manager.division).count()
    total_leave = LeaveReportManager.objects.filter(manager=manager).count()
    departments = Department.objects.filter(division=manager.division)
    total_department = departments.count()
    total_attendance = Attendance.objects.filter(department__in=departments).count()
    
    # Use utility function for attendance stats
    department_list, attendance_list = get_attendance_stats(departments)
    

    context = {
        'page_title': 'Manager Panel - ' + str(manager.admin.last_name) + ' (' + str(manager.division) + ')',
        'total_employees': total_employees,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_department': total_department,
        'department_list': department_list,
        'attendance_list': attendance_list,
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


# ======================================
# Manager GPS Attendance Views
# ======================================

@login_required
def manager_gps_attendance(request):
    """Manager team GPS attendance dashboard"""
    try:
        manager = get_object_or_404(Manager, admin=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    today = timezone.localdate()
    
    # Get team employees
    team_employees = Employee.objects.filter(division=manager.division)
    
    # Get today's team check-ins
    today_team_checkins = GPSCheckIn.objects.filter(
        employee__in=team_employees,
        check_in_time__date=today
    ).select_related('employee', 'employee__admin').order_by('-check_in_time')
    
    checked_in_count = today_team_checkins.count()
    checked_out_count = today_team_checkins.filter(check_out_time__isnull=False).count()
    total_employees = team_employees.count()
    
    context = {
        'manager': manager,
        'team_employees': team_employees,
        'today_team_checkins': today_team_checkins,
        'checked_in_count': checked_in_count,
        'checked_out_count': checked_out_count,
        'total_employees': total_employees,
        'page_title': 'Team GPS Attendance',
    }
    
    return render(request, 'manager_template/manager_gps_attendance.html', context)


@login_required
def manager_gps_checkin(request):
    """Manager GPS check-in page - Redirect to team dashboard"""
    try:
        manager = get_object_or_404(Manager, admin=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Since managers supervise employees, redirect to team GPS dashboard
    # Managers don't need individual check-in (they oversee team attendance)
    messages.info(request, "As a manager, you oversee team attendance rather than checking in individually. Redirecting to team dashboard.")
    return redirect('manager_gps_dashboard')


@login_required
def manager_gps_checkout(request):
    """Manager GPS check-out page - Redirect to team dashboard"""
    try:
        manager = get_object_or_404(Manager, admin=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Since managers supervise employees, redirect to team GPS dashboard
    # Managers don't need individual check-out (they oversee team attendance)
    messages.info(request, "As a manager, you oversee team attendance rather than checking out individually. Redirecting to team dashboard.")
    return redirect('manager_gps_dashboard')


@login_required
def manager_gps_history(request):
    """Manager GPS attendance history - View team members' GPS check-ins"""
    try:
        manager = get_object_or_404(Manager, admin=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Get team members in manager's division
    team_employees = Employee.objects.filter(division=manager.division)
    
    # Get search parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_filter = request.GET.get('employee_id')
    
    # Get check-ins from database for team members
    checkins = GPSCheckIn.objects.filter(employee__in=team_employees)
    
    # Apply filtering
    if start_date:
        checkins = checkins.filter(check_in_time__date__gte=start_date)
    if end_date:
        checkins = checkins.filter(check_in_time__date__lte=end_date)
    if employee_filter:
        checkins = checkins.filter(employee_id=employee_filter)
    
    checkins = checkins.select_related('employee', 'employee__admin').order_by('-check_in_time')[:50]
    
    context = {
        'manager': manager,
        'team_employees': team_employees,
        'checkins': checkins,
        'start_date': start_date,
        'end_date': end_date,
        'employee_filter': employee_filter,
        'page_title': 'Team GPS Attendance History',
    }
    
    return render(request, 'manager_template/manager_gps_history.html', context)


