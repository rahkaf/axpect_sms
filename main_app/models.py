from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator




class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE = ((1, "CEO"), (2, "Manager"), (3, "Employee"))
    GENDER = [("M", "Male"), ("F", "Female")]
    
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField()
    fcm_token = models.TextField(default="")  # For firebase notifications
    is_online = models.BooleanField(default=False)  # Track if user is currently signed in
    last_seen = models.DateTimeField(null=True, blank=True)  # Last activity timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()
    def __str__(self):
        return self.last_name + ", " + self.first_name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



class Division(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Manager(models.Model):
    division = models.ForeignKey(Division, on_delete=models.DO_NOTHING, null=True, blank=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.last_name + " " + self.admin.first_name


class Department(models.Model):
    name = models.CharField(max_length=120)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.DO_NOTHING, null=True, blank=False)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True, blank=False)

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name


class Attendance(models.Model):
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING)
    date = models.DateField()
    # New fields for PRD GPS-based check-in/out and working city
    start_ts = models.DateTimeField(null=True, blank=True)
    end_ts = models.DateTimeField(null=True, blank=True)
    start_gps = models.CharField(max_length=120, blank=True)
    end_gps = models.CharField(max_length=120, blank=True)
    working_city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AttendanceReport(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.DO_NOTHING)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportEmployee(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportManager(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackEmployee(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackManager(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationManager(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationEmployee(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    base = models.FloatField(default=0)
    ctc = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        if instance.user_type == 2:
            Manager.objects.create(admin=instance)
        if instance.user_type == 3:
            Employee.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    if instance.user_type == 2:
        instance.manager.save()
    if instance.user_type == 3:
        instance.employee.save()


# -----------------------------
# Core Sales CRM Models (PRD)
# -----------------------------


class City(models.Model):
    name = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    geofence_polygon = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=60, unique=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField(blank=True)
    phone_primary = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    owner_staff = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CustomerContact(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.customer.name}"


class Item(models.Model):
    CATEGORY_CHOICES = (
        ("YARN", "Yarn"),
        ("OTHER", "Other"),
    )

    name = models.CharField(max_length=255)
    uom = models.CharField(max_length=30, default="bales")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="YARN")

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateField()
    created_by_staff = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    total_bales = models.FloatField(default=0)
    total_amount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    cut = models.CharField(max_length=60, blank=True)
    rate = models.FloatField(default=0)
    qty_bales = models.FloatField(default=0)
    amount = models.FloatField(default=0)


# Old JobCard model removed - using new comprehensive JobCard model below

class JobCardAction(models.Model):
    """Legacy JobCardAction model - kept for backward compatibility"""
    ACTION_CHOICES = (
        ("UPDATE", "Update"),
        ("COMPLETE", "Complete"),
        ("REASSIGN", "Reassign"),
    )

    jobcard = models.ForeignKey('JobCard', on_delete=models.CASCADE, related_name="legacy_actions")
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    note_text = models.TextField(blank=True)
    structured_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} on {self.jobcard} by {self.actor}"


class StaffScoresDaily(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    jobs_completed = models.IntegerField(default=0)
    orders_count = models.IntegerField(default=0)
    bales_total = models.FloatField(default=0)
    payments_count = models.IntegerField(default=0)
    points = models.FloatField(default=0)

    class Meta:
        unique_together = ("staff", "date")


class CommunicationLog(models.Model):
    CHANNEL_CHOICES = (
        ("PHONE", "Phone"),
        ("WHATSAPP", "WhatsApp"),
        ("EMAIL", "Email"),
        ("VISIT", "In-person"),
    )
    DIRECTION_CHOICES = (
        ("IN", "Inbound"),
        ("OUT", "Outbound"),
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    linkages = models.JSONField(null=True, blank=True)


class Targets(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.CharField(max_length=20)  # e.g., YYYY-MM
    goal_calls = models.IntegerField(default=0)
    goal_visits = models.IntegerField(default=0)
    goal_bales = models.FloatField(default=0)
    goal_collections = models.FloatField(default=0)

    class Meta:
        unique_together = ("staff", "period")


# Additional PRD Models

class StaffCapability(models.Model):
    CAPABILITY_CHOICES = (
        ("TELE", "Tele-calling"),
        ("VISIT", "Physical visits"),
        ("SAMPLE", "Sample delivery"),
        ("COLLECTION", "Collections"),
    )
    
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="capabilities")
    capability_type = models.CharField(max_length=20, choices=CAPABILITY_CHOICES)
    
    class Meta:
        unique_together = ("staff", "capability_type")


class CustomerCapability(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="capabilities")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    monthly_volume = models.FloatField(default=0)
    strength_note = models.TextField(blank=True)


class PriceList(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    effective_date = models.DateField()
    rate = models.FloatField()
    currency = models.CharField(max_length=10, default="INR")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-effective_date']


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ("CASH", "Cash"),
        ("CHEQUE", "Cheque"),
        ("NEFT", "NEFT"),
        ("RTGS", "RTGS"),
        ("UPI", "UPI"),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.FloatField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PaymentInstrument(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("CLEARED", "Cleared"),
        ("BOUNCED", "Bounced"),
    )
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="instruments")
    instrument_no = models.CharField(max_length=100)
    bank = models.CharField(max_length=255)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")


class BusinessCalendar(models.Model):
    title = models.CharField(max_length=255)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    event_date = models.DateField()
    lead_days = models.IntegerField(default=0)
    notes = models.TextField(blank=True)


class RateAlert(models.Model):
    DIRECTION_CHOICES = (
        ("UP", "Price Increase"),
        ("DOWN", "Price Decrease"),
    )
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    threshold_percent = models.FloatField()
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    effective_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)


class CityWeekdayPlan(models.Model):
    WEEKDAY_CHOICES = (
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday"),
    )
    
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    staff = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ("city", "weekday")


class Notification(models.Model):
    CHANNEL_CHOICES = (
        ("PUSH", "Push Notification"),
        ("EMAIL", "Email"),
        ("SMS", "SMS"),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    jobcard = models.ForeignKey('JobCard', on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AIProcessingLog(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    )
    
    jobcard_action = models.ForeignKey(JobCardAction, on_delete=models.CASCADE)
    input_text = models.TextField()
    processed_data = models.JSONField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class EmployeeGPSAttendance(models.Model):
    """Individual employee GPS-based attendance tracking"""
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Below Average'),
        (3, '3 Stars - Average'),
        (4, '4 Stars - Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Check-in details
    checkin_time = models.DateTimeField(null=True, blank=True)
    checkin_gps = models.CharField(max_length=120, blank=True)
    
    # Check-out details
    checkout_time = models.DateTimeField(null=True, blank=True)
    checkout_gps = models.CharField(max_length=120, blank=True)
    
    # Work notes and additional info
    work_notes = models.TextField(blank=True)
    working_city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Performance rating (1-5 stars)
    performance_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    rating_given_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings_given')
    rating_date = models.DateTimeField(null=True, blank=True)
    rating_comments = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', '-checkin_time']
    
    def __str__(self):
        return f"{self.employee} - {self.date}"
    
    @property
    def is_checked_in(self):
        return self.checkin_time is not None
    
    @property
    def is_checked_out(self):
        return self.checkout_time is not None
    
    @property
    def hours_worked(self):
        if self.checkin_time and self.checkout_time:
            time_diff = self.checkout_time - self.checkin_time
            return round(time_diff.total_seconds() / 3600, 2)
        return 0
    
    @property
    def rating_stars(self):
        """Return star display for rating"""
        if self.performance_rating:
            return '★' * self.performance_rating + '☆' * (5 - self.performance_rating)
        return 'Not Rated'


class EmployeeTask(models.Model):
    """Task management for employees"""
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Task dates
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Assignment details
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tasks_assigned')
    
    # Task completion details
    completion_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.title} - {self.employee.admin.first_name} {self.employee.admin.last_name}"
    
    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['completed', 'cancelled']:
            from django.utils import timezone
            return timezone.localdate() > self.due_date
        return False
    
    @property
    def days_until_due(self):
        if self.due_date and self.status not in ['completed', 'cancelled']:
            from django.utils import timezone
            delta = self.due_date - timezone.localdate()
            return delta.days
        return None


class JobCard(models.Model):
    """Job Card system for task assignment and tracking"""
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Basic Information (mapped to existing DB columns)
    description = models.TextField(blank=True, default='', db_column='created_reason')
    
    # Type field from old model
    TYPE_CHOICES = (
        ("CALL", "Tele-calling"),
        ("VISIT", "Physical visit"),
        ("SAMPLE", "Sample delivery"),
        ("COLLECTION", "Collections"),
        ("FOLLOWUP", "Follow-up"),
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Assignment Details
    assigned_to = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, db_column='created_by_id')
    
    # Dates
    created_date = models.DateTimeField(auto_now_add=True, db_column='created_at')
    due_date = models.DateTimeField(null=True, blank=True, db_column='due_at')
    # Note: assigned_date, started_date, completed_date don't exist in database
    # These fields are not used in the current database schema
    
    # Note: estimated_hours, actual_hours don't exist in database
    # These fields are not used in the current database schema
    
    # Location and Customer (mapped to existing fields)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True)
    related_item = models.ForeignKey('Item', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Note: The following fields don't exist in the current database schema:
    # work_location, progress_percentage, work_notes, completion_notes, 
    # reference_documents, requires_approval, approved_by, approval_date
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['assigned_by', 'created_date']),
            models.Index(fields=['due_date']),
        ]
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"JC-{self.id} - {self.get_type_display() or 'Job Card'}"
    
    @property
    def job_card_number(self):
        """Generate job card number dynamically"""
        return f"JC-{self.id:04d}"
    
    @property
    def title(self):
        """Extract title from description or generate from type"""
        if self.description:
            # If description contains a title (first line), extract it
            lines = self.description.split('\n')
            first_line = lines[0].strip()
            if first_line and len(first_line) < 100:  # Reasonable title length
                return first_line
            else:
                # Fallback to truncated description
                return f"{self.description[:50]}..." if len(self.description) > 50 else self.description
        
        # Fallback to type display
        return self.get_type_display() if self.type else 'Job Card'
    
    # Note: estimated_hours_display property removed since estimated_hours doesn't exist in database
    
    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['COMPLETED', 'CANCELLED']:
            from django.utils import timezone
            return timezone.now() > self.due_date
        return False
    
    @property
    def days_until_due(self):
        if self.due_date and self.status not in ['COMPLETED', 'CANCELLED']:
            from django.utils import timezone
            delta = self.due_date.date() - timezone.now().date()
            return delta.days
        return None
    
    @property
    def assigned_to_name(self):
        try:
            if self.assigned_to and hasattr(self.assigned_to, 'admin') and self.assigned_to.admin:
                first_name = getattr(self.assigned_to.admin, 'first_name', '')
                last_name = getattr(self.assigned_to.admin, 'last_name', '')
                return f"{first_name} {last_name}".strip() or "Unknown User"
        except (AttributeError, Exception):
            pass
        return "Unassigned"
    
    @property
    def assigned_by_name(self):
        try:
            if self.assigned_by:
                first_name = getattr(self.assigned_by, 'first_name', '')
                last_name = getattr(self.assigned_by, 'last_name', '')
                return f"{first_name} {last_name}".strip() or "Unknown User"
        except (AttributeError, Exception):
            pass
        return "System"
    
    @property
    def status_color(self):
        colors = {
            'PENDING': 'primary',
            'IN_PROGRESS': 'warning',
            'COMPLETED': 'success',
            'CANCELLED': 'danger',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def priority_color(self):
        colors = {
            'LOW': 'success',
            'MEDIUM': 'warning',
            'HIGH': 'danger',
        }
        return colors.get(self.priority, 'secondary')


class JobCardComment(models.Model):
    """Comments and updates on job cards"""
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.job_card.job_card_number} by {self.user.first_name}"


class JobCardTimeLog(models.Model):
    """Time tracking for job cards"""
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            time_diff = self.end_time - self.start_time
            self.hours_worked = round(time_diff.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Time log for {self.job_card.job_card_number} - {self.hours_worked}h"


class GPSLocationHistory(models.Model):
    """Track GPS location history for route visualization"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='gps_history')
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    altitude = models.FloatField(null=True, blank=True, help_text="Altitude in meters")
    speed = models.FloatField(null=True, blank=True, help_text="Speed in km/h")
    heading = models.FloatField(null=True, blank=True, help_text="Direction in degrees")
    
    # Location context
    address = models.CharField(max_length=500, blank=True, help_text="Reverse geocoded address")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Time tracking
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)
    
    # Activity context
    activity_type = models.CharField(max_length=50, choices=[
        ('checkin', 'Check In'),
        ('checkout', 'Check Out'),
        ('traveling', 'Traveling'),
        ('stationary', 'Stationary'),
        ('meeting', 'Meeting'),
        ('break', 'Break'),
        ('other', 'Other')
    ], default='traveling')
    
    # Performance tracking
    time_spent_minutes = models.IntegerField(default=0, help_text="Time spent at this location in minutes")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def coordinates(self):
        return f"{self.latitude},{self.longitude}"


class GPSRoute(models.Model):
    """Daily route summary for employees"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='daily_routes')
    date = models.DateField()
    
    # Route statistics
    total_distance_km = models.FloatField(default=0, help_text="Total distance traveled in km")
    total_time_minutes = models.IntegerField(default=0, help_text="Total time on route in minutes")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Route points (stored as JSON for efficiency)
    route_points = models.JSONField(default=list, help_text="Array of [lat, lng, timestamp] points")
    
    # Performance metrics
    avg_speed_kmh = models.FloatField(default=0, help_text="Average speed in km/h")
    max_speed_kmh = models.FloatField(default=0, help_text="Maximum speed in km/h")
    stops_count = models.IntegerField(default=0, help_text="Number of stops made")
    
    # Route efficiency
    efficiency_score = models.FloatField(default=0, help_text="Route efficiency score (0-100)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.employee} - {self.date} ({self.total_distance_km:.1f}km)"
    
    @property
    def duration_hours(self):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600, 2)
        return 0


class GPSGeofence(models.Model):
    """Define geofenced areas for attendance and tracking"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Geofence definition
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    radius_meters = models.IntegerField(help_text="Radius in meters")
    
    # Polygon definition (alternative to circle)
    polygon_points = models.JSONField(null=True, blank=True, help_text="Array of [lat, lng] points for polygon geofence")
    
    # Associated entities
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    allow_checkin = models.BooleanField(default=True, help_text="Allow check-in from this geofence")
    allow_checkout = models.BooleanField(default=True, help_text="Allow check-out from this geofence")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def center_coordinates(self):
        return f"{self.center_latitude},{self.center_longitude}"


class EmployeeLocationSession(models.Model):
    """Track employee location sessions for performance analysis"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='location_sessions')
    date = models.DateField()
    
    # Session details
    session_start = models.DateTimeField()
    session_end = models.DateTimeField(null=True, blank=True)
    
    # Location details
    start_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    start_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    end_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Session context
    session_type = models.CharField(max_length=50, choices=[
        ('work', 'Work Session'),
        ('meeting', 'Meeting'),
        ('travel', 'Travel'),
        ('break', 'Break'),
        ('lunch', 'Lunch'),
        ('other', 'Other')
    ], default='work')
    
    # Performance data
    productivity_score = models.FloatField(null=True, blank=True, help_text="Productivity score (0-100)")
    notes = models.TextField(blank=True)
    
    # Geofence tracking
    geofence = models.ForeignKey(GPSGeofence, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-session_start']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['session_start']),
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.session_type} - {self.session_start.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration_minutes(self):
        if self.session_start and self.session_end:
            delta = self.session_end - self.session_start
            return round(delta.total_seconds() / 60)
        return 0
    
    @property
    def is_active(self):
        return self.session_end is None