import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView
import csv
from django.utils import timezone

from .forms import *
from .models import *


def admin_home(request):
    total_manager = Manager.objects.all().count()
    total_employees = Employee.objects.all().count()
    departments = Department.objects.all()
    total_department = departments.count()
    total_division = Division.objects.all().count()
    attendance_list = Attendance.objects.filter(department__in=departments)
    total_attendance = attendance_list.count()
    attendance_list = []
    department_list = []
    for department in departments:
        attendance_count = Attendance.objects.filter(department=department).count()
        department_list.append(department.name[:7])
        attendance_list.append(attendance_count)
    # today's points per employee (top 10)
    from datetime import date
    from django.utils import timezone
    today = date.today()
    top_scores = StaffScoresDaily.objects.filter(date=today).select_related('staff__admin').order_by('-points')[:10]
    leaderboard = [{
        'name': f"{s.staff.admin.first_name} {s.staff.admin.last_name}",
        'points': s.points
    } for s in top_scores]

    # Today's GPS Attendance Summary using individual employee records
    try:
        today_gps_attendance = EmployeeGPSAttendance.objects.filter(date=today).select_related('employee')
    except Exception:
        today_gps_attendance = []
    
    all_employees = Employee.objects.all().select_related('admin', 'department')
    
    gps_attendance_summary = {
        'total_employees': total_employees,
        'checked_in': 0,
        'checked_out': 0,
        'not_marked': 0
    }
    
    for employee in all_employees:
        emp_attendance = next((att for att in today_gps_attendance if att.employee == employee), None)
        if emp_attendance and emp_attendance.checkin_time:
            gps_attendance_summary['checked_in'] += 1
            if emp_attendance.checkout_time:
                gps_attendance_summary['checked_out'] += 1
        else:
            gps_attendance_summary['not_marked'] += 1
    

    context = {
        'page_title': "Administrative Dashboard",
        'total_employees': total_employees,
        'total_manager': total_manager,
        'total_division': total_division,
        'total_department': total_department,
        'department_list': department_list,
        'attendance_list': attendance_list,
        'leaderboard': leaderboard,
        'gps_attendance_summary': gps_attendance_summary,
        'today': today

    }
    return render(request, 'ceo_template/home_content.html', context)


def export_daily_scores_csv(request):
    today = timezone.localdate()
    qs = StaffScoresDaily.objects.filter(date=today).select_related('staff__admin')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="daily_scores_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Staff', 'Date', 'Jobs Completed', 'Orders Count', 'Bales Total', 'Payments Count', 'Points'])
    for s in qs:
        writer.writerow([
            f"{s.staff.admin.first_name} {s.staff.admin.last_name}",
            s.date,
            s.jobs_completed,
            s.orders_count,
            s.bales_total,
            s.payments_count,
            s.points,
        ])
    return response


def add_manager(request):
    form = ManagerForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'page_title': 'Add Manager'}
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password')
            division = form.cleaned_data.get('division')
            passport = request.FILES.get('profile_pic')
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=2, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.manager.division = division
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_manager'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Please fulfil all requirements")

    return render(request, 'ceo_template/add_manager_template.html', context)


def add_employee(request):
    employee_form = EmployeeForm(request.POST or None, request.FILES or None)
    context = {'form': employee_form, 'page_title': 'Add Employee'}
    if request.method == 'POST':
        if employee_form.is_valid():
            first_name = employee_form.cleaned_data.get('first_name')
            last_name = employee_form.cleaned_data.get('last_name')
            address = employee_form.cleaned_data.get('address')
            email = employee_form.cleaned_data.get('email')
            gender = employee_form.cleaned_data.get('gender')
            password = employee_form.cleaned_data.get('password')
            division = employee_form.cleaned_data.get('division')
            department = employee_form.cleaned_data.get('department')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=3, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.employee.division = division
                user.employee.department = department
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_employee'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'ceo_template/add_employee_template.html', context)


def add_division(request):
    form = DivisionForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Division'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                division = Division()
                division.name = name
                division.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_division'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'ceo_template/add_division_template.html', context)


