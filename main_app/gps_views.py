"""
GPS Views for Staff Management System
"""
import json
import math
from datetime import datetime, date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from .models import (
    CustomUser, Employee, Manager, Department, Division, City,
    Attendance, LeaveReportEmployee, LeaveReportManager, 
    FeedbackEmployee, FeedbackManager, NotificationEmployee, NotificationManager,
    GPSTrack, GPSCheckIn, EmployeeGeofence, 
    GPSRoute, GPSSession
)
from .gps_utils import is_in_geofence, calculate_distance, get_location_type


# ======================================
# Employee GPS Views
# ======================================

@login_required
def employee_gps_dashboard(request):
    """Employee GPS tracking dashboard"""
    employee = get_object_or_404(Employee, admin=request.user)
    today = timezone.localdate()
    
    try:
        # Get today's check-in status from database
        today_checkin = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date=today
        ).first()
        
        is_checked_out = today_checkin.check_out_time is not None if today_checkin else False
        checkout_info = None
        
        if today_checkin and is_checked_out:
            checkout_info = {
                'checkout_time': today_checkin.check_out_time.isoformat(),
                'work_summary': today_checkin.work_summary,
                'duration_hours': today_checkin.duration_hours
            }
    except Exception:
        today_checkin = None
        is_checked_out = False
        checkout_info = None
    
    # Get real GPS data from database
    recent_tracks = GPSTrack.objects.filter(
        employee=employee
    ).order_by('-timestamp')[:10]
    
    try:
        # Get this week's check-ins
        week_start = today - timedelta(days=7)
        week_checkins = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date__gte=week_start
        )
        
        # Calculate total hours for the week
        total_hours_week = 0
        for checkin in week_checkins:
            if checkin.check_out_time:
                duration = checkin.check_out_time - checkin.check_in_time
                total_hours_week += duration.total_seconds() / 3600
    except Exception:
        week_checkins = []
        total_hours_week = 0
    
    try:
        # Get active sessions
        active_session = GPSSession.objects.filter(
            employee=employee,
            is_active=True
        ).order_by('-start_time').first()
    except Exception:
        active_session = None
    
    context = {
        'employee': employee,
        'today_checkin': today_checkin,
        'is_checked_out': is_checked_out,
        'checkout_info': checkout_info,
        'recent_tracks': recent_tracks,
        'week_checkins': week_checkins,
        'total_hours_week': total_hours_week,
        'active_session': active_session,
        'page_title': 'GPS Tracking Dashboard',
    }
    
    return render(request, 'employee_template/gps_dashboard.html', context)


@login_required
def employee_gps_checkin(request):
    """Employee GPS check-in page"""
    employee = get_object_or_404(Employee, admin=request.user)
    today = timezone.localdate()
    
    # Check if employee already checked in today
    existing_checkin = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date=today
    ).first()
    
    if existing_checkin:
        messages.warning(request, "You have already checked in today.")
        return redirect('employee_gps_dashboard')
    
    # Get available geofences for this employee's department
    geofences = EmployeeGeofence.objects.filter(
        department=employee.department,
        is_active=True,
        allow_checkin=True
    ).order_by('name')
    
    context = {
        'employee': employee,
        'geofences': geofences,
        'page_title': 'GPS Check-In',
    }
    
    return render(request, 'employee_template/gps_checkin.html', context)


@login_required
def employee_gps_checkout(request):
    """Employee GPS check-out page"""
    employee = get_object_or_404(Employee, admin=request.user)
    today = timezone.localdate()
    
    # Check if employee has checked in today
    active_checkin = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date=today,
        check_out_time__isnull=True
    ).first()
    
    if not active_checkin:
        messages.info(request, "You are not checked in today or have already checked out.")
        return redirect('employee_gps_dashboard')
    
    context = {
        'employee': employee,
        'active_checkin': active_checkin,
        'page_title': 'GPS Check-Out',
    }
    
    return render(request, 'employee_template/gps_checkout.html', context)


@login_required
def employee_gps_history(request):
    """Employee GPS attendance history"""
    employee = get_object_or_404(Employee, admin=request.user)
    
    # Get search parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get check-ins from database
    checkins = GPSCheckIn.objects.filter(employee=employee)
    
    # Apply date filtering
    if start_date:
        checkins = checkins.filter(check_in_time__date__gte=start_date)
    if end_date:
        checkins = checkins.filter(check_in_time__date__lte=end_date)
    
    checkins = checkins.order_by('-check_in_time')[:50]
    
    context = {
        'employee': employee,
        'checkins': checkins,
        'start_date': start_date,
        'end_date': end_date,
        'page_title': 'GPS Attendance History',
    }
    
    return render(request, 'employee_template/gps_history.html', context)


@login_required
def employee_live_location(request):
    """Live location tracking for employee"""
    employee = get_object_or_404(Employee, admin=request.user)
    
    context = {
        'employee': employee,
        'page_title': 'Live Location',
    }
    
    return render(request, 'employee_template/live_location.html', context)


# ======================================
# Manager GPS Views
# ======================================

@login_required
def manager_gps_dashboard(request):
    """Manager GPS tracking dashboard"""
    from .models import Manager
    
    # Get manager record and their division employees
    try:
        manager_record = Manager.objects.get(admin=request.user)
        # Manager can only see employees in their division
        employees = Employee.objects.filter(division=manager_record.division)
        manager = manager_record
        
    except Manager.DoesNotExist:
        # If no manager profile, redirect to admin for profile creation
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    today = timezone.localdate()
    
    # Get real GPS data from database
    today_checkins = GPSCheckIn.objects.filter(
        employee__in=employees,
        check_in_time__date=today
    ).select_related('employee', 'employee__admin')
    
    checked_in_count = today_checkins.count()
    checked_out_count = today_checkins.filter(check_out_time__isnull=False).count()
    total_employees = employees.count()
    
    # Department statistics for manager's division only
    department_stats = []
    try:
        departments = Department.objects.filter(division=manager.division)
            
        for dept in departments:
            dept_employees = employees.filter(department=dept)
            dept_checked_in = GPSCheckIn.objects.filter(
                employee__in=dept_employees,
                check_in_time__date=today
            ).count()
            
            department_stats.append({
                'department': dept,
                'employee_count': dept_employees.count(),
                'checked_in_count': dept_checked_in,
                'checked_in_percentage': round((dept_checked_in / dept_employees.count() * 100) if dept_employees.count() > 0 else 0, 1)
            })
    except Exception:
        department_stats = []
    
    context = {
        'manager': manager,
        'employees': employees,
        'total_employees': total_employees,
        'checked_in_count': checked_in_count,
        'checked_out_count': checked_out_count,
        'today_checkins': today_checkins,
        'department_stats': department_stats,
        'page_title': 'Team GPS Dashboard',
    }
    
    return render(request, 'manager_template/gps_dashboard.html', context)


