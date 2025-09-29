from celery import shared_task
from services.ai_processor import AITextProcessor
from main_app.models import JobCardAction, StaffScoresDaily, Employee
from datetime import datetime, timedelta
from django.db.models import Sum, Count


@shared_task
def process_field_report(jobcard_action_id):
    """
    Background task to process field report with AI
    """
    try:
        processor = AITextProcessor()
        result = processor.process_field_report(jobcard_action_id)
        return {'status': 'success', 'data': result}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@shared_task
def calculate_daily_scores():
    """
    Calculate daily performance scores for all staff
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Get all active employees
    employees = Employee.objects.filter(admin__is_active=True)
    
    for employee in employees:
        # Calculate yesterday's performance
        jobs_completed = JobCardAction.objects.filter(
            actor=employee.admin,
            timestamp__date=yesterday,
            action='COMPLETE'
        ).count()
        
        orders_count = employee.order_set.filter(
            created_at__date=yesterday
        ).count()
        
        bales_total = employee.order_set.filter(
            created_at__date=yesterday
        ).aggregate(total=Sum('total_bales'))['total'] or 0
        
        payments_count = employee.admin.communicationlog_set.filter(
            timestamp__date=yesterday,
            body__icontains='payment'
        ).count()
        
        # Calculate points based on PRD scoring system
        points = (
            jobs_completed * 1.0 +  # 1 point per job completion
            orders_count * 1.0 +    # 1 point per order
            bales_total * 0.2 +     # 0.2 points per bale
            payments_count * 1.0    # 1 point per payment
        )
        
        # Create or update daily score record
        score_record, created = StaffScoresDaily.objects.get_or_create(
            staff=employee,
            date=yesterday,
            defaults={
                'jobs_completed': jobs_completed,
                'orders_count': orders_count,
                'bales_total': bales_total,
                'payments_count': payments_count,
                'points': points
            }
        )
        
        if not created:
            # Update existing record
            score_record.jobs_completed = jobs_completed
            score_record.orders_count = orders_count
            score_record.bales_total = bales_total
            score_record.payments_count = payments_count
            score_record.points = points
            score_record.save()
    
    return f"Calculated scores for {employees.count()} employees"


@shared_task
def generate_automatic_jobcards():
    """
    Generate automatic job cards based on business rules
    """
    from main_app.models import Customer, JobCard, CityWeekdayPlan
    from datetime import datetime
    
    today = datetime.now()
    weekday = today.weekday() + 1  # Convert to 1-7 format
    
    # Get customers that need to be contacted (2x per month minimum)
    customers_needing_contact = Customer.objects.filter(
        active=True
    ).exclude(
        # Exclude customers contacted in last 15 days
        jobcard__created_at__gte=today - timedelta(days=15),
        jobcard__status='COMPLETED'
    )
    
    # Get staff assignments for today's cities
    city_plans = CityWeekdayPlan.objects.filter(weekday=weekday)
    
    created_count = 0
    for plan in city_plans:
        if plan.staff and plan.city:
            # Get customers in this city that need contact
            city_customers = customers_needing_contact.filter(city=plan.city)
            
            for customer in city_customers[:5]:  # Limit to 5 per staff per day
                # Create job card
                JobCard.objects.create(
                    type='CALL',
                    priority='MEDIUM',
                    status='PENDING',
                    assigned_to=plan.staff,
                    customer=customer,
                    city=plan.city,
                    due_at=today + timedelta(hours=8),  # Due by end of day
                    created_reason='Auto-generated: Regular customer contact',
                )
                created_count += 1
    
    return f"Created {created_count} automatic job cards"


@shared_task
def send_daily_notifications():
    """
    Send daily notifications to staff about pending tasks
    """
    from main_app.models import Notification
    
    today = datetime.now().date()
    
    # Get all employees with pending tasks
    employees = Employee.objects.filter(
        jobcard__status__in=['PENDING', 'IN_PROGRESS'],
        jobcard__due_at__date=today
    ).distinct()
    
    sent_count = 0
    for employee in employees:
        pending_count = employee.jobcard_set.filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            due_at__date=today
        ).count()
        
        if pending_count > 0:
            Notification.objects.create(
                user=employee.admin,
                channel='PUSH',
                title='Daily Task Reminder',
                message=f'You have {pending_count} pending tasks for today. Please complete them on time.',
                sent_at=datetime.now()
            )
            sent_count += 1
    
    return f"Sent notifications to {sent_count} employees"


@shared_task
def sync_google_drive_data():
    """
    Sync data from Google Drive (placeholder for future implementation)
    """
    # This would integrate with Google Drive API to sync customer/product data
    # For now, just return a placeholder
    return "Google Drive sync completed (placeholder)"


@shared_task
def process_whatsapp_messages():
    """
    Process incoming WhatsApp messages (placeholder for future implementation)
    """
    # This would process WhatsApp webhook messages
    # For now, just return a placeholder
    return "WhatsApp messages processed (placeholder)"