def add_department(request):
    form = DepartmentForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Department'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            division = form.cleaned_data.get('division')
            try:
                department = Department()
                department.name = name
                department.division = division
                department.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_department'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")

    return render(request, 'ceo_template/add_department_template.html', context)


def manage_manager(request):
    allManager = CustomUser.objects.filter(user_type=2)
    context = {
        'allManager': allManager,
        'page_title': 'Manage Manager'
    }
    return render(request, "ceo_template/manage_manager.html", context)


def manage_employee(request):
    employees = CustomUser.objects.filter(user_type=3)
    context = {
        'employees': employees,
        'page_title': 'Manage Employees'
    }
    return render(request, "ceo_template/manage_employee.html", context)


def manage_division(request):
    divisions = Division.objects.all()
    context = {
        'divisions': divisions,
        'page_title': 'Manage Divisions'
    }
    return render(request, "ceo_template/manage_division.html", context)


def manage_department(request):
    departments = Department.objects.all()
    context = {
        'departments': departments,
        'page_title': 'Manage Departments'
    }
    return render(request, "ceo_template/manage_department.html", context)


def customers_manage(request):
    """Enhanced customer management with filtering and pagination"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    active_filter = request.GET.get('active', '')
    
    # Base queryset
    customers = Customer.objects.select_related('city', 'owner_staff__admin').order_by('-created_at')
    
    # Apply filters
    if search_query:
        from django.db import models
        customers = customers.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(phone_primary__icontains=search_query)
        )
    
    if city_filter:
        customers = customers.filter(city_id=city_filter)
    
    if active_filter:
        customers = customers.filter(active=active_filter == 'true')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    customers_page = paginator.get_page(page_number)
    
    # Statistics
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(active=True).count()
    inactive_customers = Customer.objects.filter(active=False).count()
    
    # Get cities for filter dropdown
    cities = City.objects.all().order_by('name')
    
    context = {
        'customers': customers_page,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'cities': cities,
        'current_filters': {
            'search': search_query,
            'city': city_filter,
            'active': active_filter,
        },
        'page_title': 'Customer Management'
    }
    return render(request, "ceo_template/customers_manage.html", context)


def customer_add(request):
    form = CustomerForm(request.POST or None)
    context = {'form': form, 'page_title': 'Add Customer'}
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added")
            return redirect(reverse('customers_manage'))
        else:
            messages.error(request, "Please fix the errors")
    return render(request, 'ceo_template/customer_form.html', context)


def customer_edit(request, customer_id):
    instance = get_object_or_404(Customer, id=customer_id)
    form = CustomerForm(request.POST or None, instance=instance)
    context = {'form': form, 'page_title': 'Edit Customer'}
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated")
            return redirect(reverse('customers_manage'))
        else:
            messages.error(request, "Please fix the errors")
    return render(request, 'ceo_template/customer_form.html', context)


def customer_delete(request, customer_id):
    instance = get_object_or_404(Customer, id=customer_id)
    instance.delete()
    messages.success(request, "Customer deleted")
    return redirect(reverse('customers_manage'))


def customer_toggle_status(request, customer_id):
    """Toggle customer active status via AJAX"""
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            customer.active = not customer.active
            customer.save()
            
            status = 'activated' if customer.active else 'deactivated'
            return JsonResponse({
                'success': True,
                'message': f'Customer "{customer.name}" {status} successfully!',
                'active': customer.active
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def edit_manager(request, manager_id):
    manager = get_object_or_404(Manager, id=manager_id)
    form = ManagerForm(request.POST or None, instance=manager)
    context = {
        'form': form,
        'manager_id': manager_id,
        'page_title': 'Edit Manager'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            division = form.cleaned_data.get('division')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=manager.admin.id)
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                manager.division = division
                user.save()
                manager.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_manager', args=[manager_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please fil form properly")
    else:
        user = CustomUser.objects.get(id=manager_id)
        manager = Manager.objects.get(id=user.id)
        return render(request, "ceo_template/edit_manager_template.html", context)


def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    form = EmployeeForm(request.POST or None, instance=employee)
    context = {
        'form': form,
        'employee_id': employee_id,
        'page_title': 'Edit Employee'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            division = form.cleaned_data.get('division')
            department = form.cleaned_data.get('department')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=employee.admin.id)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                employee.division = division
                employee.department = department
                user.save()
                employee.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_employee', args=[employee_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please Fill Form Properly!")
    else:
        return render(request, "ceo_template/edit_employee_template.html", context)


def edit_division(request, division_id):
    instance = get_object_or_404(Division, id=division_id)
    form = DivisionForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'division_id': division_id,
        'page_title': 'Edit Division'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                division = Division.objects.get(id=division_id)
                division.name = name
                division.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'ceo_template/edit_division_template.html', context)


def edit_department(request, department_id):
    instance = get_object_or_404(Department, id=department_id)
    form = DepartmentForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'department_id': department_id,
        'page_title': 'Edit Department'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            division = form.cleaned_data.get('division')
            try:
                department = Department.objects.get(id=department_id)
                department.name = name
                department.division = division
                department.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_department', args=[department_id]))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")
    return render(request, 'ceo_template/edit_department_template.html', context)


@csrf_exempt
def check_email_availability(request):
    email = request.POST.get("email")
    try:
        user = CustomUser.objects.filter(email=email).exists()
        if user:
            return HttpResponse(True)
        return HttpResponse(False)
    except Exception as e:
        return HttpResponse(False)


@csrf_exempt
def employee_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackEmployee.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Employee Feedback Messages'
        }
        return render(request, 'ceo_template/employee_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackEmployee, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def manager_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackManager.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Manager Feedback Messages'
        }
        return render(request, 'ceo_template/manager_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackManager, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def view_manager_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportManager.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Manager'
        }
        return render(request, "ceo_template/manager_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportManager, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


@csrf_exempt
def view_employee_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportEmployee.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Employees'
        }
        return render(request, "ceo_template/employee_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportEmployee, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


def admin_view_attendance(request):
    departments = Department.objects.all()
    context = {
        'departments': departments,
        'page_title': 'View Attendance'
    }

    return render(request, "ceo_template/admin_view_attendance.html", context)


@csrf_exempt
def get_admin_attendance(request):
    department_id = request.POST.get('department')
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        department = get_object_or_404(Department, id=department_id)
        attendance = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_reports = AttendanceReport.objects.filter(attendance=attendance)
        json_data = []
        for report in attendance_reports:
            data = {
                "status": str(report.status),
                "name": str(report.employee)
            }
            json_data.append(data)
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        return None


def admin_view_profile(request):
    admin = get_object_or_404(Admin, admin=request.user)
    form = AdminForm(request.POST or None, request.FILES or None,
                     instance=admin)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                passport = request.FILES.get('profile_pic') or None
                custom_user = admin.admin
                if password != None:
                    custom_user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    custom_user.profile_pic = passport_url
                custom_user.first_name = first_name
                custom_user.last_name = last_name
                custom_user.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('admin_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
    return render(request, "ceo_template/admin_view_profile.html", context)


def admin_notify_manager(request):
    manager = CustomUser.objects.filter(user_type=2)
    context = {
        'page_title': "Send Notifications To Manager",
        'allManager': manager
    }
    return render(request, "ceo_template/manager_notification.html", context)


def admin_notify_employee(request):
    employee = CustomUser.objects.filter(user_type=3)
    context = {
        'page_title': "Send Notifications To Employees",
        'employees': employee
    }
    return render(request, "ceo_template/employee_notification.html", context)


@csrf_exempt
def send_employee_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    employee = get_object_or_404(Employee, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Axpect Technologies Textile OTM",
                'body': message,
                'click_action': reverse('employee_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': employee.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationEmployee(employee=employee, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


@csrf_exempt
def send_manager_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    manager = get_object_or_404(Manager, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Axpect Technologies Textile OTM",
                'body': message,
                'click_action': reverse('manager_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': manager.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationManager(manager=manager, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def delete_manager(request, manager_id):
    manager = get_object_or_404(CustomUser, manager__id=manager_id)
    manager.delete()
    messages.success(request, "Manager deleted successfully!")
    return redirect(reverse('manage_manager'))


def delete_employee(request, employee_id):
    employee = get_object_or_404(CustomUser, employee__id=employee_id)
    employee.delete()
    messages.success(request, "Employee deleted successfully!")
    return redirect(reverse('manage_employee'))


def delete_division(request, division_id):
    division = get_object_or_404(Division, id=division_id)
    try:
        division.delete()
        messages.success(request, "Division deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some employees are assigned to this division already. Kindly change the affected employee division and try again")
    return redirect(reverse('manage_division'))


def delete_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    department.delete()
    messages.success(request, "Department deleted successfully!")
    return redirect(reverse('manage_department'))


def admin_gps_attendance_dashboard(request):
    """GPS attendance dashboard for admins to see all employee attendance"""
    if request.user.user_type != '1':  # Only admins can access
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    # Get today's date
    from django.utils import timezone
    today = timezone.localdate()
    
    # Get all employees
    employees = Employee.objects.all().select_related('admin', 'department', 'division')
    
    # Get all departments
    departments = Department.objects.all()
    
    # Get today's individual employee attendance records
    try:
        today_attendance = EmployeeGPSAttendance.objects.filter(date=today).select_related('employee__admin', 'employee__department')
    except Exception as e:
        # Fallback if table doesn't exist yet or missing columns
        print(f"Database error in admin_gps_attendance_dashboard: {e}")
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
    
    # Department-wise statistics
    dept_stats = {}
    for dept in departments:
        dept_employees = [ea for ea in employee_attendance if ea['employee'].department == dept]
        dept_stats[dept.name] = {
            'total': len(dept_employees),
            'checked_in': len([ea for ea in dept_employees if ea['status'] in ['Checked In', 'Checked Out']]),
            'checked_out': len([ea for ea in dept_employees if ea['status'] == 'Checked Out']),
            'not_marked': len([ea for ea in dept_employees if ea['status'] == 'Not Marked'])
        }
    
    context = {
        'page_title': 'Admin GPS Attendance Dashboard',
        'employee_attendance': employee_attendance,
        'departments': departments,
        'today': today,
        'total_employees': total_employees,
        'checked_in': checked_in,
        'checked_out': checked_out,
        'not_marked': not_marked,
        'dept_stats': dept_stats,
    }
    return render(request, 'ceo_template/gps_attendance_dashboard.html', context)


@csrf_exempt
def submit_employee_rating(request):
    """Submit performance rating for an employee"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    if request.user.user_type not in ['1', '2']:  # Only admin or manager
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        attendance_id = data.get('attendance_id')
        rating = int(data.get('rating'))
        comments = data.get('comments', '')
        
        if rating < 1 or rating > 5:
            return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
        
        # Get the attendance record
        attendance = get_object_or_404(EmployeeGPSAttendance, id=attendance_id)
        
        # Check if user has permission to rate this employee
        if request.user.user_type == '2':  # Manager
            manager = get_object_or_404(Manager, admin=request.user)
            if attendance.employee.division != manager.division:
                return JsonResponse({'error': 'You can only rate employees in your division'}, status=403)
        
        # Update the rating
        from django.utils import timezone
        attendance.performance_rating = rating
        attendance.rating_given_by = request.user
        attendance.rating_date = timezone.now()
        attendance.rating_comments = comments
        attendance.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Rating submitted successfully for {attendance.employee.admin.first_name} {attendance.employee.admin.last_name}',
            'rating': rating,
            'stars': attendance.rating_stars
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===============================
# CUSTOMER MANAGEMENT VIEWS
# ===============================