@login_required
def manager_employee_locations(request):
    """Manager view of all employee locations"""
    from .models import Manager
    
    # Get manager record and their division employees
    try:
        manager_record = Manager.objects.get(admin=request.user)
        employees = Employee.objects.filter(division=manager_record.division)
        manager = manager_record
        
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Get real GPS location data from database
    today = timezone.localdate()
    employee_locations = []
    
    # Get today's check-ins for employees in manager's division
    today_checkins = GPSCheckIn.objects.filter(
        employee__in=employees,
        check_in_time__date=today
    ).select_related('employee', 'employee__admin')
    
    for checkin in today_checkins:
        # Get latest GPS track for more accurate location
        latest_track = GPSTrack.objects.filter(
            employee=checkin.employee,
            timestamp__date=today
        ).order_by('-timestamp').first()
        
        location_info = {
            'employee': checkin.employee,
            'latitude': float(latest_track.latitude if latest_track else checkin.check_in_latitude),
            'longitude': float(latest_track.longitude if latest_track else checkin.check_in_longitude),
            'address': latest_track.address if latest_track else checkin.check_in_address,
            'check_in_time': checkin.check_in_time.isoformat(),
            'status': 'Checked Out' if checkin.check_out_time else 'Checked In',
            'work_summary': checkin.work_summary,
            'duration_hours': checkin.duration_hours or 0,
            'last_update': latest_track.timestamp if latest_track else checkin.check_in_time
        }
        employee_locations.append(location_info)
    
    context = {
        'manager': manager,
        'employees': employees,
        'employee_locations': employee_locations,
        'total_locations': len(employee_locations),
        'page_title': 'Team Locations',
    }
    
    return render(request, 'manager_template/employee_locations.html', context)


@login_required
def manager_attendance_reports(request):
    """Manager attendance reports and analytics"""
    from .models import Manager
    
    # Get manager record and their division employees
    try:
        manager_record = Manager.objects.get(admin=request.user)
        employees = Employee.objects.filter(division=manager_record.division)
        manager = manager_record
        
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Get attendance data from database
    today = timezone.localdate()
    month_start = today.replace(day=1)
    
    month_attendance = GPSCheckIn.objects.filter(
        employee__in=employees,
        check_in_time__date__gte=month_start
    ).select_related('employee', 'employee__admin').order_by('-check_in_time')
    
    total_employees = employees.count()
    checked_in_today = GPSCheckIn.objects.filter(
        employee__in=employees,
        check_in_time__date=today
    ).count()
    
    context = {
        'manager': manager,
        'employees': employees,
        'month_attendance': month_attendance,
        'total_employees': total_employees,
        'checked_in_today': checked_in_today,
        'page_title': 'Attendance Reports',
    }
    
    return render(request, 'manager_template/attendance_reports.html', context)


@login_required
def manager_employee_details(request, employee_id):
    """Manager view of specific employee GPS details (division-scoped)"""
    from .models import Manager
    
    # Get manager record and verify permissions
    try:
        manager_record = Manager.objects.get(admin=request.user)
        manager = manager_record
        
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found. Please contact admin.")
        return redirect('manager_home')
    
    # Get employee and verify they're in manager's division
    try:
        employee = get_object_or_404(Employee, id=employee_id)
        
        # Security check: Manager can only view employees in their division
        if employee.division != manager.division:
            messages.error(request, "Access denied. You can only view employees in your division.")
            return redirect('manager_attendance_reports')
            
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('manager_attendance_reports')
    
    # Get date range (default: last 30 days)
    end_date = timezone.localdate()
    date_filter = request.GET.get('date_range', '30')
    
    if date_filter == '7':
        start_date = end_date - timedelta(days=7)
    elif date_filter == '90':
        start_date = end_date - timedelta(days=90)
    else:  # 30 days default
        start_date = end_date - timedelta(days=30)
    
    # Get employee's GPS check-ins
    checkins = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date
    ).order_by('-check_in_time')
    
    # Get today's check-in
    today_checkin = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date=end_date
    ).first()
    
    # Calculate statistics
    total_checkins = checkins.count()
    completed_checkins = checkins.filter(check_out_time__isnull=False).count()
    
    # Calculate average hours
    total_hours = 0
    for checkin in checkins.filter(check_out_time__isnull=False):
        if checkin.duration_hours:
            total_hours += checkin.duration_hours
    
    avg_hours = total_hours / completed_checkins if completed_checkins > 0 else 0
    
    # Get recent GPS tracks
    recent_tracks = GPSTrack.objects.filter(
        employee=employee,
        timestamp__date__gte=start_date
    ).order_by('-timestamp')[:20]
    
    # Get active session
    active_session = GPSSession.objects.filter(
        employee=employee,
        is_active=True
    ).first()
    
    # Prepare chart data for the last 7 days
    chart_labels = []
    chart_data = []
    
    for i in range(7):
        date = end_date - timedelta(days=i)
        chart_labels.insert(0, date.strftime('%m/%d'))
        
        daily_checkins = checkins.filter(check_in_time__date=date).count()
        chart_data.insert(0, daily_checkins)
    
    chart_data_json = {
        'daily_activity': {
            'labels': chart_labels,
            'data': chart_data
        }
    }
    
    context = {
        'manager': manager,
        'employee': employee,
        'today_checkin': today_checkin,
        'checkins': checkins,
        'recent_tracks': recent_tracks,
        'active_session': active_session,
        'total_checkins': total_checkins,
        'completed_checkins': completed_checkins,
        'avg_hours': avg_hours,
        'start_date': start_date,
        'end_date': end_date,
        'date_filter': date_filter,
        'chart_data': json.dumps(chart_data_json),
        'page_title': f'{employee.admin.first_name} {employee.admin.last_name} - GPS Details',
    }
    
    return render(request, 'manager_template/employee_gps_details.html', context)


# ======================================
# CEO/Admin GPS Views
# ======================================

