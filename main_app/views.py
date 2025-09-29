import json
import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Attendance, Department, JobCard, Customer, City, Item, JobCardAction, StaffScoresDaily, CommunicationLog
from datetime import date, datetime, timedelta
from django.utils import timezone
from .EmailBackend import EmailBackend

# Create your views here.

def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("manager_home"))
        else:
            return redirect(reverse("employee_home"))
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        #Google recaptcha - TEMPORARILY DISABLED FOR TESTING
        # captcha_token = request.POST.get('g-recaptcha-response')
        # captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        # captcha_key = "6Lf9RfcnAAAAAIn2o_U8h3KQwb3lVMeDvenBCXYp"
        # data = {
        #     'secret': captcha_key,
        #     'response': captcha_token
        # }
        # # Make request
        # try:
        #     captcha_server = requests.post(url=captcha_url, data=data)
        #     response = json.loads(captcha_server.text)
        #     if response['success'] == False:
        #         messages.error(request, 'Invalid Captcha. Try Again')
        #         return redirect('/')
        # except:
        #     messages.error(request, 'Captcha could not be verified. Try Again')
        #     return redirect('/')
        
        #Authenticate
        user = authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user != None:
            login(request, user)
            if user.user_type == '1':
                return redirect(reverse("admin_home"))
            elif user.user_type == '2':
                return redirect(reverse("manager_home"))
            else:
                return redirect(reverse("employee_home"))
        else:
            messages.error(request, "Invalid details")
            return redirect("/")



def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    department_id = request.POST.get('department')
    try:
        department = get_object_or_404(Department, id=department_id)
        attendance = Attendance.objects.filter(department=department)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date)
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')


# -----------------------------
# Minimal JobCard APIs
# -----------------------------


@csrf_exempt
def jobcard_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        jobcard = JobCard.objects.create(
            type=payload.get('type', 'FOLLOWUP'),
            priority=payload.get('priority', 'MEDIUM'),
            status=payload.get('status', 'PENDING'),
            assigned_to_id=payload.get('assigned_to_id'),
            customer_id=payload.get('customer_id'),
            city_id=payload.get('city_id'),
            due_at=payload.get('due_at'),
            created_by=request.user if request.user.is_authenticated else None,
            created_reason=payload.get('created_reason', ''),
            related_item_id=payload.get('related_item_id'),
        )
        return JsonResponse({'id': jobcard.id, 'status': jobcard.status})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


