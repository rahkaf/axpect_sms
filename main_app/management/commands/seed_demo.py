from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from main_app.models import (
    Division, Department, Manager, Employee, City, Customer, CustomerContact,
    Item, JobCard, StaffCapability
)


class Command(BaseCommand):
    help = 'Seed demo data: users, org, city, customer, item, and a sample jobcard.'

    def handle(self, *args, **options):
        User = get_user_model()

        # Create Division and Department
        div, _ = Division.objects.get_or_create(name='Sales')
        dept, _ = Department.objects.get_or_create(name='Field', division=div)

        # Create CEO (admin)
        admin_email = 'admin@admin.com'
        if not User.objects.filter(email=admin_email).exists():
            ceo = User.objects.create_user(
                email=admin_email,
                password='admin',
                first_name='Admin',
                last_name='User',
                user_type=1,
                gender='M',
                profile_pic='',
                address='HQ'
            )
            self.stdout.write(self.style.SUCCESS('Created CEO admin@admin.com / admin'))
        else:
            ceo = User.objects.get(email=admin_email)

        # Create Manager
        manager_email = 'manager@manager.com'
        if not User.objects.filter(email=manager_email).exists():
            mgr_user = User.objects.create_user(
                email=manager_email,
                password='manager',
                first_name='Regional',
                last_name='Manager',
                user_type=2,
                gender='M',
                profile_pic='',
                address='City'
            )
            mgr = mgr_user.manager
            mgr.division = div
            mgr.save()
            self.stdout.write(self.style.SUCCESS('Created Manager manager@manager.com / manager'))
        else:
            mgr_user = User.objects.get(email=manager_email)

        # Create Employee
        employee_email = 'employee@employee.com'
        if not User.objects.filter(email=employee_email).exists():
            emp_user = User.objects.create_user(
                email=employee_email,
                password='employee',
                first_name='Field',
                last_name='Executive',
                user_type=3,
                gender='M',
                profile_pic='',
                address='On field'
            )
            emp = emp_user.employee
            emp.division = div
            emp.department = dept
            emp.save()
            # Capabilities
            StaffCapability.objects.get_or_create(staff=emp, capability_type='VISIT')
            StaffCapability.objects.get_or_create(staff=emp, capability_type='TELE')
            self.stdout.write(self.style.SUCCESS('Created Employee employee@employee.com / employee'))
        else:
            emp_user = User.objects.get(email=employee_email)
            emp = emp_user.employee

        # City
        blr, _ = City.objects.get_or_create(name='Bengaluru', state='Karnataka', country='India')

        # Customer
        cust, _ = Customer.objects.get_or_create(
            code='TALLAM001',
            defaults={
                'name': 'Tallam Brothers',
                'city': blr,
                'phone_primary': '+911234567890',
                'email': 'tallam@example.com',
                'owner_staff': emp
            }
        )
        CustomerContact.objects.get_or_create(customer=cust, name='Sahil', role='Buyer', phone='+911112223334', email='sahil@tallam.com', is_primary=True)

        # Item
        yarn, _ = Item.objects.get_or_create(name='40s Yarn', uom='bales', category='YARN')

        # Sample JobCard
        if not JobCard.objects.filter(customer=cust, assigned_to=emp).exists():
            JobCard.objects.create(
                type='VISIT',
                priority='MEDIUM',
                status='PENDING',
                assigned_to=emp,
                customer=cust,
                city=blr,
                due_at=timezone.now(),
                created_reason='Initial customer visit',
                related_item=yarn
            )
            self.stdout.write(self.style.SUCCESS('Created sample JobCard for Tallam Brothers'))

        self.stdout.write(self.style.SUCCESS('Demo data seeding complete.'))