@login_required
def admin_gps_dashboard(request):
    """CEO GPS tracking dashboard with real-time data"""
    from django.db.models import Count, Q
    import json
    
    today = timezone.localdate()
    
    # Organization-wide statistics
    all_employees = Employee.objects.all()
    total_employees = all_employees.count()
    
    # Get real GPS data from database
    today_checkins = GPSCheckIn.objects.filter(
        check_in_time__date=today
    ).select_related('employee', 'employee__admin', 'employee__department')
    
    checked_in_today = today_checkins.count()
    active_sessions = today_checkins.filter(check_out_time__isnull=True)
    completed_sessions = today_checkins.filter(check_out_time__isnull=False)
    
    # Recent activity (last 20 check-ins/check-outs)
    recent_activity = []
    
    # Recent check-ins
    recent_checkins = today_checkins.order_by('-check_in_time')[:10]
    for checkin in recent_checkins:
        recent_activity.append({
            'type': 'checkin',
            'employee': checkin.employee,
            'time': checkin.check_in_time,
            'location': checkin.check_in_address or 'Location not available'
        })
    
    # Recent check-outs
    recent_checkouts = completed_sessions.order_by('-check_out_time')[:10]
    for checkout in recent_checkouts:
        recent_activity.append({
            'type': 'checkout',
            'employee': checkout.employee,
            'time': checkout.check_out_time,
            'location': checkout.check_out_address or 'Location not available'
        })
    
    # Sort by time (most recent first)
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    recent_activity = recent_activity[:20]
    
    # Department statistics with real data
    department_stats = []
    for dept in Department.objects.all():
        dept_employees = Employee.objects.filter(department=dept)
        dept_checked_in = today_checkins.filter(employee__department=dept).count()
        dept_active = active_sessions.filter(employee__department=dept).count()
        
        department_stats.append({
            'department': dept,
            'employee_count': dept_employees.count(),
            'checked_in_count': dept_checked_in,
            'active_count': dept_active,
            'checked_in_percentage': round((dept_checked_in / dept_employees.count() * 100) if dept_employees.count() > 0 else 0, 1)
        })
    
    # Organization Activity Map Data
    map_data = []
    
    # If no active sessions, create some sample data for demonstration
    if not active_sessions.exists():
        # Add sample data for demonstration (remove this in production)
        sample_employees = Employee.objects.all()[:3]  # Get first 3 employees
        for i, emp in enumerate(sample_employees):
            if emp.department:
                dept_colors = {
                    'Engineering': '#667eea',
                    'Sales': '#28a745', 
                    'Marketing': '#ffc107',
                    'HR': '#17a2b8',
                    'Operations': '#fd7e14'
                }
                dept_name = emp.department.name
                color = dept_colors.get(dept_name, '#6c757d')
                
                # Sample coordinates around San Francisco
                sample_coords = [
                    (37.7749, -122.4194),  # SF City Hall
                    (37.7849, -122.4094),  # North Beach
                    (37.7649, -122.4294),  # Mission District
                ]
                
                lat, lng = sample_coords[i % len(sample_coords)]
                
                map_data.append({
                    'id': emp.id,
                    'name': f"{emp.admin.first_name} {emp.admin.last_name}",
                    'department': dept_name,
                    'latitude': lat,
                    'longitude': lng,
                    'address': f'Sample Location {i+1}, San Francisco',
                    'checkin_time': timezone.now().strftime('%I:%M %p'),
                    'status': 'Demo',
                    'color': color,
                    'work_summary': f'Sample work activity for {emp.admin.first_name}'
                })
    
    # Process real active sessions
    for checkin in active_sessions:
        if checkin.check_in_latitude and checkin.check_in_longitude:
            # Determine department color
            dept_colors = {
                'Engineering': '#667eea',
                'Sales': '#28a745', 
                'Marketing': '#ffc107',
                'HR': '#17a2b8',
                'Operations': '#fd7e14'
            }
            dept_name = checkin.employee.department.name if checkin.employee.department else 'Other'
            color = dept_colors.get(dept_name, '#6c757d')
            
            map_data.append({
                'id': checkin.employee.id,
                'name': f"{checkin.employee.admin.first_name} {checkin.employee.admin.last_name}",
                'department': dept_name,
                'latitude': float(checkin.check_in_latitude),
                'longitude': float(checkin.check_in_longitude),
                'address': checkin.check_in_address or 'Address not available',
                'checkin_time': checkin.check_in_time.strftime('%I:%M %p'),
                'status': 'Active',
                'color': color,
                'work_summary': checkin.work_summary or 'No summary provided'
            })
    
    # Location usage statistics
    office_checkins = 0
    field_checkins = 0
    remote_checkins = 0
    
    # Get geofences for categorization
    office_geofences = EmployeeGeofence.objects.filter(
        fence_type='OFFICE',
        is_active=True
    )
    
    field_geofences = EmployeeGeofence.objects.filter(
        fence_type__in=['WORK_SITE', 'FIELD'],
        is_active=True
    )
    
    # Categorize check-ins by location type
    for checkin in today_checkins:
        if checkin.check_in_latitude and checkin.check_in_longitude:
            is_office = False
            is_field = False
            
            # Check if location is within office geofences
            for geofence in office_geofences:
                if is_in_geofence(checkin.check_in_latitude, checkin.check_in_longitude, geofence):
                    is_office = True
                    break
            
            # Check if location is within field geofences
            if not is_office:
                for geofence in field_geofences:
                    if is_in_geofence(checkin.check_in_latitude, checkin.check_in_longitude, geofence):
                        is_field = True
                        break
            
            if is_office:
                office_checkins += 1
            elif is_field:
                field_checkins += 1
            else:
                remote_checkins += 1
        else:
            remote_checkins += 1
    
    context = {
        'total_employees': total_employees,
        'checked_in_today': checked_in_today,
        'active_sessions_count': active_sessions.count(),
        'completed_sessions_count': completed_sessions.count(),
        'department_stats': department_stats,
        'today_checkins': today_checkins,
        'active_sessions': active_sessions,
        'recent_activity': recent_activity,
        'map_data': json.dumps(map_data),
        'office_checkins': office_checkins,
        'field_checkins': field_checkins,
        'remote_checkins': remote_checkins,
        'page_title': 'Organization GPS Dashboard',
    }
    
    return render(request, 'ceo_template/gps_dashboard.html', context)


