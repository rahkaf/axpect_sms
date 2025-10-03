import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from django.contrib.auth.decorators import login_required


def employee_home(request):
    employee = get_object_or_404(Employee, admin=request.user)
    total_department = Department.objects.filter(division=employee.division).count()
    total_attendance = AttendanceReport.objects.filter(employee=employee).count()
    total_present = AttendanceReport.objects.filter(employee=employee, status=True).count()
    if total_attendance == 0:  # Don't divide. DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    department_name = []
    data_present = []
    data_absent = []
    departments = Department.objects.filter(division=employee.division)
    for department in departments:
        attendance = Attendance.objects.filter(department=department)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, employee=employee).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, employee=employee).count()
        department_name.append(department.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    
    # Get today's individual GPS attendance data
    from django.utils import timezone
    today = timezone.localdate()
    # Mock GPS attendance data until GPS models are created
    today_attendance = None
    
    # Get task statistics
    try:
        total_tasks = EmployeeTask.objects.filter(employee=employee).count()
        completed_tasks = EmployeeTask.objects.filter(employee=employee, status='completed').count()
        pending_tasks = EmployeeTask.objects.filter(employee=employee, status__in=['assigned', 'in_progress']).count()
        overdue_tasks = EmployeeTask.objects.filter(
            employee=employee, 
            status__in=['assigned', 'in_progress'],
            due_date__lt=today
        ).count()
    except Exception:
        total_tasks = completed_tasks = pending_tasks = overdue_tasks = 0
    
    # Get recent performance ratings (mock data until GPS models are created)
    recent_ratings = []
    avg_rating = 0
    
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_department': total_department,
        'departments': departments,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': department_name,
        'page_title': 'Employee Homepage',
        'employee': employee,
        'today_attendance': today_attendance,
        # Task statistics
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'overdue_tasks': overdue_tasks,
        # Performance ratings
        'recent_ratings': recent_ratings,
        'avg_rating': round(avg_rating, 1),

    }
    return render(request, 'employee_template/home_content.html', context)


@ csrf_exempt
def employee_view_attendance(request):
    employee = get_object_or_404(Employee, admin=request.user)
    if request.method != 'POST':
        division = get_object_or_404(Division, id=employee.division.id)
        context = {
            'departments': Department.objects.filter(division=division),
            'page_title': 'View Attendance'
        }
        return render(request, 'employee_template/employee_view_attendance.html', context)
    else:
        department_id = request.POST.get('department')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            department = get_object_or_404(Department, id=department_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), department=department)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, employee=employee)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def employee_apply_leave(request):
    form = LeaveReportEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportEmployee.objects.filter(employee=employee),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('employee_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_apply_leave.html", context)


def employee_feedback(request):
    form = FeedbackEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackEmployee.objects.filter(employee=employee),
        'page_title': 'Employee Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('employee_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_feedback.html", context)


def employee_view_profile(request):
    employee = get_object_or_404(Employee, admin=request.user)
    form = EmployeeEditForm(request.POST or None, request.FILES or None,
                           instance=employee)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = employee.admin
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
                employee.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('employee_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "employee_template/employee_view_profile.html", context)


@csrf_exempt
def employee_fcmtoken(request):
    token = request.POST.get('token')
    employee_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        employee_user.fcm_token = token
        employee_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def employee_view_notification(request):
    employee = get_object_or_404(Employee, admin=request.user)
    notifications = NotificationEmployee.objects.filter(employee=employee)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "employee_template/employee_view_notification.html", context)


def employee_view_salary(request):
    employee = get_object_or_404(Employee, admin=request.user)
    salarys = EmployeeSalary.objects.filter(employee=employee)
    context = {
        'salarys': salarys,
        'page_title': "View Salary"
    }
    return render(request, "employee_template/employee_view_salary.html", context)


@login_required
def employee_targets(request):
    if not hasattr(request.user, 'employee'):
        return redirect('employee_home')
    # fetch via ORM for server-render
    emp = request.user.employee
    from django.utils import timezone
    today = timezone.localdate()
    period = f"{today.year}-{today.month:02d}"
    tgt = Targets.objects.filter(staff=emp, period=period).first()
    start = today.replace(day=1)
    # Mock scores data until GPS models are created
    progress = {
        'jobs_completed': 0,
        'orders_count': 0,
        'bales_total': 0,
        'payments_count': 0,
        'points': 0,
    }
    context = {
        'page_title': 'My Targets',
        'period': period,
        'tgt': tgt,
        'progress': progress,
    }
    return render(request, 'employee_template/targets.html', context)


@login_required
def employee_jobcards(request):
    if not hasattr(request.user, 'employee'):
        return redirect('employee_home')
    qs = JobCard.objects.filter(assigned_to=request.user.employee).select_related('customer', 'city').order_by('due_at')
    context = {
        'page_title': 'My JobCards',
        'jobcards': qs
    }
    return render(request, 'employee_template/jobcards_list.html', context)


@login_required
def order_create(request, jobcard_id=None):
    if not hasattr(request.user, 'employee'):
        return redirect('employee_home')
    jobcard = JobCard.objects.filter(id=jobcard_id).first() if jobcard_id else None
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer_id') or (jobcard.customer_id if jobcard else None)
            order_date = request.POST.get('order_date') or datetime.now().date().isoformat()
            items_json = request.POST.get('items_json')  # expects JSON array [{item_id, cut, rate, qty_bales}]
            items = json.loads(items_json) if items_json else []
            order = Order.objects.create(
                customer_id=customer_id,
                order_date=order_date,
                created_by_staff=request.user.employee,
                status='CONFIRMED'
            )
            total_bales = 0
            total_amount = 0
            for it in items:
                qty = float(it.get('qty_bales') or 0)
                rate = float(it.get('rate') or 0)
                amt = qty * rate
                OrderItem.objects.create(
                    order=order,
                    item_id=it.get('item_id'),
                    cut=it.get('cut', ''),
                    rate=rate,
                    qty_bales=qty,
                    amount=amt,
                )
                total_bales += qty
                total_amount += amt
            order.total_bales = total_bales
            order.total_amount = total_amount
            order.save()

            # scoring system disabled until StaffScoresDaily model is created
            pass

            # optional: complete jobcard if provided
            if jobcard and jobcard.status != 'COMPLETED':
                jobcard.status = 'COMPLETED'
                jobcard.save(update_fields=['status', 'updated_at'])

            messages.success(request, "Order saved")
            return redirect('employee_jobcards')
        except Exception as e:
            messages.error(request, f"Failed to save order: {e}")
    context = {
        'page_title': 'Create Order',
        'jobcard': jobcard,
        'customers': Customer.objects.filter(active=True).order_by('name'),
        'items': Item.objects.all().order_by('name')
    }
    return render(request, 'employee_template/order_form.html', context)

