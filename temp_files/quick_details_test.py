"""
Quick test to verify the Details button is working
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

def quick_test():
    """Quick test of the Details button"""
    print("=" * 60)
    print("QUICK TEST: Details Button Functionality")
    print("=" * 60)
    
    # Create test client
    client = Client()
    
    # Create test data
    division = Division.objects.create(name="Test Division")
    department = Department.objects.create(name="Test Department", division=division)
    
    admin_user = CustomUser.objects.create_user(
        email="admin@test.com",
        password="adminpass123",
        user_type="1",
        first_name="Admin",
        last_name="User"
    )
    
    print(f"[OK] Created test data")
    
    # Test the admin GPS dashboard
    client.force_login(admin_user)
    
    try:
        response = client.get(reverse('admin_gps_dashboard'))
        print(f"[OK] Dashboard status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Check if the alert is in the function
            if 'alert(\'Details button clicked!' in content:
                print("[OK] Alert statement found in showDepartmentDetails function")
            else:
                print("[ERROR] Alert statement NOT found in showDepartmentDetails function")
            
            # Check if the function is defined
            if 'function showDepartmentDetails(' in content:
                print("[OK] showDepartmentDetails function definition found")
            else:
                print("[ERROR] showDepartmentDetails function definition NOT found")
            
            # Count how many times the function is defined
            function_count = content.count('function showDepartmentDetails(')
            print(f"[INFO] showDepartmentDetails function defined {function_count} times")
            
            if function_count > 1:
                print("[WARNING] Multiple showDepartmentDetails functions found - this could cause conflicts!")
            
            # Check if the button HTML exists
            if 'onclick="showDepartmentDetails(' in content:
                print("[OK] Details button onclick found in template")
            else:
                print("[ERROR] Details button onclick NOT found in template")
                
        else:
            print(f"[ERROR] Dashboard failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Dashboard error: {e}")
    
    # Cleanup
    CustomUser.objects.filter(email="admin@test.com").delete()
    Division.objects.filter(name="Test Division").delete()
    print("[OK] Test data cleaned up")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    print("\nINSTRUCTIONS:")
    print("1. Open your browser and go to: http://127.0.0.1:8000/admin/gps/dashboard/")
    print("2. Login as admin")
    print("3. Click any 'Details' button")
    print("4. You should see an alert popup saying 'Details button clicked!'")
    print("5. Check browser console (F12) for debug messages")

if __name__ == "__main__":
    quick_test()