@login_required
def api_department_details(request, department_id):
    """API endpoint to get department and employee details"""
    try:
        from .models import Department, Employee
        from django.utils import timezone
        
        department = get_object_or_404(Department, id=department_id)
        today = timezone.localdate()
        
        # Get all employees in this department
        employees = Employee.objects.filter(department=department).select_related('admin')
        
        employee_data = []
        checked_in_count = 0
        
        # Get today's check-ins for department employees
        dept_checkins = GPSCheckIn.objects.filter(
            employee__in=employees,
            check_in_time__date=today
        ).select_related('employee', 'employee__admin')
        
        # Create a lookup dict for quick access
        checkin_lookup = {checkin.employee.id: checkin for checkin in dept_checkins}
        
        for emp in employees:
            checkin = checkin_lookup.get(emp.id)
            
            # Determine status
            if checkin:
                if checkin.check_out_time:
                    status = 'Checked Out'
                    status_class = 'bg-secondary'
                    last_checkin = checkin.check_out_time.strftime('%I:%M %p')
                else:
                    status = 'Checked In'
                    status_class = 'bg-success'
                    last_checkin = checkin.check_in_time.strftime('%I:%M %p')
                checked_in_count += 1
            else:
                status = 'Not Checked In'
                status_class = 'bg-warning'
                last_checkin = '-'
            
            employee_data.append({
                'id': emp.id,
                'name': f"{emp.admin.first_name} {emp.admin.last_name}",
                'email': emp.admin.email,
                'status': status,
                'status_class': status_class,
                'last_checkin': last_checkin,
                'work_summary': checkin.work_summary if checkin else '',
                'duration_hours': checkin.duration_hours if checkin else 0
            })
        
        # Calculate statistics
        total_employees = employees.count()
        participation_rate = (checked_in_count / total_employees * 100) if total_employees > 0 else 0
        
        # Get department GPS stats
        total_checkins_today = checked_in_count
        active_sessions = checked_in_count - sum(1 for emp in employee_data if emp['status'] == 'Checked Out')
        
        response_data = {
            'success': True,
            'department': {
                'id': department.id,
                'name': department.name,
                'division': department.division.name if department.division else 'No Division'
            },
            'statistics': {
                'total_employees': total_employees,
                'checked_in_today': checked_in_count,
                'participation_rate': round(participation_rate, 1),
                'total_checkins_today': total_checkins_today,
                'avg_work_hours': 8.0,  # Default for now
                'active_sessions': active_sessions,
                'last_activity': employee_data[0]['last_checkin'] if employee_data else 'N/A'
            },
            'employees': employee_data
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def admin_location_analytics(request):
    """CEO location analytics and insights"""
    from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField
    from datetime import datetime, timedelta
    import json
    
    # Get filter parameters
    time_period = int(request.GET.get('time_period', 30))  # days
    department_filter = request.GET.get('department_filter', '')
    location_filter = request.GET.get('location_filter', '')
    
    # Calculate date range
    end_date = timezone.localdate()
    if time_period == 7:
        start_date = end_date - timedelta(days=7)
    elif time_period == 90:
        start_date = end_date - timedelta(days=90)
    elif time_period == 365:
        start_date = end_date - timedelta(days=365)
    else:  # 30 days default
        start_date = end_date - timedelta(days=30)
    
    # Base queryset for checkins
    checkins_qs = GPSCheckIn.objects.filter(
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date
    )
    
    # Apply department filter
    if department_filter:
        checkins_qs = checkins_qs.filter(employee__department_id=department_filter)
    
    # Calculate key metrics
    total_checkins = checkins_qs.count()
    
    # Average hours calculation - calculate duration in database
    completed_checkins = checkins_qs.filter(check_out_time__isnull=False)
    
    # Calculate average duration using database expressions
    duration_expression = ExpressionWrapper(
        F('check_out_time') - F('check_in_time'),
        output_field=DurationField()
    )
    
    avg_duration_result = completed_checkins.aggregate(
        avg_duration=Avg(duration_expression)
    )['avg_duration']
    
    # Convert to hours
    avg_hours = 0
    if avg_duration_result:
        avg_hours = avg_duration_result.total_seconds() / 3600
    
    # Current active checkins
    current_checkins = GPSCheckIn.objects.filter(
        check_in_time__date=end_date,
        check_out_time__isnull=True
    ).count()
    
    # Completion rate (percentage of checkins that have checkout)
    completion_rate = 0
    if total_checkins > 0:
        completed_count = completed_checkins.count()
        completion_rate = (completed_count / total_checkins) * 100
    
    # Top performing employees with proper duration calculation
    duration_expression = ExpressionWrapper(
        F('gps_checkins__check_out_time') - F('gps_checkins__check_in_time'),
        output_field=DurationField()
    )
    
    active_employees = Employee.objects.annotate(
        checkin_count=Count('gps_checkins', filter=Q(
            gps_checkins__check_in_time__date__gte=start_date,
            gps_checkins__check_in_time__date__lte=end_date
        )),
        avg_duration_seconds=Avg(duration_expression, filter=Q(
            gps_checkins__check_in_time__date__gte=start_date,
            gps_checkins__check_in_time__date__lte=end_date,
            gps_checkins__check_out_time__isnull=False
        )),
        location_count=Count('gps_tracks', filter=Q(
            gps_tracks__timestamp__date__gte=start_date,
            gps_tracks__timestamp__date__lte=end_date
        ), distinct=True)
    ).filter(checkin_count__gt=0).order_by('-checkin_count')[:10]
    
    # Convert duration from seconds to hours for each employee
    for employee in active_employees:
        if employee.avg_duration_seconds:
            employee.avg_duration = employee.avg_duration_seconds.total_seconds() / 3600
        else:
            employee.avg_duration = 0
    
    # Location usage analysis
    office_geofences = EmployeeGeofence.objects.filter(
        fence_type='OFFICE',
        is_active=True
    ).values_list('id', flat=True)
    
    field_geofences = EmployeeGeofence.objects.filter(
        fence_type='FIELD',
        is_active=True
    ).values_list('id', flat=True)
    
    # Categorize checkins by location type
    office_checkins = 0
    field_checkins = 0
    remote_checkins = 0
    
    for checkin in checkins_qs.select_related('employee'):
        # Check if checkin location matches any geofence
        is_office = False
        is_field = False
        
        if checkin.check_in_latitude and checkin.check_in_longitude:
            for geofence_id in office_geofences:
                try:
                    geofence = EmployeeGeofence.objects.get(id=geofence_id)
                    if is_in_geofence(checkin.check_in_latitude, checkin.check_in_longitude, geofence):
                        is_office = True
                        break
                except EmployeeGeofence.DoesNotExist:
                    continue
            
            if not is_office:
                for geofence_id in field_geofences:
                    try:
                        geofence = EmployeeGeofence.objects.get(id=geofence_id)
                        if is_in_geofence(checkin.check_in_latitude, checkin.check_in_longitude, geofence):
                            is_field = True
                            break
                    except EmployeeGeofence.DoesNotExist:
                        continue
        
        if is_office:
            office_checkins += 1
        elif is_field:
            field_checkins += 1
        else:
            remote_checkins += 1
    
    # Department statistics for charts
    department_stats = Department.objects.annotate(
        checkin_count=Count('employee__gps_checkins', filter=Q(
            employee__gps_checkins__check_in_time__date__gte=start_date,
            employee__gps_checkins__check_in_time__date__lte=end_date
        ))
    ).filter(checkin_count__gt=0).order_by('-checkin_count')[:10]
    
    # Attendance trends data (daily checkins for the period)
    daily_checkins = {}
    current_date = start_date
    while current_date <= end_date:
        daily_count = checkins_qs.filter(check_in_time__date=current_date).count()
        daily_checkins[current_date.strftime('%Y-%m-%d')] = daily_count
        current_date += timedelta(days=1)
    
    # Prepare chart data
    chart_data = {
        'attendance_trends': {
            'labels': list(daily_checkins.keys()),
            'data': list(daily_checkins.values())
        },
        'department_distribution': {
            'labels': [dept.name for dept in department_stats],
            'data': [dept.checkin_count for dept in department_stats]
        },
        'location_usage': {
            'labels': ['Office', 'Field', 'Remote'],
            'data': [office_checkins, field_checkins, remote_checkins]
        }
    }
    
    top_departments = Department.objects.all()
    
    context = {
        'total_checkins': total_checkins,
        'avg_hours': avg_hours,
        'current_checkins': current_checkins,
        'avg_checkout_duration': completion_rate,
        'active_employees': active_employees,
        'office_checkins': office_checkins,
        'field_checkins': field_checkins,
        'remote_checkins': remote_checkins,
        'top_departments': top_departments,
        'department_stats': department_stats,
        'chart_data': json.dumps(chart_data),
        'time_period': time_period,
        'department_filter': department_filter,
        'location_filter': location_filter,
        'start_date': start_date,
        'end_date': end_date,
        'page_title': 'Location Analytics',
    }
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format in ['csv', 'excel', 'pdf']:
        return export_analytics_data(request, export_format, context)
    
    return render(request, 'ceo_template/location_analytics.html', context)


def export_analytics_data(request, format_type, context):
    """Export analytics data in various formats"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="location_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write summary data
        writer.writerow(['Location Analytics Report'])
        writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Time Period:', f"{context['start_date']} to {context['end_date']}"])
        writer.writerow([])
        
        # Write key metrics
        writer.writerow(['Key Metrics'])
        writer.writerow(['Total Check-ins', context['total_checkins']])
        writer.writerow(['Average Hours', f"{context['avg_hours']:.1f}"])
        writer.writerow(['Currently Active', context['current_checkins']])
        writer.writerow(['Completion Rate', f"{context['avg_checkout_duration']:.1f}%"])
        writer.writerow([])
        
        # Write location usage
        writer.writerow(['Location Usage'])
        writer.writerow(['Office Check-ins', context['office_checkins']])
        writer.writerow(['Field Check-ins', context['field_checkins']])
        writer.writerow(['Remote Check-ins', context['remote_checkins']])
        writer.writerow([])
        
        # Write top performers
        writer.writerow(['Top Performing Employees'])
        writer.writerow(['Name', 'Department', 'Check-ins', 'Avg Duration (hrs)', 'GPS Points'])
        for employee in context['active_employees']:
            writer.writerow([
                f"{employee.admin.first_name} {employee.admin.last_name}",
                employee.department.name if employee.department else 'No Department',
                employee.checkin_count or 0,
                f"{employee.avg_duration:.1f}" if hasattr(employee, 'avg_duration') and employee.avg_duration else '0.0',
                employee.location_count or 0
            ])
        
        return response
    
    elif format_type == 'excel':
        # For Excel export, you would use openpyxl or xlsxwriter
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="location_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Placeholder - would implement Excel export here
        response.write(b'Excel export not yet implemented')
        return response
    
    elif format_type == 'pdf':
        # For PDF export, you would use reportlab or weasyprint
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="location_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        # Placeholder - would implement PDF export here
        response.write(b'PDF export not yet implemented')
        return response
    
    return HttpResponse('Invalid export format', status=400)


@login_required
def admin_gps_employee_details(request, employee_id):
    """Detailed GPS view for specific employee - Admin only"""
    from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField
    from datetime import datetime, timedelta
    import json
    
    # Security check - only admin/CEO can access
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('admin_home')
    
    try:
        employee = get_object_or_404(Employee, id=employee_id)
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('admin_gps_dashboard')
    
    # Get date range (default: last 30 days)
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=30)
    
    # Get filter parameters
    date_filter = request.GET.get('date_range', '30')
    if date_filter == '7':
        start_date = end_date - timedelta(days=7)
    elif date_filter == '90':
        start_date = end_date - timedelta(days=90)
    
    # Employee's GPS check-ins
    checkins = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date
    ).order_by('-check_in_time')[:50]
    
    # Calculate statistics
    total_checkins = checkins.count()
    completed_checkins = checkins.filter(check_out_time__isnull=False)
    
    # Average duration calculation
    duration_expression = ExpressionWrapper(
        F('check_out_time') - F('check_in_time'),
        output_field=DurationField()
    )
    
    avg_duration_result = completed_checkins.aggregate(
        avg_duration=Avg(duration_expression)
    )['avg_duration']
    
    avg_hours = 0
    if avg_duration_result:
        avg_hours = avg_duration_result.total_seconds() / 3600
    
    # Recent GPS tracks
    recent_tracks = GPSTrack.objects.filter(
        employee=employee,
        timestamp__date__gte=start_date
    ).order_by('-timestamp')[:20]
    
    # Active session
    active_session = GPSSession.objects.filter(
        employee=employee,
        is_active=True
    ).first()
    
    # Today's status
    today_checkin = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date=end_date
    ).first()
    
    # Performance metrics
    on_time_checkins = 0  # Would calculate based on work schedule
    late_checkins = 0
    
    # Geofence compliance
    geofence_violations = 0  # Would calculate based on geofence rules
    
    # Prepare chart data for location history
    daily_activity = {}
    for i in range(7):  # Last 7 days
        date = end_date - timedelta(days=i)
        daily_checkins = checkins.filter(check_in_time__date=date).count()
        daily_activity[date.strftime('%Y-%m-%d')] = daily_checkins
    
    chart_data = {
        'daily_activity': {
            'labels': list(daily_activity.keys()),
            'data': list(daily_activity.values())
        }
    }
    
    context = {
        'employee': employee,
        'checkins': checkins,
        'recent_tracks': recent_tracks,
        'active_session': active_session,
        'today_checkin': today_checkin,
        'total_checkins': total_checkins,
        'completed_checkins': completed_checkins.count(),
        'avg_hours': avg_hours,
        'on_time_checkins': on_time_checkins,
        'late_checkins': late_checkins,
        'geofence_violations': geofence_violations,
        'chart_data': json.dumps(chart_data),
        'date_filter': date_filter,
        'start_date': start_date,
        'end_date': end_date,
        'page_title': f'GPS Details - {employee.admin.first_name} {employee.admin.last_name}',
    }
    
    return render(request, 'ceo_template/gps_employee_details.html', context)


@login_required
def admin_geofence_management(request):
    """CEO geofence management"""
    from django.db.models import Avg
    
    if request.method == 'POST':
        # Handle geofence creation/updates
        action = request.POST.get('action')
        
        if action == 'create':
            try:
                geofence = EmployeeGeofence.objects.create(
                    name=request.POST.get('name'),
                    fence_type=request.POST.get('fence_type'),
                    center_latitude=float(request.POST.get('center_latitude')),
                    center_longitude=float(request.POST.get('center_longitude')),
                    radius_meters=int(request.POST.get('radius_meters', 100)),
                    department_id=request.POST.get('department_id') if request.POST.get('department_id') else None,
                    allow_checkin=request.POST.get('allow_checkin') == 'on',
                    allow_checkout=request.POST.get('allow_checkout') == 'on'
                )
                messages.success(request, f'Geofence "{geofence.name}" created successfully!')
            except Exception as e:
                messages.error(request, f'Error creating geofence: {str(e)}')
        
        elif action == 'update':
            try:
                geofence_id = request.POST.get('geofence_id')
                geofence = get_object_or_404(EmployeeGeofence, id=geofence_id)
                
                geofence.name = request.POST.get('name')
                geofence.fence_type = request.POST.get('fence_type')
                geofence.center_latitude = float(request.POST.get('center_latitude'))
                geofence.center_longitude = float(request.POST.get('center_longitude'))
                geofence.radius_meters = int(request.POST.get('radius_meters', 100))
                geofence.department_id = request.POST.get('department_id') if request.POST.get('department_id') else None
                geofence.allow_checkin = request.POST.get('allow_checkin') == 'on'
                geofence.allow_checkout = request.POST.get('allow_checkout') == 'on'
                geofence.is_active = request.POST.get('is_active') == 'on'
                geofence.save()
                
                messages.success(request, f'Geofence "{geofence.name}" updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating geofence: {str(e)}')
        
        elif action == 'delete':
            try:
                geofence_id = request.POST.get('geofence_id')
                geofence = get_object_or_404(EmployeeGeofence, id=geofence_id)
                geofence_name = geofence.name
                geofence.delete()
                messages.success(request, f'Geofence "{geofence_name}" deleted successfully!')
            except Exception as e:
                messages.error(request, f'Error deleting geofence: {str(e)}')
        
        return redirect('admin_geofence_management')
    
    # Get geofence data
    geofences = EmployeeGeofence.objects.all().select_related('department', 'city')
    active_locations = geofences.filter(is_active=True).count()
    total_geofence_usage = GPSCheckIn.objects.filter(
        check_in_time__date__gte=timezone.localdate() - timedelta(days=30)
    ).count()
    avg_radius = geofences.aggregate(Avg('radius_meters'))['radius_meters__avg'] or 100
    
    # Get departments for dropdown
    departments = Department.objects.all().select_related('division')
    
    context = {
        'geofences': geofences,
        'departments': departments,
        'active_locations': active_locations,
        'total_geofence_usage': total_geofence_usage,
        'avg_radius': round(avg_radius),
        'page_title': 'Geofence Management',
    }
    
    return render(request, 'ceo_template/geofence_management.html', context)


# ======================================
# GPS API Endpoints
# ======================================

@csrf_exempt
@login_required
def api_gps_checkin(request):
    """API endpoint for GPS check-in"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        employee = get_object_or_404(Employee, admin=request.user)
        
        # Handle both JSON and FormData requests
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8')) if request.body else {}
            except json.JSONDecodeError:
                data = {}
        else:
            # FormData request (from our check-in form)
            data = request.POST
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        work_summary = data.get('work_summary', '')
        geofence_id = data.get('geofence_id')
        
        # Validate required GPS data
        if not latitude or not longitude:
            return JsonResponse({'error': 'GPS coordinates (latitude/longitude) are required'}, status=400)
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid GPS coordinates. Please ensure numbers are provided.'}, status=400)
        
        # Check if employee already checked in today
        today = timezone.localdate()
        existing_checkin = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date=today
        ).first()
        
        if existing_checkin:
            return JsonResponse({'error': 'You have already checked in today'}, status=400)
        
        # Validate geofence if provided
        geofence = None
        if geofence_id:
            geofence = get_object_or_404(EmployeeGeofence, id=geofence_id)
            
            # Calculate distance from geofence center
            distance = calculate_distance(
                float(geofence.center_latitude),
                float(geofence.center_longitude),
                latitude,
                longitude
            )
            
            if distance > geofence.radius_meters:
                return JsonResponse({
                    'error': f'You must be within {geofence.radius_meters}m of {geofence.name}'
                }, status=400)
        
        # Get address from coordinates
        address = get_address_from_coords(latitude, longitude)
        
        # Create check-in record in database
        checkin = GPSCheckIn.objects.create(
            employee=employee,
            check_in_time=timezone.now(),
            check_in_latitude=latitude,
            check_in_longitude=longitude,
            check_in_address=address,
            work_summary=work_summary
        )
        
        # Start a GPS session
        GPSSession.objects.create(
            employee=employee,
            session_type='WORK',
            start_latitude=latitude,
            start_longitude=longitude,
            notes=f"Check-in session for {checkin.id}"
        )
        
        # Create initial GPS track
        GPSTrack.objects.create(
            employee=employee,
            latitude=latitude,
            longitude=longitude,
            address=address,
            status='CHECKED_IN'
        )
        
        return JsonResponse({
            'success': True,
            'checkin_id': checkin.id,
            'message': 'Check-in successful! GPS tracking started.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
def api_gps_checkout(request):
    """API endpoint for GPS check-out"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        employee = get_object_or_404(Employee, admin=request.user)
        today = timezone.localdate()
        
        # Check for today's active check-in
        active_checkin = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date=today,
            check_out_time__isnull=True
        ).first()
        
        if not active_checkin:
            return JsonResponse({'error': 'No active check-in found. Please check in first.'}, status=400)
        
        # Handle both JSON and FormData requests
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8')) if request.body else {}
            except json.JSONDecodeError:
                data = {}
        else:
            # FormData request (from our check-in form)
            data = request.POST
        
        checkout_time = timezone.now()
        work_summary = data.get('work_summary', active_checkin.work_summary or '')
        latitude = float(data.get('latitude', active_checkin.check_in_latitude))
        longitude = float(data.get('longitude', active_checkin.check_in_longitude))
        
        # Get address from coordinates
        address = get_address_from_coords(latitude, longitude)
        
        # Update check-in record with checkout information
        active_checkin.check_out_time = checkout_time
        active_checkin.check_out_latitude = latitude
        active_checkin.check_out_longitude = longitude
        active_checkin.check_out_address = address
        active_checkin.work_summary = work_summary
        active_checkin.save()
        
        # End active GPS sessions
        GPSSession.objects.filter(
            employee=employee,
            is_active=True
        ).update(
            is_active=False,
            end_time=checkout_time,
            end_latitude=latitude,
            end_longitude=longitude
        )
        
        # Create final GPS track
        GPSTrack.objects.create(
            employee=employee,
            latitude=latitude,
            longitude=longitude,
            address=address,
            status='CHECKED_OUT'
        )
        
        return JsonResponse({
            'success': True,
            'checkout_id': active_checkin.id,
            'duration_hours': round(active_checkin.duration_hours or 0, 2),
            'message': 'Checkout successful! Work session completed.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
def api_gps_location_update(request):
    """API endpoint for GPS location updates"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        employee = get_object_or_404(Employee, admin=request.user)
        
        # Handle both JSON and FormData requests
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        else:
            data = request.POST
        
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        accuracy = float(data.get('accuracy', 0))
        speed = float(data.get('speed', 0))
        battery = int(data.get('battery', 100))
        heading = float(data.get('heading', 0))
        
        # Get address from coordinates
        address = get_address_from_coords(latitude, longitude)
        
        # Determine status based on active check-in
        today = timezone.localdate()
        active_checkin = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date=today,
            check_out_time__isnull=True
        ).first()
        
        status = 'WORKING' if active_checkin else 'CHECKED_OUT'
        
        # Create GPS track record
        track = GPSTrack.objects.create(
            employee=employee,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            battery_level=battery,
            status=status,
            address=address
        )
        
        # Update user status
        user_status, created = UserStatus.objects.get_or_create(
            user=employee.admin,
            defaults={'status_type': 'online', 'is_checked_in': bool(active_checkin)}
        )
        user_status.status_type = 'online'
        user_status.is_checked_in = bool(active_checkin)
        user_status.save()
        
        # Check geofence violations if employee is checked in
        geofence_alerts = []
        if active_checkin:
            geofences = EmployeeGeofence.objects.filter(
                department=employee.department,
                is_active=True
            )
            
            for geofence in geofences:
                distance = calculate_distance(
                    latitude, longitude,
                    float(geofence.center_latitude),
                    float(geofence.center_longitude)
                )
                
                if distance > geofence.radius_meters:
                    geofence_alerts.append({
                        'type': 'outside_geofence',
                        'message': f'Employee is {distance:.0f}m outside {geofence.name}',
                        'geofence': geofence.name,
                        'distance': distance
                    })
        
        response_data = {
            'success': True,
            'track_id': track.id,
            'status': status,
            'address': address
        }
        
        if geofence_alerts:
            response_data['alerts'] = geofence_alerts
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_employee_current_location(request):
    """API endpoint to get employee's current location"""
    employee_id = request.GET.get('employee_id')
    
    if not employee_id:
        return JsonResponse({'error': 'Employee ID required'}, status=400)
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Check if requesting user has permission to view this employee's location
    if request.user.user_type == '2':  # Manager
        try:
            manager = Manager.objects.get(admin=request.user)
            if employee.division != manager.division:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        except Manager.DoesNotExist:
            return JsonResponse({'error': 'Manager profile not found'}, status=403)
    elif request.user.user_type == '3':  # Employee
        # Employees can only see their own location
        if employee.admin != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    # Admin (user_type == '1') can see all locations
    
    # Get latest GPS track
    latest_track = GPSTrack.objects.filter(
        employee=employee
    ).order_by('-timestamp').first()
    
    if not latest_track:
        return JsonResponse({'error': 'No location data found'}, status=404)
    
    # Get today's check-in status
    today = timezone.localdate()
    active_checkin = GPSCheckIn.objects.filter(
        employee=employee,
        check_in_time__date=today,
        check_out_time__isnull=True
    ).first()
    
    return JsonResponse({
        'employee_id': employee.id,
        'employee_name': f"{employee.admin.first_name} {employee.admin.last_name}",
        'department': employee.department.name if employee.department else 'No Department',
        'division': employee.division.name if employee.division else 'No Division',
        'latitude': float(latest_track.latitude),
        'longitude': float(latest_track.longitude),
        'address': latest_track.address,
        'timestamp': latest_track.timestamp.isoformat(),
        'speed': latest_track.speed,
        'heading': latest_track.heading,
        'accuracy': latest_track.accuracy,
        'battery_level': latest_track.battery_level,
        'status': latest_track.get_status_display(),
        'is_checked_in': bool(active_checkin),
        'check_in_time': active_checkin.check_in_time.isoformat() if active_checkin else None,
        'work_summary': active_checkin.work_summary if active_checkin else ''
    })


# ======================================
# Utility Functions
# ======================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters"""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon/2) * math.sin(delta_lon/2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def get_address_from_coords(latitude, longitude):
    """Get address from coordinates (reverse geocoding)"""
    # This is a placeholder - you would integrate with a real geocoding service
    # like Google Geocoding API, OpenStreetMap Nominatim, or similar
    return f"Location: {latitude:.6f}, {longitude:.6f}"


def is_in_geofence(latitude, longitude, geofence):
    """Check if coordinates are within a geofence"""
    distance = calculate_distance(
        float(geofence.center_latitude),
        float(geofence.center_longitude),
        latitude,
        longitude
    )
    return distance <= geofence.radius_meters


# ======================================
# Additional Real-Time GPS API Endpoints
# ======================================

@login_required
def api_team_locations(request):
    """API endpoint to get all team member locations for managers/admins"""
    try:
        # Check user permissions
        if request.user.user_type == '2':  # Manager
            try:
                manager = Manager.objects.get(admin=request.user)
                employees = Employee.objects.filter(division=manager.division)
            except Manager.DoesNotExist:
                return JsonResponse({'error': 'Manager profile not found'}, status=403)
        elif request.user.user_type == '1':  # Admin/CEO
            employees = Employee.objects.all()
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get latest location for each employee
        team_locations = []
        today = timezone.localdate()
        
        for employee in employees:
            # Get latest GPS track
            latest_track = GPSTrack.objects.filter(
                employee=employee
            ).order_by('-timestamp').first()
            
            if latest_track:
                # Get today's check-in status
                active_checkin = GPSCheckIn.objects.filter(
                    employee=employee,
                    check_in_time__date=today,
                    check_out_time__isnull=True
                ).first()
                
                team_locations.append({
                    'employee_id': employee.id,
                    'employee_name': f"{employee.admin.first_name} {employee.admin.last_name}",
                    'department': employee.department.name if employee.department else 'No Department',
                    'latitude': float(latest_track.latitude),
                    'longitude': float(latest_track.longitude),
                    'address': latest_track.address,
                    'timestamp': latest_track.timestamp.isoformat(),
                    'speed': latest_track.speed,
                    'accuracy': latest_track.accuracy,
                    'battery_level': latest_track.battery_level,
                    'status': latest_track.get_status_display(),
                    'is_checked_in': bool(active_checkin),
                    'last_update_minutes': int((timezone.now() - latest_track.timestamp).total_seconds() / 60)
                })
        
        return JsonResponse({
            'success': True,
            'team_locations': team_locations,
            'total_employees': len(team_locations),
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_employee_route_history(request):
    """API endpoint to get employee's route history for a specific date"""
    try:
        employee_id = request.GET.get('employee_id')
        date_str = request.GET.get('date', timezone.localdate().isoformat())
        
        if not employee_id:
            return JsonResponse({'error': 'Employee ID required'}, status=400)
        
        employee = get_object_or_404(Employee, id=employee_id)
        
        # Check permissions
        if request.user.user_type == '2':  # Manager
            try:
                manager = Manager.objects.get(admin=request.user)
                if employee.division != manager.division:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            except Manager.DoesNotExist:
                return JsonResponse({'error': 'Manager profile not found'}, status=403)
        elif request.user.user_type == '3':  # Employee
            if employee.admin != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Get GPS tracks for the date
        tracks = GPSTrack.objects.filter(
            employee=employee,
            timestamp__date=target_date
        ).order_by('timestamp')
        
        # Get check-in/check-out for the date
        checkin = GPSCheckIn.objects.filter(
            employee=employee,
            check_in_time__date=target_date
        ).first()
        
        route_points = []
        for track in tracks:
            route_points.append({
                'latitude': float(track.latitude),
                'longitude': float(track.longitude),
                'timestamp': track.timestamp.isoformat(),
                'address': track.address,
                'speed': track.speed,
                'accuracy': track.accuracy,
                'status': track.get_status_display()
            })
        
        return JsonResponse({
            'success': True,
            'employee_name': f"{employee.admin.first_name} {employee.admin.last_name}",
            'date': target_date.isoformat(),
            'route_points': route_points,
            'total_points': len(route_points),
            'check_in_time': checkin.check_in_time.isoformat() if checkin else None,
            'check_out_time': checkin.check_out_time.isoformat() if checkin and checkin.check_out_time else None,
            'work_summary': checkin.work_summary if checkin else '',
            'duration_hours': checkin.duration_hours if checkin else 0
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_geofence_status(request):
    """API endpoint to check geofence status for all active employees"""
    try:
        # Check permissions (managers and admins only)
        if request.user.user_type == '2':  # Manager
            try:
                manager = Manager.objects.get(admin=request.user)
                employees = Employee.objects.filter(division=manager.division)
            except Manager.DoesNotExist:
                return JsonResponse({'error': 'Manager profile not found'}, status=403)
        elif request.user.user_type == '1':  # Admin/CEO
            employees = Employee.objects.all()
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        today = timezone.localdate()
        geofence_status = []
        
        # Get employees who are currently checked in
        active_checkins = GPSCheckIn.objects.filter(
            employee__in=employees,
            check_in_time__date=today,
            check_out_time__isnull=True
        ).select_related('employee', 'employee__admin', 'employee__department')
        
        for checkin in active_checkins:
            employee = checkin.employee
            
            # Get latest location
            latest_track = GPSTrack.objects.filter(
                employee=employee
            ).order_by('-timestamp').first()
            
            if latest_track:
                # Check geofences for this employee's department
                geofences = EmployeeGeofence.objects.filter(
                    department=employee.department,
                    is_active=True
                )
                
                employee_geofence_status = {
                    'employee_id': employee.id,
                    'employee_name': f"{employee.admin.first_name} {employee.admin.last_name}",
                    'department': employee.department.name if employee.department else 'No Department',
                    'latitude': float(latest_track.latitude),
                    'longitude': float(latest_track.longitude),
                    'timestamp': latest_track.timestamp.isoformat(),
                    'geofence_violations': []
                }
                
                for geofence in geofences:
                    distance = calculate_distance(
                        float(latest_track.latitude),
                        float(latest_track.longitude),
                        float(geofence.center_latitude),
                        float(geofence.center_longitude)
                    )
                    
                    is_inside = distance <= geofence.radius_meters
                    
                    if not is_inside:
                        employee_geofence_status['geofence_violations'].append({
                            'geofence_name': geofence.name,
                            'geofence_type': geofence.get_fence_type_display(),
                            'distance_from_center': round(distance),
                            'allowed_radius': geofence.radius_meters,
                            'violation_distance': round(distance - geofence.radius_meters)
                        })
                
                geofence_status.append(employee_geofence_status)
        
        return JsonResponse({
            'success': True,
            'geofence_status': geofence_status,
            'total_active_employees': len(geofence_status),
            'employees_with_violations': len([emp for emp in geofence_status if emp['geofence_violations']]),
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
