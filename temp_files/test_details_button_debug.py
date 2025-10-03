"""
Simple test to debug the Details button issue
This script will help identify what's wrong with the JavaScript function
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

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from main_app.models import CustomUser, Division, Department

def test_details_button():
    """Test the Details button functionality"""
    print("=" * 60)
    print("TESTING DETAILS BUTTON FUNCTIONALITY")
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
    
    print(f"[OK] Created division: {division.name}")
    print(f"[OK] Created department: {department.name}")
    print(f"[OK] Created admin user: {admin_user.email}")
    
    # Test the admin GPS dashboard
    print("\n2. Testing admin GPS dashboard...")
    client.force_login(admin_user)
    
    try:
        response = client.get(reverse('admin_gps_dashboard'))
        print(f"[OK] Dashboard status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Check if the Details button exists
            if 'showDepartmentDetails' in content:
                print("[OK] showDepartmentDetails function found in template")
            else:
                print("[ERROR] showDepartmentDetails function NOT found in template")
            
            # Check if jQuery is loaded
            if 'jquery' in content.lower():
                print("[OK] jQuery reference found in template")
            else:
                print("[ERROR] jQuery reference NOT found in template")
            
            # Check if Bootstrap is loaded
            if 'bootstrap' in content.lower():
                print("[OK] Bootstrap reference found in template")
            else:
                print("[ERROR] Bootstrap reference NOT found in template")
            
            # Check if the button HTML exists
            if 'data-dept-id' in content:
                print("[OK] Details button HTML found in template")
            else:
                print("[ERROR] Details button HTML NOT found in template")
            
            # Look for JavaScript errors
            if 'function showDepartmentDetails' in content:
                print("[OK] showDepartmentDetails function definition found")
            else:
                print("[ERROR] showDepartmentDetails function definition NOT found")
            
            # Check for modal HTML
            if 'modal' in content.lower():
                print("[OK] Modal HTML found in template")
            else:
                print("[ERROR] Modal HTML NOT found in template")
                
        else:
            print(f"[ERROR] Dashboard failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Dashboard error: {e}")
    
    # Test the department details API
    print("\n3. Testing department details API...")
    
    try:
        api_url = reverse('api_department_details', kwargs={'department_id': department.id})
        response = client.get(api_url)
        print(f"[OK] API status: {response.status_code}")
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            print(f"[OK] API response: {data}")
        else:
            print(f"[ERROR] API failed: {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"[ERROR] API error: {e}")
    
    print("\n" + "=" * 60)
    print("DETAILS BUTTON TEST COMPLETED")
    print("=" * 60)
    
    # Cleanup
    print("\nCleaning up test data...")
    CustomUser.objects.filter(email="admin@test.com").delete()
    Division.objects.filter(name="Test Division").delete()
    print("[OK] Test data cleaned up")

if __name__ == "__main__":
    test_details_button()
