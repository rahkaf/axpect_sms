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
    try:
        today_attendance = EmployeeGPSAttendance.objects.filter(
            employee=employee, 
            date=today
        ).first()
    except Exception:
        # Fallback if table doesn't exist yet
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
    
    # Get recent performance ratings (last 7 days)
    try:
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        recent_ratings = EmployeeGPSAttendance.objects.filter(
            employee=employee,
            date__gte=week_ago,
            performance_rating__isnull=False
        ).order_by('-date')[:5]
        
        # Calculate average rating
        ratings = [r.performance_rating for r in recent_ratings if r.performance_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
    except Exception:
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
    qs = StaffScoresDaily.objects.filter(staff=emp, date__gte=start, date__lte=today)
    progress = {
        'jobs_completed': sum([x.jobs_completed or 0 for x in qs]),
        'orders_count': sum([x.orders_count or 0 for x in qs]),
        'bales_total': sum([x.bales_total or 0 for x in qs]),
        'payments_count': sum([x.payments_count or 0 for x in qs]),
        'points': sum([x.points or 0 for x in qs]),
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

            # scoring: 1 point + 0.2 per bale
            today = datetime.now().date()
            score, _ = StaffScoresDaily.objects.get_or_create(staff=request.user.employee, date=today)
            score.orders_count = (score.orders_count or 0) + 1
            score.bales_total = (score.bales_total or 0) + total_bales
            score.points = (score.points or 0) + 1.0 + (0.2 * total_bales)
            score.save()

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


@login_required
def employee_gps_attendance(request):
    """GPS-based attendance marking page for employees"""
    if request.user.user_type != '3':  # Only employees can access
        messages.error(request, "Access denied. Only employees can access this page.")
        return redirect('login_page')
    
    employee = get_object_or_404(Employee, admin=request.user)
    
    # Get today's attendance if exists
    from django.utils import timezone
    today = timezone.localdate()
    today_attendance = Attendance.objects.filter(
        department=employee.department, 
        date=today
    ).first()
    
    context = {
        'page_title': 'GPS Attendance',
        'employee': employee,
        'today_attendance': today_attendance,
        'department': employee.department,
    }
    return render(request, 'employee_template/gps_attendance.html', context)




@login_required
def simple_checkin(request):
    """Simple form-based check-in"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('employee_home')
    
    if request.user.user_type != '3':
        messages.error(request, "Access denied. Only employees can check in.")
        return redirect('login_page')
    
    try:
        employee = get_object_or_404(Employee, admin=request.user)
        gps = request.POST.get('gps', '')
        
        # Debug: Check what GPS data we received
        print(f"DEBUG Employee Checkin: User {request.user.email} attempting checkin")
        print(f"DEBUG Employee Checkin: GPS data received: '{gps}'")
        print(f"DEBUG Employee Checkin: GPS length: {len(gps) if gps else 0}")
        
        # Get today's date
        from django.utils import timezone
        today = timezone.localdate()
        print(f"DEBUG Employee Checkin: Today's date: {today}")
        
        # Create or get individual employee attendance record
        try:
            attendance, created = EmployeeGPSAttendance.objects.get_or_create(
                employee=employee, 
                date=today
            )
            print(f"DEBUG Employee Checkin: Attendance record {'created' if created else 'found'}")
        except Exception as e:
            print(f"DEBUG Employee Checkin: Database error: {e}")
            messages.error(request, f"Database error: Please run migrations first. Error: {str(e)}")
            return redirect('employee_home')
        
        # Check if already checked in
        if attendance.checkin_time:
            print(f"DEBUG Employee Checkin: Already checked in at {attendance.checkin_time}")
            messages.warning(request, f"You have already checked in today at {attendance.checkin_time.strftime('%H:%M:%S')}!")
            return redirect('employee_home')
        
        # Update check-in details
        attendance.checkin_time = timezone.now()
        attendance.checkin_gps = gps
        attendance.save()
        
        print(f"DEBUG Employee Checkin: Saved - Time: {attendance.checkin_time}, GPS: '{attendance.checkin_gps}'")
        messages.success(request, f"Successfully checked in at {attendance.checkin_time.strftime('%H:%M:%S')} with GPS location!")
        
    except Exception as e:
        messages.error(request, f"Check-in failed: {str(e)}")
    
    return redirect('employee_home')


@login_required
def simple_checkout(request):
    """Simple form-based check-out"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('employee_home')
    
    if request.user.user_type != '3':
        messages.error(request, "Access denied. Only employees can check out.")
        return redirect('login_page')
    
    try:
        employee = get_object_or_404(Employee, admin=request.user)
        gps = request.POST.get('gps', '')
        notes = request.POST.get('notes', '')
        
        # Get today's date
        from django.utils import timezone
        today = timezone.localdate()
        
        # Get individual employee attendance record
        try:
            attendance = EmployeeGPSAttendance.objects.filter(
                employee=employee, 
                date=today
            ).first()
        except Exception as e:
            messages.error(request, f"Database error: Please run migrations first. Error: {str(e)}")
            return redirect('employee_home')
        
        if not attendance or not attendance.checkin_time:
            messages.error(request, "Please check in first before checking out.")
            return redirect('employee_home')
        
        # Check if already checked out
        if attendance.checkout_time:
            messages.warning(request, f"You have already checked out today at {attendance.checkout_time.strftime('%H:%M:%S')}!")
            return redirect('employee_home')
        
        # Update check-out details
        attendance.checkout_time = timezone.now()
        attendance.checkout_gps = gps
        attendance.work_notes = notes
        attendance.save()
        
        # Calculate hours worked
        hours_worked = attendance.hours_worked
        
        messages.success(request, f"Successfully checked out at {attendance.checkout_time.strftime('%H:%M:%S')}! You worked {hours_worked:.1f} hours today.")
        
    except Exception as e:
        messages.error(request, f"Check-out failed: {str(e)}")
    
    return redirect('employee_home')


def employee_live_gps_map(request):
    """Employee Live GPS Map - Shows only themselves and their manager"""
    if request.user.user_type != '3':  # Only Employee can access
        messages.error(request, "Access denied. Employee access required.")
        return redirect('employee_home')
    
    context = {
        'page_title': 'Live GPS Map - My Location'
    }
    return render(request, 'employee_template/live_gps_map.html', context)


@csrf_exempt
def employee_gps_data_api(request):
    """API endpoint for Employee to fetch GPS data of themselves and their manager"""
    if request.user.user_type != '3':  # Only Employee can access
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from datetime import date
        today = date.today()
        
        employee = Employee.objects.get(admin=request.user)
        gps_data = []
        
        # Debug: Check employee GPS records
        all_employee_records = EmployeeGPSAttendance.objects.filter(employee=employee, date=today)
        print(f"DEBUG Employee API: Found {all_employee_records.count()} records for {request.user.email} today")
        for record in all_employee_records:
            print(f"DEBUG Employee API: Record - GPS: '{record.checkin_gps}', Time: {record.checkin_time}")
        
        # Get employee's own GPS location for today (only if they are online and recently active)
        from datetime import timedelta
        recent_threshold = timezone.now() - timedelta(minutes=10)
        
        # Only show employee's own location if they are online and recently active
        if employee.admin.is_online and employee.admin.last_seen and employee.admin.last_seen >= recent_threshold:
            try:
                employee_attendance = EmployeeGPSAttendance.objects.filter(
                    employee=employee,
                    date=today,
                    checkin_gps__isnull=False,
                    checkin_gps__gt=''  # Ensure GPS is not empty
                ).order_by('-checkin_time').first()
                
                print(f"DEBUG Employee API: Latest attendance record: {employee_attendance}")
                if employee_attendance:
                    print(f"DEBUG Employee API: GPS data: '{employee_attendance.checkin_gps}'")
                
                if employee_attendance and employee_attendance.checkin_gps.strip():
                    coords = employee_attendance.checkin_gps.split(',')
                    if len(coords) == 2:
                        lat = float(coords[0].strip())
                        lng = float(coords[1].strip())
                        
                        gps_data.append({
                            'user_id': employee.admin.id,
                            'name': f"{employee.admin.first_name} {employee.admin.last_name}",
                            'role': 'Employee (You)',
                            'lat': lat,
                            'lng': lng,
                            'marker_color': 'green',
                            'last_seen': employee.admin.last_seen.isoformat() if employee.admin.last_seen else None,
                            'checkin_time': employee_attendance.checkin_time.isoformat() if employee_attendance.checkin_time else None,
                            'is_online': employee.admin.is_online
                        })
            except (ValueError, IndexError) as e:
                print(f"Error parsing employee GPS coordinates: {e}")
        
        # Add manager's location if they are online and have GPS data
        try:
            # Find manager in the same department who is recently active
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(minutes=10)
            
            managers_in_dept = Manager.objects.filter(
                admin__employee__department=employee.department,
                admin__is_online=True,
                admin__last_seen__gte=recent_threshold  # Only managers active within last 10 minutes
            ).select_related('admin')
            
            for manager in managers_in_dept:
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
                except (ValueError, IndexError) as e:
                    print(f"Error parsing manager GPS coordinates: {e}")
                    continue
        except Exception as e:
            print(f"Error getting manager GPS data: {e}")
        
        return JsonResponse({
            'success': True,
            'data': gps_data,
            'count': len(gps_data)
        })
        
    except Exception as e:
        print(f"Error in employee_gps_data_api: {e}")
        return JsonResponse({'error': 'Failed to fetch GPS data'}, status=500)
