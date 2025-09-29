from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
import json

from .models import *
from .forms import JobCardForm, JobCardUpdateForm, JobCardCommentForm, JobCardTimeLogForm


# ===============================
# ADMIN JOB CARD VIEWS
# ===============================

@login_required
def admin_job_card_dashboard(request):
    """Admin dashboard for managing all job cards"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    assigned_to_filter = request.GET.get('assigned_to', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    job_cards = JobCard.objects.all().select_related('assigned_to', 'assigned_by', 'customer')
    
    # Apply filters
    if status_filter:
        job_cards = job_cards.filter(status=status_filter)
    if priority_filter:
        job_cards = job_cards.filter(priority=priority_filter)
    if assigned_to_filter:
        job_cards = job_cards.filter(assigned_to_id=assigned_to_filter)
    if search_query:
        job_cards = job_cards.filter(
            Q(description__icontains=search_query) |
            Q(type__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(job_cards, 20)
    page_number = request.GET.get('page')
    job_cards_page = paginator.get_page(page_number)
    
    # Statistics
    total_job_cards = JobCard.objects.count()
    active_job_cards = JobCard.objects.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    completed_job_cards = JobCard.objects.filter(status='COMPLETED').count()
    overdue_job_cards = JobCard.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()
    
    # Get users for assignment filter
    users = CustomUser.objects.filter(user_type__in=['2', '3']).order_by('first_name', 'last_name')
    
    context = {
        'page_title': 'Admin Job Card Dashboard',
        'job_cards': job_cards_page,
        'total_job_cards': total_job_cards,
        'active_job_cards': active_job_cards,
        'completed_job_cards': completed_job_cards,
        'overdue_job_cards': overdue_job_cards,
        'users': users,
        'status_choices': JobCard.STATUS_CHOICES,
        'priority_choices': JobCard.PRIORITY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'assigned_to': assigned_to_filter,
            'search': search_query,
        }
    }
    return render(request, 'ceo_template/job_card_dashboard.html', context)


@login_required
def admin_create_job_card(request):
    """Admin view to create new job cards"""
    if request.user.user_type != '1':
        messages.error(request, "Access denied. Only administrators can access this page.")
        return redirect('login_page')
    
    if request.method == 'POST':
        form = JobCardForm(request.POST, user=request.user)
        if form.is_valid():
            job_card = form.save(commit=False)
            job_card.assigned_by = request.user
            job_card.status = 'PENDING'
            job_card.save()
            
            messages.success(request, f'Job Card {job_card.job_card_number} created successfully!')
            return redirect('admin_job_card_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JobCardForm(user=request.user)
    
    context = {
        'page_title': 'Create Job Card',
        'form': form,
        'form_action': 'Create'
    }
    return render(request, 'ceo_template/job_card_form.html', context)


# ===============================
# MANAGER JOB CARD VIEWS
# ===============================

@login_required
def manager_job_card_dashboard(request):
    """Manager dashboard for managing job cards in their division"""
    if request.user.user_type != '2':
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    try:
        manager = Manager.objects.get(admin=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect('login_page')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset - job cards assigned by this manager or to employees in their division
    job_cards = JobCard.objects.filter(
        Q(assigned_by=request.user) |
        Q(assigned_to__division=manager.division)
    ).select_related('assigned_to', 'assigned_by', 'customer').distinct()
    
    # Apply filters
    if status_filter:
        job_cards = job_cards.filter(status=status_filter)
    if priority_filter:
        job_cards = job_cards.filter(priority=priority_filter)
    if search_query:
        job_cards = job_cards.filter(
            Q(description__icontains=search_query) |
            Q(type__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(job_cards, 20)
    page_number = request.GET.get('page')
    job_cards_page = paginator.get_page(page_number)
    
    # Statistics
    total_job_cards = job_cards.count()
    active_job_cards = job_cards.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    completed_job_cards = job_cards.filter(status='COMPLETED').count()
    overdue_job_cards = job_cards.filter(
        due_date__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()
    
    context = {
        'page_title': 'Manager Job Card Dashboard',
        'job_cards': job_cards_page,
        'total_job_cards': total_job_cards,
        'active_job_cards': active_job_cards,
        'completed_job_cards': completed_job_cards,
        'overdue_job_cards': overdue_job_cards,
        'status_choices': JobCard.STATUS_CHOICES,
        'priority_choices': JobCard.PRIORITY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'search': search_query,
        }
    }
    return render(request, 'manager_template/job_card_dashboard.html', context)


@login_required
def manager_create_job_card(request):
    """Manager view to create new job cards for employees in their division"""
    if request.user.user_type != '2':
        messages.error(request, "Access denied. Only managers can access this page.")
        return redirect('login_page')
    
    if request.method == 'POST':
        form = JobCardForm(request.POST, user=request.user)
        if form.is_valid():
            job_card = form.save(commit=False)
            job_card.assigned_by = request.user
            job_card.status = 'PENDING'
            job_card.save()
            
            messages.success(request, f'Job Card {job_card.job_card_number} created successfully!')
            return redirect('manager_job_card_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JobCardForm(user=request.user)
    
    context = {
        'page_title': 'Create Job Card',
        'form': form,
        'form_action': 'Create'
    }
    return render(request, 'manager_template/job_card_form.html', context)


# ===============================
# EMPLOYEE JOB CARD VIEWS
# ===============================

@login_required
def employee_job_card_dashboard(request):
    """Employee dashboard to view assigned job cards"""
    if request.user.user_type != '3':
        messages.error(request, "Access denied. Only employees can access this page.")
        return redirect('login_page')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    
    # Base queryset - job cards assigned to this employee
    try:
        employee = request.user.employee
        job_cards = JobCard.objects.filter(
            assigned_to=employee
        ).select_related('assigned_by', 'customer')
    except AttributeError:
        # User doesn't have an employee profile
        job_cards = JobCard.objects.none()
    
    # Apply filters
    if status_filter:
        job_cards = job_cards.filter(status=status_filter)
    if priority_filter:
        job_cards = job_cards.filter(priority=priority_filter)
    
    # Pagination
    paginator = Paginator(job_cards, 15)
    page_number = request.GET.get('page')
    job_cards_page = paginator.get_page(page_number)
    
    # Statistics
    total_job_cards = job_cards.count()
    active_job_cards = job_cards.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    completed_job_cards = job_cards.filter(status='COMPLETED').count()
    overdue_job_cards = job_cards.filter(
        due_date__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()
    
    context = {
        'page_title': 'My Job Cards',
        'job_cards': job_cards_page,
        'total_job_cards': total_job_cards,
        'active_job_cards': active_job_cards,
        'completed_job_cards': completed_job_cards,
        'overdue_job_cards': overdue_job_cards,
        'status_choices': JobCard.STATUS_CHOICES,
        'priority_choices': JobCard.PRIORITY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
        }
    }
    return render(request, 'employee_template/job_card_dashboard.html', context)


# ===============================
# SHARED JOB CARD VIEWS
# ===============================

@login_required
def job_card_detail(request, job_card_id):
    """Detailed view of a specific job card"""
    job_card = get_object_or_404(JobCard, id=job_card_id)
    
    # Check permissions
    can_view = False
    can_edit = False
    
    if request.user.user_type == '1':  # Admin
        can_view = can_edit = True
    elif request.user.user_type == '2':  # Manager
        try:
            manager = Manager.objects.get(admin=request.user)
            can_view = (job_card.assigned_by == request.user or 
                       job_card.assigned_to.division == manager.division)
            can_edit = can_view
        except Manager.DoesNotExist:
            pass
    elif request.user.user_type == '3':  # Employee
        can_view = job_card.assigned_to.admin == request.user
        can_edit = can_view
    
    if not can_view:
        messages.error(request, "You don't have permission to view this job card.")
        return redirect('login_page')
    
    # Get comments and time logs (handle missing tables gracefully)
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_app_jobcardcomment';")
            if cursor.fetchone():
                comments = job_card.comments.all()
            else:
                comments = []
    except Exception:
        comments = []
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_app_jobcardtimelog';")
            if cursor.fetchone():
                time_logs = job_card.time_logs.all()
            else:
                time_logs = []
    except Exception:
        time_logs = []
    
    # Handle form submissions
    if request.method == 'POST':
        if not can_edit:
            messages.error(request, "You don't have permission to edit this job card.")
            return redirect('job_card_detail', job_card_id=job_card_id)
        
        form_type = request.POST.get('form_type')
        
        if form_type == 'update':
            form = JobCardUpdateForm(request.POST, instance=job_card, user=request.user)
            if form.is_valid():
                updated_job_card = form.save()
                # Note: completed_date and started_date fields don't exist in database
                messages.success(request, 'Job card updated successfully!')
                return redirect('job_card_detail', job_card_id=job_card_id)
        
        elif form_type == 'comment':
            try:
                comment_form = JobCardCommentForm(request.POST)
                if comment_form.is_valid():
                    comment = comment_form.save(commit=False)
                    comment.job_card = job_card
                    comment.user = request.user
                    comment.save()
                    messages.success(request, 'Comment added successfully!')
                    return redirect('job_card_detail', job_card_id=job_card_id)
            except Exception:
                messages.error(request, 'Comments feature is not available in this database.')
                return redirect('job_card_detail', job_card_id=job_card_id)
        
        elif form_type == 'time_log':
            try:
                time_log_form = JobCardTimeLogForm(request.POST)
                if time_log_form.is_valid():
                    time_log = time_log_form.save(commit=False)
                    time_log.job_card = job_card
                    time_log.user = request.user
                    time_log.save()
                    messages.success(request, 'Time log added successfully!')
                    return redirect('job_card_detail', job_card_id=job_card_id)
            except Exception:
                messages.error(request, 'Time logging feature is not available in this database.')
                return redirect('job_card_detail', job_card_id=job_card_id)
    
    # Initialize forms (handle missing models gracefully)
    update_form = JobCardUpdateForm(instance=job_card, user=request.user) if can_edit else None
    
    # Check if comment form should be available
    comment_form = None
    if can_edit:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_app_jobcardcomment';")
                if cursor.fetchone():
                    comment_form = JobCardCommentForm()
        except Exception:
            pass
    
    # Check if time log form should be available
    time_log_form = None
    if can_edit:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_app_jobcardtimelog';")
                if cursor.fetchone():
                    time_log_form = JobCardTimeLogForm()
        except Exception:
            pass
    
    context = {
        'page_title': f'Job Card - {job_card.job_card_number}',
        'job_card': job_card,
        'comments': comments,
        'time_logs': time_logs,
        'update_form': update_form,
        'comment_form': comment_form,
        'time_log_form': time_log_form,
        'can_edit': can_edit,
    }
    
    # Use different templates based on user type
    if request.user.user_type == '1':
        template = 'ceo_template/job_card_detail.html'
    elif request.user.user_type == '2':
        template = 'manager_template/job_card_detail.html'
    else:
        template = 'employee_template/job_card_detail.html'
    
    return render(request, template, context)


@csrf_exempt
@login_required
def update_job_card_status(request):
    """AJAX endpoint to update job card status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        job_card_id = data.get('job_card_id')
        new_status = data.get('status')
        
        job_card = get_object_or_404(JobCard, id=job_card_id)
        
        # Check permissions
        can_edit = False
        if request.user.user_type == '1':  # Admin
            can_edit = True
        elif request.user.user_type == '2':  # Manager
            try:
                manager = Manager.objects.get(admin=request.user)
                can_edit = (job_card.assigned_by == request.user or 
                           job_card.assigned_to.division == manager.division)
            except Manager.DoesNotExist:
                pass
        elif request.user.user_type == '3':  # Employee
            can_edit = job_card.assigned_to.admin == request.user
        
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Update status
        job_card.status = new_status
        # Note: completed_date and started_date fields don't exist in database
        job_card.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Job card status updated to {new_status}',
            'status': new_status,
            'status_color': job_card.status_color
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
