from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from main_app.models import (
    CustomUser, Employee, Customer, JobCard, JobCardAction,
    Order, OrderItem, Payment, Attendance,
    CommunicationLog, City, Item, Notification
)
from .serializers import (
    LoginSerializer, UserSerializer, AttendanceSerializer,
    CitySerializer, CustomerSerializer, JobCardSerializer,
    JobCardActionSerializer, OrderSerializer, OrderItemSerializer,
    PaymentSerializer, CommunicationLogSerializer,
    NotificationSerializer, ItemSerializer
)
import json

def _point_in_polygon(point, polygon):
    """Ray casting algorithm for point-in-polygon. point=(lat,lon), polygon=[(lat,lon), ...]"""
    try:
        x, y = point[1], point[0]  # treat lon as x, lat as y
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i-1][1], polygon[i-1][0]
            x2, y2 = polygon[i][1], polygon[i][0]
            if ((y1 > y) != (y2 > y)):
                xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
                if x < xinters:
                    inside = not inside
        return inside
    except Exception:
        return True


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_api(request):
    """
    Mobile app login endpoint
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Update last login
        user.last_login = timezone.now()
        user.save()
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout_api(request):
    """
    Mobile app logout endpoint
    """
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def check_in(request):
    """
    Staff check-in with GPS location
    """
    if request.user.user_type != 3:  # Only employees can check in
        return Response({'error': 'Only employees can check in'}, status=status.HTTP_403_FORBIDDEN)
    
    employee = Employee.objects.get(admin=request.user)
    today = timezone.now().date()
    
    # Check if already checked in today
    existing_attendance = Attendance.objects.filter(
        department=employee.department,
        date=today
    ).first()
    
    if existing_attendance:
        # Update existing attendance
        gps = request.data.get('gps_location', '')
        working_city_id = request.data.get('working_city_id')

        # Geofence validation (if city has polygon)
        if gps and working_city_id:
            try:
                lat, lon = map(float, gps.split(','))
                from main_app.models import City
                city = City.objects.filter(id=working_city_id).first()
                if city and city.geofence_polygon:
                    poly_json = json.loads(city.geofence_polygon)
                    coords = poly_json.get('coordinates', [])
                    # Expecting GeoJSON Polygon: [ [ [lon,lat], ... ] ]
                    if coords and len(coords[0]) >= 3:
                        polygon = [(c[1], c[0]) for c in coords[0]]
                        if not _point_in_polygon((lat, lon), polygon):
                            return Response({'error': 'Check-in location is outside the configured geofence for this city.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass

        existing_attendance.start_ts = timezone.now()
        existing_attendance.start_gps = gps
        existing_attendance.working_city_id = working_city_id
        existing_attendance.notes = request.data.get('notes', '')
        existing_attendance.save()
        
        return Response({
            'message': 'Checked in successfully',
            'attendance': AttendanceSerializer(existing_attendance).data
        })
    else:
        # Create new attendance record
        gps = request.data.get('gps_location', '')
        working_city_id = request.data.get('working_city_id')

        # Geofence validation (if city has polygon)
        if gps and working_city_id:
            try:
                lat, lon = map(float, gps.split(','))
                from main_app.models import City
                city = City.objects.filter(id=working_city_id).first()
                if city and city.geofence_polygon:
                    poly_json = json.loads(city.geofence_polygon)
                    coords = poly_json.get('coordinates', [])
                    if coords and len(coords[0]) >= 3:
                        polygon = [(c[1], c[0]) for c in coords[0]]
                        if not _point_in_polygon((lat, lon), polygon):
                            return Response({'error': 'Check-in location is outside the configured geofence for this city.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass

        attendance = Attendance.objects.create(
            department=employee.department,
            date=today,
            start_ts=timezone.now(),
            start_gps=gps,
            working_city_id=working_city_id,
            notes=request.data.get('notes', '')
        )
        
        return Response({
            'message': 'Checked in successfully',
            'attendance': AttendanceSerializer(attendance).data
        })


@api_view(['POST'])
def check_out(request):
    """
    Staff check-out with GPS location
    """
    if request.user.user_type != 3:
        return Response({'error': 'Only employees can check out'}, status=status.HTTP_403_FORBIDDEN)
    
    employee = Employee.objects.get(admin=request.user)
    today = timezone.now().date()
    
    attendance = Attendance.objects.filter(
        department=employee.department,
        date=today
    ).first()
    
    if attendance:
        attendance.end_ts = timezone.now()
        attendance.end_gps = request.data.get('gps_location', '')
        attendance.save()
        
        return Response({
            'message': 'Checked out successfully',
            'attendance': AttendanceSerializer(attendance).data
        })
    else:
        return Response({'error': 'No check-in record found for today'}, status=status.HTTP_400_BAD_REQUEST)


class JobCardViewSet(viewsets.ModelViewSet):
    serializer_class = JobCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 3:  # Employee
            employee = Employee.objects.get(admin=user)
            return JobCard.objects.filter(assigned_to=employee).order_by('-created_at')
        elif user.user_type == 2:  # Manager
            # Manager can see all job cards in their division
            manager = user.manager
            return JobCard.objects.filter(
                assigned_to__division=manager.division
            ).order_by('-created_at')
        else:  # Admin/CEO
            return JobCard.objects.all().order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get current user's pending tasks"""
        if request.user.user_type != 3:
            return Response({'error': 'Only employees can access this endpoint'})
        
        employee = Employee.objects.get(admin=request.user)
        pending_tasks = JobCard.objects.filter(
            assigned_to=employee,
            status__in=['PENDING', 'IN_PROGRESS']
        ).order_by('due_at', 'priority')
        
        serializer = self.get_serializer(pending_tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_task(self, request, pk=None):
        """Update task with field report"""
        jobcard = self.get_object()
        
        # Create job card action
        action = JobCardAction.objects.create(
            jobcard=jobcard,
            actor=request.user,
            action='UPDATE',
            note_text=request.data.get('note_text', ''),
            structured_json=request.data.get('structured_data', {})
        )
        
        # Update job card status if provided
        if 'status' in request.data:
            jobcard.status = request.data['status']
            jobcard.save()
        
        # Trigger AI processing for the note text
        from .tasks import process_field_report
        process_field_report.delay(action.id)
        
        return Response({
            'message': 'Task updated successfully',
            'action': JobCardActionSerializer(action).data
        })


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 3:  # Employee
            employee = Employee.objects.get(admin=user)
            return Customer.objects.filter(owner_staff=employee, active=True)
        else:
            return Customer.objects.filter(active=True)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search customers by name or code"""
        query = request.query_params.get('q', '')
        if query:
            customers = self.get_queryset().filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            )[:20]
            serializer = self.get_serializer(customers, many=True)
            return Response(serializer.data)
        return Response([])


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 3:  # Employee
            employee = Employee.objects.get(admin=user)
            return Order.objects.filter(created_by_staff=employee).order_by('-created_at')
        else:
            return Order.objects.all().order_by('-created_at')


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.all().order_by('-created_at')


@api_view(['GET'])
def dashboard_stats(request):
    """
    Get dashboard statistics for mobile app
    """
    if request.user.user_type != 3:
        return Response({'error': 'Only employees can access dashboard stats'})
    
    employee = Employee.objects.get(admin=request.user)
    today = timezone.now().date()
    
    # Today's tasks
    today_tasks = JobCard.objects.filter(
        assigned_to=employee,
        due_at__date=today
    )
    
    # This month's performance
    month_start = today.replace(day=1)
    month_performance = StaffScoresDaily.objects.filter(
        staff=employee,
        date__gte=month_start
    ).aggregate(
        total_points=Sum('points'),
        total_jobs=Sum('jobs_completed'),
        total_orders=Sum('orders_count'),
        total_bales=Sum('bales_total')
    )
    
    # Recent communications
    recent_comms = CommunicationLog.objects.filter(
        user=request.user
    ).order_by('-timestamp')[:5]
    
    return Response({
        'today_tasks': {
            'total': today_tasks.count(),
            'completed': today_tasks.filter(status='COMPLETED').count(),
            'pending': today_tasks.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
        },
        'month_performance': month_performance,
        'recent_communications': CommunicationLogSerializer(recent_comms, many=True).data
    })


@api_view(['GET'])
def cities_list(request):
    """Get list of cities for working location selection"""
    cities = City.objects.all().order_by('name')
    return Response(CitySerializer(cities, many=True).data)


@api_view(['GET'])
def notifications_list(request):
    """Get user notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    return Response(NotificationSerializer(notifications, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def whatsapp_webhook(request):
    """Inbound WhatsApp webhook handler (placeholder)."""
    from_phone = request.data.get('from') or request.data.get('From')
    body = request.data.get('body') or request.data.get('Body') or ''

    # Try to match customer/contact by phone
    customer = None
    if from_phone:
        customer = Customer.objects.filter(
            Q(phone_primary__icontains=from_phone)
        ).first()
        if not customer:
            contact = Customer.objects.filter(contacts__phone__icontains=from_phone).first()
            if contact:
                customer = contact

    # Log communication
    CommunicationLog.objects.create(
        channel='WHATSAPP',
        direction='IN',
        customer=customer,
        user=None,
        subject='WhatsApp Message',
        body=body,
        linkages={'from': from_phone}
    )

    # Notify owner if exists
    if customer and customer.owner_staff:
        Notification.objects.create(
            user=customer.owner_staff.admin,
            channel='PUSH',
            title='New WhatsApp message',
            message=f'Incoming WhatsApp from {from_phone} for customer {customer.name}',
            sent_at=timezone.now()
        )
    return Response({'status': 'received'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def email_inbound(request):
    """Inbound Email webhook handler (placeholder)."""
    sender = request.data.get('from') or request.data.get('sender')
    to = request.data.get('to')
    subject = request.data.get('subject', '')
    body = request.data.get('body', '')

    # Try to match customer by email
    customer = None
    if sender:
        customer = Customer.objects.filter(email__iexact=sender).first()
        if not customer:
            customer = Customer.objects.filter(contacts__email__iexact=sender).first()

    CommunicationLog.objects.create(
        channel='EMAIL',
        direction='IN',
        customer=customer,
        user=None,
        subject=subject,
        body=body,
        linkages={'from': sender, 'to': to}
    )
    return Response({'status': 'received'})


@api_view(['POST'])
def trigger_gdrive_sync(request):
    from .tasks import sync_google_drive_data
    sync_google_drive_data.delay()
    return Response({'status': 'queued'})


@api_view(['POST'])
def trigger_whatsapp_processing(request):
    from .tasks import process_whatsapp_messages
    process_whatsapp_messages.delay()
    return Response({'status': 'queued'})
