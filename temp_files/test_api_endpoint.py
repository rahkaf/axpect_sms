#!/usr/bin/env python3
"""
Test script to check if the GPS dashboard API endpoints are working
Run this from the Django project root directory
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axpect_tech_config.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

# Import models
from main_app.models import (
    CustomUser, Employee, Manager, Division, Department,
    GPSCheckIn, GPSTrack, EmployeeGeofence
)

def test_api_endpoints():
    """Test the GPS API endpoints"""
    print("=" * 60)
    print("TESTING GPS DASHBOARD API ENDPOINTS")
    print("=" * 60)
    
    # Create test client
    client = Client()
    
    # Create test data
    print("\n1. Creating test data...")
    
    # Create division and department
    division = Division.objects.create(name="Test Division")
    department = Department.objects.create(name="Test Department", division=division)
    
    # Create admin user
    admin_user = CustomUser.objects.create_user(
        email="admin@test.com",
        password="adminpass123",
        user_type="1",
        first_name="Admin",
        last_name="User"
    )
    
    # Create employee
    employee_user = CustomUser.objects.create_user(
        email="employee@test.com",
        password="employeepass123",
        user_type="3",
        first_name="Employee",
        last_name="User"
    )
    
    employee = Employee.objects.create(
        admin=employee_user,
        division=division,
        department=department
    )
    
    print(f"[OK] Created division: {division.name}")
    print(f"[OK] Created department: {department.name}")
    print(f"[OK] Created admin user: {admin_user.email}")
    print(f"[OK] Created employee: {employee_user.email}")
    
    # Test 1: Check if admin GPS dashboard loads
    print("\n2. Testing admin GPS dashboard...")
    client.force_login(admin_user)
    
    try:
        response = client.get(reverse('admin_gps_dashboard'))
        print(f"[OK] Admin GPS dashboard status: {response.status_code}")
        if response.status_code == 200:
            print("[OK] Dashboard loads successfully")
        else:
            print(f"[ERROR] Dashboard failed to load: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Dashboard error: {e}")
    
    # Test 2: Check department details API endpoint
    print("\n3. Testing department details API...")
    
    try:
        api_url = reverse('api_department_details', kwargs={'department_id': department.id})
        response = client.get(api_url)
        print(f"[OK] API endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"[OK] API response success: {data.get('success', False)}")
            print(f"[OK] Department name: {data.get('department', {}).get('name', 'N/A')}")
            print(f"[OK] Employee count: {data.get('statistics', {}).get('total_employees', 0)}")
        else:
            print(f"[ERROR] API failed: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
            
    except Exception as e:
        print(f"[ERROR] API error: {e}")
    
    # Test 3: Check if GPS check-in API works
    print("\n4. Testing GPS check-in API...")
    
    try:
        client.force_login(employee_user)
        checkin_data = {
            'latitude': 12.9716,
            'longitude': 77.5946,
            'work_summary': 'Test work'
        }
        
        response = client.post(reverse('api_gps_checkin'), checkin_data)
        print(f"[OK] GPS check-in status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"[OK] Check-in success: {data.get('success', False)}")
            
            # Check if check-in was created in database
            checkin = GPSCheckIn.objects.filter(employee=employee).first()
            if checkin:
                print(f"[OK] Check-in created in database: ID {checkin.id}")
            else:
                print("[ERROR] Check-in not found in database")
        else:
            print(f"[ERROR] Check-in failed: {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"[ERROR] Check-in error: {e}")
    
    # Test 4: Test location analytics
    print("\n5. Testing location analytics...")
    
    try:
        client.force_login(admin_user)
        response = client.get(reverse('admin_location_analytics'))
        print(f"[OK] Location analytics status: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] Location analytics loads successfully")
        else:
            print(f"[ERROR] Location analytics failed: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Location analytics error: {e}")
    
    # Test 5: Test geofence management
    print("\n6. Testing geofence management...")
    
    try:
        response = client.get(reverse('admin_geofence_management'))
        print(f"[OK] Geofence management status: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] Geofence management loads successfully")
        else:
            print(f"[ERROR] Geofence management failed: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Geofence management error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    
    # Cleanup
    print("\nCleaning up test data...")
    CustomUser.objects.filter(email__in=["admin@test.com", "employee@test.com"]).delete()
    Division.objects.filter(name="Test Division").delete()
    print("[OK] Test data cleaned up")

def test_url_patterns():
    """Test if all URL patterns are properly configured"""
    print("\n" + "=" * 60)
    print("TESTING URL PATTERNS")
    print("=" * 60)
    
    from django.urls import reverse, NoReverseMatch
    
    urls_to_test = [
        'admin_gps_dashboard',
        'admin_location_analytics', 
        'admin_geofence_management',
        'api_department_details',
        'api_gps_checkin',
        'api_gps_checkout',
        'api_gps_location_update',
    ]
    
    for url_name in urls_to_test:
        try:
            if url_name == 'api_department_details':
                url = reverse(url_name, kwargs={'department_id': 1})
            else:
                url = reverse(url_name)
            print(f"[OK] {url_name}: {url}")
        except NoReverseMatch as e:
            print(f"[ERROR] {url_name}: URL not found - {e}")
        except Exception as e:
            print(f"[ERROR] {url_name}: Error - {e}")

if __name__ == "__main__":
    print("Starting GPS Dashboard API Tests...")
    
    # Test URL patterns first
    test_url_patterns()
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\nAll tests completed!")
