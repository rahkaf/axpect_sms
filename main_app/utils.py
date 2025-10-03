"""
Utility functions for the staff management system
"""
from typing import Tuple, List, Dict, Any
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Attendance, Department


def get_home_for_user_type(user_type: str) -> str:
    """Helper function to get appropriate home URL for user type"""
    home_urls = {
        '1': 'admin_home',
        '2': 'manager_home',
        '3': 'employee_home'
    }
    return home_urls.get(user_type, 'employee_home')


def redirect_to_user_home(user_type: str):
    """Redirect user to their appropriate home page"""
    return redirect(reverse(get_home_for_user_type(user_type)))


def get_attendance_stats(departments) -> Tuple[List[str], List[int]]:
    """
    Get attendance statistics for a list of departments
    Returns department names and their attendance counts
    """
    department_list = []
    attendance_list = []
    
    for department in departments:
        attendance_count = Attendance.objects.filter(department=department).count()
        department_list.append(department.name[:7] if len(department.name) > 7 else department.name)
        attendance_list.append(attendance_count)
    
    return department_list, attendance_list


def validate_required_fields(request, fields: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that required fields are present in request
    Returns (is_valid, missing_fields)
    """
    missing_fields = []
    for field in fields:
        if not request.POST.get(field):
            missing_fields.append(field)
    
    return len(missing_fields) == 0, {
        'missing_fields': missing_fields,
        'message': f"Missing required fields: {', '.join(missing_fields)}"
    }


def add_error_message(request, message: str):
    """Convenience function to add error message"""
    messages.error(request, message)


def add_success_message(request, message: str):
    """Convenience function to add success message"""
    messages.success(request, message)


def add_warning_message(request, message: str):
    """Convenience function to add warning message"""
    messages.warning(request, message)


def safe_get_or_create(model_class, **kwargs):
    """
    Safely create or get an object, with proper error handling
    Returns tuple: (object, created, error)
    """
    try:
        obj, created = model_class.objects.get_or_create(**kwargs)
        return obj, created, None
    except Exception as e:
        return None, False, str(e)


def format_user_display_name(user) -> str:
    """
    Format user display name consistently across the application
    """
    if not user:
        return "Unknown User"
    
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    
    if first_name and last_name:
        return f"{first_name} {last_name}".strip()
    elif first_name:
        return first_name
    elif last_name:
        return last_name
    else:
        return user.email or "Unknown User"
