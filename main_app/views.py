import json
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Attendance, Department, JobCard, Customer, City, Item, JobCardAction, CommunicationLog
from django.shortcuts import get_object_or_404
from .utils import get_home_for_user_type, redirect_to_user_home, validate_required_fields, add_error_message, add_success_message
from datetime import date, datetime, timedelta
from django.utils import timezone

# Create your views here.

def login_page(request):
    if request.user.is_authenticated:
        return redirect_to_user_home(request.user.user_type)
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Access Denied</h4>")
    
    is_valid, validation_data = validate_required_fields(request, ['email', 'password'])
    if not is_valid:
        add_error_message(request, validation_data['message'])
        return redirect('/')
    
    email = request.POST.get('email')
    password = request.POST.get('password')
    
    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        return redirect_to_user_home(user.user_type)
    else:
        add_error_message(request, "Invalid email or password")
        return redirect("/")



def logout_user(request):
    if request.user is not None:
        # Set user offline before logout
        if hasattr(request.user, 'is_online'):
            request.user.is_online = False
            request.user.save(update_fields=['is_online'])
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
    jc.save(update_fields=['status','updated_at'])
    
    # Log jobcard completion
    if new_status == 'COMPLETED' and jc.assigned_to:
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