def jobcard_list_my(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'employee'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    qs = JobCard.objects.filter(assigned_to=request.user.employee).order_by('due_at')
    out = []
    for jc in qs.select_related('customer', 'city'):
        out.append({
            'id': jc.id,
            'type': jc.type,
            'priority': jc.priority,
            'status': jc.status,
            'customer': jc.customer.name if jc.customer else None,
            'city': jc.city.name if jc.city else None,
            'due_at': jc.due_at.isoformat() if jc.due_at else None,
        })
    return JsonResponse(out, safe=False)


@csrf_exempt
def jobcard_update_status(request, jobcard_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    jc = JobCard.objects.filter(id=jobcard_id).first()
    if not jc:
        return JsonResponse({'error': 'Not found'}, status=404)
    payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    new_status = payload.get('status')
    if new_status not in dict(JobCard.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid status'}, status=400)
    jc.status = new_status
    jc.save(update_fields=['status', 'updated_at'])
    # scoring on completion
    if new_status == 'COMPLETED' and jc.assigned_to:
        today = date.today()
        score, _ = StaffScoresDaily.objects.get_or_create(staff=jc.assigned_to, date=today)
        score.jobs_completed = (score.jobs_completed or 0) + 1
        score.points = (score.points or 0) + 1.0
        score.save()
        JobCardAction.objects.create(jobcard=jc, actor=request.user if request.user.is_authenticated else None, action='COMPLETE', note_text='Completed via API')
        try:
            CommunicationLog.objects.create(
                channel='VISIT' if jc.type == 'VISIT' else 'PHONE',
                direction='OUT',
                customer=jc.customer,
                user=request.user if request.user.is_authenticated else None,
                subject=f"JobCard {jc.id} Completed",
                body=f"{jc.type} completed with priority {jc.priority}.")
        except Exception:
            pass
    return JsonResponse({'id': jc.id, 'status': jc.status})


# -----------------------------
# NLP stub: parse notes and auto-create follow-up
# -----------------------------


@csrf_exempt
def nlp_parse_and_followup(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        note = payload.get('note', '')
        customer_id = payload.get('customer_id')
        # naive rule: if 'days' in note, schedule follow-up in that many days
        import re
        m = re.search(r"(\d+)\s*day", note, re.IGNORECASE)
        days = int(m.group(1)) if m else 3
        due = datetime.utcnow() + timedelta(days=days)
        jc = JobCard.objects.create(
            type='FOLLOWUP',
            priority='MEDIUM',
            status='PENDING',
            assigned_to=request.user.employee if request.user.is_authenticated and hasattr(request.user, 'employee') else None,
            customer_id=customer_id,
            due_at=due,
            created_by=request.user if request.user.is_authenticated else None,
            created_reason='Auto follow-up from note',
        )
        JobCardAction.objects.create(jobcard=jc, actor=request.user if request.user.is_authenticated else None, action='UPDATE', note_text=note)
        return JsonResponse({'followup_jobcard_id': jc.id, 'due_at': due.isoformat()})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


# -----------------------------
# Attendance Check-in/Check-out APIs
# -----------------------------


def _require_employee(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'employee'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return None


def get_or_create_employee_profile(user):
    """
    Get or create an Employee profile for any user type (Admin, Manager, Employee)
    This allows all user types to use the attendance system
    """
    try:
        # First try to get existing employee profile
        if hasattr(user, 'employee'):
            return user.employee
        
        # If no employee profile exists, create one based on user type
        from .models import Employee, Manager, Admin, Division, Department
        
        if user.user_type == '1':  # CEO/Admin
            # Get or create a default division and department for admin
            admin_division, _ = Division.objects.get_or_create(
                name='Administration',
                defaults={'name': 'Administration'}
            )
            admin_department, _ = Department.objects.get_or_create(
                name='Executive',
                division=admin_division,
                defaults={'name': 'Executive', 'division': admin_division}
            )
            
            # Create employee profile for admin
            employee = Employee.objects.create(
                admin=user,
                division=admin_division,
                department=admin_department
            )
            print(f"Created employee profile for admin: {user.email}")
            return employee
            
        elif user.user_type == '2':  # Manager
            try:
                # Get the manager profile
                manager = Manager.objects.get(admin=user)
                
                # Get or create a default department for the manager's division
                if manager.division:
                    department, _ = Department.objects.get_or_create(
                        name='Management',
                        division=manager.division,
                        defaults={'name': 'Management', 'division': manager.division}
                    )
                else:
                    # Create default division if manager doesn't have one
                    default_division, _ = Division.objects.get_or_create(
                        name='General',
                        defaults={'name': 'General'}
                    )
                    manager.division = default_division
                    manager.save()
                    
                    department, _ = Department.objects.get_or_create(
                        name='Management',
                        division=default_division,
                        defaults={'name': 'Management', 'division': default_division}
                    )
                
                # Create employee profile for manager
                employee = Employee.objects.create(
                    admin=user,
                    division=manager.division,
                    department=department
                )
                print(f"Created employee profile for manager: {user.email}")
                return employee
                
            except Manager.DoesNotExist:
                # Create manager profile first, then employee profile
                default_division, _ = Division.objects.get_or_create(
                    name='General',
                    defaults={'name': 'General'}
                )
                
                manager = Manager.objects.create(
                    admin=user,
                    division=default_division
                )
                
                department, _ = Department.objects.get_or_create(
                    name='Management',
                    division=default_division,
                    defaults={'name': 'Management', 'division': default_division}
                )
                
                employee = Employee.objects.create(
                    admin=user,
                    division=default_division,
                    department=department
                )
                print(f"Created manager and employee profile for: {user.email}")
                return employee
                
        elif user.user_type == '3':  # Employee
            # This should already exist, but create if missing
            try:
                return user.employee
            except AttributeError:
                # Create with default division/department
                default_division, _ = Division.objects.get_or_create(
                    name='General',
                    defaults={'name': 'General'}
                )
                default_department, _ = Department.objects.get_or_create(
                    name='General',
                    division=default_division,
                    defaults={'name': 'General', 'division': default_division}
                )
                
                employee = Employee.objects.create(
                    admin=user,
                    division=default_division,
                    department=default_department
                )
                print(f"Created employee profile for: {user.email}")
                return employee
        
        return None
        
    except Exception as e:
        print(f"Error creating employee profile for {user.email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


@csrf_exempt
def attendance_checkin(request):
    try:
        # Debug logging
        print(f"Attendance checkin request: {request.method}")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User: {request.user}")
        
        if request.method != 'POST':
            return JsonResponse({'error': 'Invalid method'}, status=405)
        
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=401)
        
        # Get or create employee profile for any user type
        employee = get_or_create_employee_profile(request.user)
        if not employee:
            return JsonResponse({'error': 'Could not create employee profile'}, status=500)
        
        # Parse request data
        try:
            if request.body:
                payload = json.loads(request.body.decode('utf-8'))
            else:
                payload = request.POST.dict()
            
            gps = payload.get('gps', '')
            city_id = payload.get('city_id')
            
            print(f"GPS data: {gps}")
            print(f"Employee: {employee}")
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        # Create or update individual employee attendance
        today = timezone.localdate()
        from .models import EmployeeGPSAttendance
        attendance, created = EmployeeGPSAttendance.objects.get_or_create(
            employee=employee, 
            date=today
        )
        
        # Check if already checked in
        if attendance.checkin_time:
            return JsonResponse({
                'error': 'Already checked in today',
                'checkin_time': attendance.checkin_time.isoformat()
            }, status=400)
        
        # Update attendance record
        attendance.checkin_time = timezone.now()
        attendance.checkin_gps = gps or ''
        if city_id:
            attendance.working_city_id = city_id
        attendance.save()
        
        print(f"Attendance saved: {attendance.id}")
        
        return JsonResponse({
            'success': True,
            'attendance_id': attendance.id, 
            'checkin_time': attendance.checkin_time.isoformat(),
            'message': 'Check-in successful'
        })
        
    except Exception as exc:
        print(f"Attendance checkin error: {str(exc)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(exc)}'}, status=500)


@csrf_exempt
def attendance_checkout(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'Invalid method'}, status=405)
        
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=401)
        
        # Get or create employee profile for any user type
        employee = get_or_create_employee_profile(request.user)
        if not employee:
            return JsonResponse({'error': 'Could not create employee profile'}, status=500)
        
        # Parse request data
        try:
            payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
            gps = payload.get('gps', '')
            notes = payload.get('notes', '')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        today = timezone.localdate()
        from .models import EmployeeGPSAttendance
        attendance = EmployeeGPSAttendance.objects.filter(employee=employee, date=today).first()
        
        if not attendance or not attendance.checkin_time:
            return JsonResponse({'error': 'No active check-in for today'}, status=404)
        
        if attendance.checkout_time:
            return JsonResponse({
                'error': 'Already checked out today', 
                'checkout_time': attendance.checkout_time.isoformat()
            }, status=400)
        
        # Update checkout details
        attendance.checkout_time = timezone.now()
        attendance.checkout_gps = gps or ''
        attendance.work_notes = notes or ''
        attendance.save()
        
        return JsonResponse({
            'success': True,
            'attendance_id': attendance.id, 
            'checkout_time': attendance.checkout_time.isoformat(), 
            'hours_worked': attendance.hours_worked,
            'message': 'Check-out successful'
        })
        
    except Exception as exc:
        print(f"Attendance checkout error: {str(exc)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(exc)}'}, status=500)


@csrf_exempt
def get_attendance_status(request):
    """Get current attendance status for the logged-in user"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=401)
        
        # Get or create employee profile
        employee = get_or_create_employee_profile(request.user)
        if not employee:
            return JsonResponse({'error': 'Could not create employee profile'}, status=500)
        
        today = timezone.localdate()
        from .models import EmployeeGPSAttendance
        
        try:
            attendance = EmployeeGPSAttendance.objects.get(employee=employee, date=today)
            
            status = {
                'date': today.isoformat(),
                'is_checked_in': attendance.checkin_time is not None,
                'is_checked_out': attendance.checkout_time is not None,
                'checkin_time': attendance.checkin_time.isoformat() if attendance.checkin_time else None,
                'checkout_time': attendance.checkout_time.isoformat() if attendance.checkout_time else None,
                'hours_worked': attendance.hours_worked,
                'work_notes': attendance.work_notes,
                'user_name': f"{request.user.first_name} {request.user.last_name}",
                'user_type': dict(request.user.USER_TYPE)[int(request.user.user_type)]
            }
            
        except EmployeeGPSAttendance.DoesNotExist:
            status = {
                'date': today.isoformat(),
                'is_checked_in': False,
                'is_checked_out': False,
                'checkin_time': None,
                'checkout_time': None,
                'hours_worked': None,
                'work_notes': '',
                'user_name': f"{request.user.first_name} {request.user.last_name}",
                'user_type': dict(request.user.USER_TYPE)[int(request.user.user_type)]
            }
        
        return JsonResponse(status)
        
    except Exception as exc:
        print(f"Get attendance status error: {str(exc)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(exc)}'}, status=500)


# -----------------------------
# Scoring Leaderboard & Summary APIs
# -----------------------------


def scoring_leaderboard_today(request):
    today = timezone.localdate()
    qs = StaffScoresDaily.objects.filter(date=today).select_related('staff__admin').order_by('-points')
    data = [{
        'staff_id': s.staff.id,
        'name': f"{s.staff.admin.first_name} {s.staff.admin.last_name}",
        'points': s.points,
        'jobs_completed': s.jobs_completed,
    } for s in qs]
    return JsonResponse(data, safe=False)


def scoring_summary(request):
    period = request.GET.get('period', 'weekly')
    today = timezone.localdate()
    if period == 'monthly':
        start = today - timedelta(days=30)
    else:
        start = today - timedelta(days=7)
    qs = StaffScoresDaily.objects.filter(date__gte=start, date__lte=today).select_related('staff__admin')
    # aggregate per staff
    summary = {}
    for s in qs:
        key = s.staff.id
        if key not in summary:
            summary[key] = {
                'staff_id': key,
                'name': f"{s.staff.admin.first_name} {s.staff.admin.last_name}",
                'points': 0.0,
                'jobs_completed': 0,
                'orders_count': 0,
                'bales_total': 0.0,
                'payments_count': 0,
            }
        agg = summary[key]
        agg['points'] += s.points or 0
        agg['jobs_completed'] += s.jobs_completed or 0
        agg['orders_count'] += s.orders_count or 0
        agg['bales_total'] += s.bales_total or 0
        agg['payments_count'] += s.payments_count or 0
    # to list sorted by points
    data = sorted(summary.values(), key=lambda x: x['points'], reverse=True)
    return JsonResponse({'period': period, 'start': start.isoformat(), 'end': today.isoformat(), 'data': data})


# -----------------------------
# Targets API (get my targets and progress)
# -----------------------------


def my_targets(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'employee'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    emp = request.user.employee
    today = timezone.localdate()
    period = request.GET.get('period') or f"{today.year}-{today.month:02d}"
    tgt = Targets.objects.filter(staff=emp, period=period).first()
    # progress based on StaffScoresDaily aggregation for month
    start = today.replace(day=1)
    qs = StaffScoresDaily.objects.filter(staff=emp, date__gte=start, date__lte=today)
    progress = {
        'jobs_completed': sum([x.jobs_completed or 0 for x in qs]),
        'orders_count': sum([x.orders_count or 0 for x in qs]),
        'bales_total': sum([x.bales_total or 0 for x in qs]),
        'payments_count': sum([x.payments_count or 0 for x in qs]),
        'points': sum([x.points or 0 for x in qs]),
    }
    data = {
        'period': period,
        'goal_calls': tgt.goal_calls if tgt else 0,
        'goal_visits': tgt.goal_visits if tgt else 0,
        'goal_bales': tgt.goal_bales if tgt else 0,
        'goal_collections': tgt.goal_collections if tgt else 0,
        'progress': progress,
    }
    return JsonResponse(data)


# -----------------------------
# Communication Logs APIs
# -----------------------------


@csrf_exempt
def comm_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        log = CommunicationLog.objects.create(
            channel=payload.get('channel', 'PHONE'),
            direction=payload.get('direction', 'OUT'),
            customer_id=payload.get('customer_id'),
            user=request.user if request.user.is_authenticated else None,
            subject=payload.get('subject', ''),
            body=payload.get('body', ''),
            linkages=payload.get('linkages'),
        )
        return JsonResponse({'id': log.id, 'timestamp': log.timestamp.isoformat()})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


def comm_list(request):
    customer_id = request.GET.get('customer_id')
    qs = CommunicationLog.objects.all().select_related('customer', 'user')
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    data = [{
        'id': c.id,
        'channel': c.channel,
        'direction': c.direction,
        'customer': c.customer.name if c.customer else None,
        'user': c.user.email if c.user else None,
        'subject': c.subject,
        'body': c.body,
        'timestamp': c.timestamp.isoformat(),
    } for c in qs.order_by('-timestamp')[:200]]
    return JsonResponse(data, safe=False)


# -----------------------------
# Monthly Cadence Generator (ensure >=2 contacts per month)
# -----------------------------


@csrf_exempt
def cadence_generate(request):
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'error': 'Invalid method'}, status=405)
    today = timezone.localdate()
    start_month = today.replace(day=1)
    created = []
    try:
        customers = Customer.objects.filter(active=True)
        for cust in customers:
            comms = CommunicationLog.objects.filter(customer=cust, timestamp__date__gte=start_month, timestamp__date__lte=today).count()
            if comms < 2:
                assigned = cust.owner_staff if cust.owner_staff_id else None
                jc = JobCard.objects.create(
                    type='FOLLOWUP',
                    priority='MEDIUM',
                    status='PENDING',
                    assigned_to=assigned,
                    customer=cust,
                    city=cust.city,
                    due_at=datetime.utcnow() + timedelta(days=3),
                    created_by=request.user if request.user.is_authenticated else None,
                    created_reason='Auto monthly cadence',
                )
                created.append(jc.id)
        return JsonResponse({'created_count': len(created), 'jobcard_ids': created})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


# -----------------------------
# Email send stub and WhatsApp webhook
# -----------------------------


@csrf_exempt
def email_send_stub(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        subject = payload.get('subject', '')
        body = payload.get('body', '')
        customer_id = payload.get('customer_id')
        # Log communication
        log = CommunicationLog.objects.create(
            channel='EMAIL', direction='OUT', customer_id=customer_id, user=request.user if request.user.is_authenticated else None, subject=subject, body=body
        )
        # Optionally attempt to send (if EMAIL configured and customer email exists)
        try:
            from django.core.mail import send_mail
            cust = Customer.objects.filter(id=customer_id).first()
            to_email = cust.email if cust and cust.email else None
            if to_email:
                send_mail(subject, body, None, [to_email], fail_silently=True)
        except Exception:
            pass
        return JsonResponse({'id': log.id})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@csrf_exempt
def whatsapp_webhook(request):
    # Accept inbound message and log it
    try:
        if request.method == 'GET':
            return JsonResponse({'status': 'ok'})
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        phone = payload.get('from') or payload.get('phone')
        body = payload.get('body', '')
        # naive match by phone_primary
        cust = Customer.objects.filter(phone_primary__icontains=phone).first() if phone else None
        log = CommunicationLog.objects.create(
            channel='WHATSAPP', direction='IN', customer=cust, subject='Inbound WhatsApp', body=body
        )
        return JsonResponse({'id': log.id})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


# -----------------------------
# Simple Customer list/create (minimal)
# -----------------------------


def customers_list(request):
    qs = Customer.objects.select_related('city').order_by('name')
    out = []
    for c in qs:
        out.append({
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'city': c.city.name if c.city else None,
            'phone_primary': c.phone_primary,
            'email': c.email,
            'active': c.active,
        })
    return JsonResponse(out, safe=False)


@csrf_exempt
def customers_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        c = Customer.objects.create(
            name=payload.get('name'),
            code=payload.get('code'),
            city_id=payload.get('city_id'),
            address=payload.get('address', ''),
            phone_primary=payload.get('phone_primary', ''),
            email=payload.get('email', ''),
            active=payload.get('active', True),
            owner_staff=request.user.employee if request.user.is_authenticated and hasattr(request.user, 'employee') else None,
        )
        return JsonResponse({'id': c.id})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


def test_attendance_page(request):
    """Test page for attendance system"""
    return render(request, 'test_attendance.html')


@csrf_exempt
def test_ajax(request):
    """Test AJAX endpoint"""
    if request.method == 'POST':
        return JsonResponse({
            'status': 'success',
            'message': 'AJAX request successful',
            'user': str(request.user),
            'authenticated': request.user.is_authenticated,
            'user_type': getattr(request.user, 'user_type', 'None'),
            'post_data': dict(request.POST)
        })
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'})


@csrf_exempt  
def test_manager_checkin(request):
    """Test manager check-in functionality"""
    print(f"Test manager checkin called - Method: {request.method}")
    print(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
    print(f"User type: {getattr(request.user, 'user_type', 'None')}")
    print(f"POST data: {dict(request.POST)}")
    
    if request.method == 'POST':
        try:
            from .models import Manager, Employee, Department, EmployeeGPSAttendance
            from django.utils import timezone
            
            if request.user.user_type == '2':
                manager = Manager.objects.get(admin=request.user)
                print(f"Manager found: {manager}")
                
                # Get or create Employee record
                employee, created = Employee.objects.get_or_create(
                    admin=request.user,
                    defaults={
                        'division': manager.division,
                        'department': Department.objects.filter(division=manager.division).first()
                    }
                )
                print(f"Employee record: {employee} (created: {created})")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Test successful',
                    'manager': str(manager),
                    'employee': str(employee),
                    'employee_created': created
                })
            else:
                return JsonResponse({'status': 'error', 'message': f'Wrong user type: {request.user.user_type}'})
                
        except Exception as e:
            print(f"Error in test_manager_checkin: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'})