def admin_customer_list(request):
    """Admin view to list and manage all customers"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    active_filter = request.GET.get('active', '')
    
    # Base queryset
    customers = Customer.objects.select_related('city', 'owner_staff').order_by('-created_at')
    
    # Apply filters
    if search_query:
        customers = customers.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(phone_primary__icontains=search_query)
        )
    
    if city_filter:
        customers = customers.filter(city_id=city_filter)
    
    if active_filter:
        customers = customers.filter(active=active_filter == 'true')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    customers_page = paginator.get_page(page_number)
    
    # Statistics
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(active=True).count()
    inactive_customers = Customer.objects.filter(active=False).count()
    
    # Get cities for filter dropdown
    cities = City.objects.all().order_by('name')
    
    context = {
        'page_title': 'Customer Management',
        'customers': customers_page,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'cities': cities,
        'current_filters': {
            'search': search_query,
            'city': city_filter,
            'active': active_filter,
        }
    }
    return render(request, 'ceo_template/customer_list.html', context)


def admin_customer_create(request):
    """Admin view to create new customers"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" created successfully!')
            return redirect('admin_customer_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerForm()
    
    context = {
        'page_title': 'Add New Customer',
        'form': form,
        'form_action': 'Create'
    }
    return render(request, 'ceo_template/customer_form.html', context)


def admin_customer_edit(request, customer_id):
    """Admin view to edit existing customers"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('admin_customer_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'page_title': 'Edit Customer',
        'form': form,
        'form_action': 'Update',
        'customer': customer
    }
    return render(request, 'ceo_template/customer_form.html', context)


def admin_customer_delete(request, customer_id):
    """Admin view to delete customers"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{customer_name}" deleted successfully!')
        return redirect('admin_customer_list')
    
    context = {
        'page_title': 'Delete Customer',
        'customer': customer
    }
    return render(request, 'ceo_template/customer_delete.html', context)


def admin_customer_toggle_status(request, customer_id):
    """Admin view to toggle customer active status"""
    if request.user.user_type != '1':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        customer.active = not customer.active
        customer.save()
        
        status = 'activated' if customer.active else 'deactivated'
        return JsonResponse({
            'success': True,
            'message': f'Customer "{customer.name}" {status} successfully!',
            'active': customer.active
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def admin_mark_attendance(request):
    """Admin self-attendance marking page"""
    if request.user.user_type != '1':  # Only admins can access
        messages.error(request, "Access denied. Only admins can access this page.")
        return redirect('login_page')
    
    try:
        # Get or create employee profile for admin
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
            'today_attendance': today_attendance,
            'today': today,
            'employee': employee,
        }
        
        return render(request, 'ceo_template/admin_mark_attendance.html', context)
        
    except Exception as e:
        print(f"Error in admin_mark_attendance: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('admin_home')


def admin_checkin(request):
    """Handle admin check-in using form submission with success messages"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('admin_mark_attendance')
    
    if not request.user.is_authenticated:
        messages.error(request, "User not authenticated.")
        return redirect('login_page')
    
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    try:
        # Get GPS data from POST
        gps_location = request.POST.get('gps', '')
        
        # Get or create employee profile
        from .views import get_or_create_employee_profile
        employee = get_or_create_employee_profile(request.user)
        
        if not employee:
            messages.error(request, "Could not create employee profile. Please contact system administrator.")
            return redirect('admin_mark_attendance')
        
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
            return redirect('admin_mark_attendance')
        
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
        print(f"Admin checkin error: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Check-in failed: {str(e)}")
    
    return redirect('admin_mark_attendance')


def admin_checkout(request):
    """Handle admin check-out using form submission with success messages"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('admin_mark_attendance')
    
    if not request.user.is_authenticated:
        messages.error(request, "User not authenticated.")
        return redirect('login_page')
    
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
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
            return redirect('admin_mark_attendance')
        
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
            return redirect('admin_mark_attendance')
        
        if attendance.checkout_time:
            messages.warning(request, f"You have already checked out today at {attendance.checkout_time.strftime('%H:%M:%S')}!")
            return redirect('admin_mark_attendance')
        
        # Update checkout details
        attendance.checkout_time = current_time
        attendance.checkout_gps = gps_location
        attendance.work_notes = work_notes
        attendance.save()
        
        messages.success(request, f"Successfully checked out at {current_time.strftime('%H:%M:%S')}! Total hours worked: {attendance.hours_worked:.2f}")
        
    except Exception as e:
        print(f"Admin checkout error: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Check-out failed: {str(e)}")
    
    return redirect('admin_mark_attendance')
