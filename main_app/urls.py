"""axpect_tech_config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from main_app.EditSalaryView import EditSalaryView

from . import ceo_views, manager_views, employee_views, views, jobcard_views, gps_views

urlpatterns = [
    path("", views.login_page, name='login_page'),
    path("get_attendance", views.get_attendance, name='get_attendance'),
    path("firebase-messaging-sw.js", views.showFirebaseJS, name='showFirebaseJS'),
    path("doLogin/", views.doLogin, name='user_login'),
    path("logout_user/", views.logout_user, name='user_logout'),
    path("admin/home/", ceo_views.admin_home, name='admin_home'),
    path("manager/add", ceo_views.add_manager, name='add_manager'),
    path("division/add", ceo_views.add_division, name='add_division'),
    path("send_employee_notification/", ceo_views.send_employee_notification,
         name='send_employee_notification'),
    path("send_manager_notification/", ceo_views.send_manager_notification,
         name='send_manager_notification'),
    path("admin_notify_employee", ceo_views.admin_notify_employee,
         name='admin_notify_employee'),
    path("admin_notify_manager", ceo_views.admin_notify_manager,
         name='admin_notify_manager'),
    path("admin_view_profile", ceo_views.admin_view_profile,
         name='admin_view_profile'),
    path("check_email_availability", ceo_views.check_email_availability,
         name="check_email_availability"),
    path("employee/view/feedback/", ceo_views.employee_feedback_message,
         name="employee_feedback_message",),
    path("manager/view/feedback/", ceo_views.manager_feedback_message,
         name="manager_feedback_message",),
    path("employee/view/leave/", ceo_views.view_employee_leave,
         name="view_employee_leave",),
    path("manager/view/leave/", ceo_views.view_manager_leave, name="view_manager_leave",),
    path("attendance/view/", ceo_views.admin_view_attendance,
         name="admin_view_attendance",),
    path("attendance/fetch/", ceo_views.get_admin_attendance,
         name='get_admin_attendance'),
    
    # Test URLs
    path("test-attendance/", views.test_attendance_page, name='test_attendance_page'),
    path("test-ajax/", views.test_ajax, name='test_ajax'),
    
    
    
    # Job Card URLs
    path("admin/job-cards/", jobcard_views.admin_job_card_dashboard,
         name='admin_job_card_dashboard'),
    path("admin/job-cards/create/", jobcard_views.admin_create_job_card,
         name='admin_create_job_card'),
    path("manager/job-cards/", jobcard_views.manager_job_card_dashboard,
         name='manager_job_card_dashboard'),
    path("manager/job-cards/create/", jobcard_views.manager_create_job_card,
         name='manager_create_job_card'),
    path("employee/job-cards/", jobcard_views.employee_job_card_dashboard,
         name='employee_job_card_dashboard'),
    path("job-card/<int:job_card_id>/", jobcard_views.job_card_detail,
         name='job_card_detail'),
    path("api/job-card/update-status/", jobcard_views.update_job_card_status,
         name='update_job_card_status'),
    
    # Customer Management URLs
    path("admin/customers/", ceo_views.admin_customer_list,
         name='admin_customer_list'),
    path("admin/customers/create/", ceo_views.admin_customer_create,
         name='admin_customer_create'),
    path("admin/customers/edit/<int:customer_id>/", ceo_views.admin_customer_edit,
         name='admin_customer_edit'),
    path("admin/customers/delete/<int:customer_id>/", ceo_views.admin_customer_delete,
         name='admin_customer_delete'),
    path("admin/customers/toggle-status/<int:customer_id>/", ceo_views.admin_customer_toggle_status,
         name='admin_customer_toggle_status'),
    path("employee/add/", ceo_views.add_employee, name='add_employee'),
    path("department/add/", ceo_views.add_department, name='add_department'),
    path("manager/manage/", ceo_views.manage_manager, name='manage_manager'),
    path("employee/manage/", ceo_views.manage_employee, name='manage_employee'),
    path("division/manage/", ceo_views.manage_division, name='manage_division'),
    path("department/manage/", ceo_views.manage_department, name='manage_department'),
    path("customers/manage/", ceo_views.customers_manage, name='customers_manage'),
    path("customers/add/", ceo_views.customer_add, name='customer_add'),
    path("customers/<int:customer_id>/edit/", ceo_views.customer_edit, name='customer_edit'),
    path("customers/<int:customer_id>/delete/", ceo_views.customer_delete, name='customer_delete'),
    path("customers/<int:customer_id>/toggle-status/", ceo_views.customer_toggle_status, name='customer_toggle_status'),
    path("manager/edit/<int:manager_id>", ceo_views.edit_manager, name='edit_manager'),
    path("manager/delete/<int:manager_id>",
         ceo_views.delete_manager, name='delete_manager'),

    path("division/delete/<int:division_id>",
         ceo_views.delete_division, name='delete_division'),

    path("department/delete/<int:department_id>",
         ceo_views.delete_department, name='delete_department'),

    path("employee/delete/<int:employee_id>",
         ceo_views.delete_employee, name='delete_employee'),
    path("employee/edit/<int:employee_id>",
         ceo_views.edit_employee, name='edit_employee'),
    path("division/edit/<int:division_id>",
         ceo_views.edit_division, name='edit_division'),
    path("department/edit/<int:department_id>",
         ceo_views.edit_department, name='edit_department'),


    # Manager
    path("manager/home/", manager_views.manager_home, name='manager_home'),
    path("manager/apply/leave/", manager_views.manager_apply_leave,
         name='manager_apply_leave'),
    path("manager/feedback/", manager_views.manager_feedback, name='manager_feedback'),
    path("manager/view/profile/", manager_views.manager_view_profile,
         name='manager_view_profile'),
    path("manager/attendance/take/", manager_views.manager_take_attendance,
         name='manager_take_attendance'),
    path("manager/attendance/update/", manager_views.manager_update_attendance,
         name='manager_update_attendance'),
    path("manager/get_employees/", manager_views.get_employees, name='get_employees'),
    path("manager/attendance/fetch/", manager_views.get_employee_attendance,
         name='get_employee_attendance'),
    path("manager/attendance/save/",
         manager_views.save_attendance, name='save_attendance'),
    path("manager/attendance/update/",
         manager_views.update_attendance, name='update_attendance'),
    path("manager/fcmtoken/", manager_views.manager_fcmtoken, name='manager_fcmtoken'),
    path("manager/view/notification/", manager_views.manager_view_notification,
         name="manager_view_notification"),
    path("manager/salary/add/", manager_views.manager_add_salary, name='manager_add_salary'),
    path("manager/salary/edit/", EditSalaryView.as_view(),
         name='edit_employee_salary'),
    path('manager/salary/fetch/', manager_views.fetch_employee_salary,
         name='fetch_employee_salary'),
    
    # Manager GPS Attendance
    path('manager/gps/attendance/', manager_views.manager_gps_attendance, name='manager_gps_attendance'),
    path('manager/gps/checkin/', manager_views.manager_gps_checkin, name='manager_gps_checkin'),
    path('manager/gps/checkout/', manager_views.manager_gps_checkout, name='manager_gps_checkout'),
    path('manager/gps/history/', manager_views.manager_gps_history, name='manager_gps_history'),
    
    



    # Employee GPS Views
    path("employee/gps/dashboard/", gps_views.employee_gps_dashboard, name='employee_gps_dashboard'),
    path("employee/gps/checkin/", gps_views.employee_gps_checkin, name='employee_gps_checkin'),
    path("employee/gps/checkout/", gps_views.employee_gps_checkout, name='employee_gps_checkout'),
    path("employee/gps/history/", gps_views.employee_gps_history, name='employee_gps_history'),
    path("employee/live-location/", gps_views.employee_live_location, name='employee_live_location'),
    
    # Manager GPS Views
    path("manager/gps/dashboard/", gps_views.manager_gps_dashboard, name='manager_gps_dashboard'),
    path("manager/employee-locations/", gps_views.manager_employee_locations, name='manager_employee_locations'),
    path("manager/attendance-reports/", gps_views.manager_attendance_reports, name='manager_attendance_reports'),
    path("manager/gps/employee/<int:employee_id>/", gps_views.manager_employee_details, name='manager_employee_details'),
    
    # CEO GPS Views  
    path("admin/gps/dashboard/", gps_views.admin_gps_dashboard, name='admin_gps_dashboard'),
    path("admin/gps/details/<int:employee_id>/", gps_views.admin_gps_employee_details, name='admin_gps_employee_details'),
    path("admin/location-analytics/", gps_views.admin_location_analytics, name='admin_location_analytics'),
    path("admin/geofence-management/", gps_views.admin_geofence_management, name='admin_geofence_management'),
    
    # GPS API Endpoints
    path('api/gps/checkin/', gps_views.api_gps_checkin, name='api_gps_checkin'),
    path('api/gps/checkout/', gps_views.api_gps_checkout, name='api_gps_checkout'),
    path('api/gps/location-update/', gps_views.api_gps_location_update, name='api_gps_location_update'),
    path('api/employee-current-location/', gps_views.api_employee_current_location, name='api_employee_current_location'),
    path('api/department/<int:department_id>/details/', gps_views.api_department_details, name='api_department_details'),
    
    # Real-Time GPS API Endpoints
    path('api/team-locations/', gps_views.api_team_locations, name='api_team_locations'),
    path('api/employee-route-history/', gps_views.api_employee_route_history, name='api_employee_route_history'),
    path('api/geofence-status/', gps_views.api_geofence_status, name='api_geofence_status'),

    # Employee
    path("employee/home/", employee_views.employee_home, name='employee_home'),
    path("employee/view/attendance/", employee_views.employee_view_attendance,
         name='employee_view_attendance'),
    path("employee/apply/leave/", employee_views.employee_apply_leave,
         name='employee_apply_leave'),
    path("employee/feedback/", employee_views.employee_feedback,
         name='employee_feedback'),
    path("employee/view/profile/", employee_views.employee_view_profile,
         name='employee_view_profile'),
    path("employee/fcmtoken/", employee_views.employee_fcmtoken,
         name='employee_fcmtoken'),
    path("employee/view/notification/", employee_views.employee_view_notification,
         name="employee_view_notification"),
    path('employee/view/salary/', employee_views.employee_view_salary,
         name='employee_view_salary'),
    path('employee/jobcards/', employee_views.employee_jobcards, name='employee_jobcards'),
    path('employee/orders/new/', employee_views.order_create, name='order_create'),
    path('employee/orders/new/<int:jobcard_id>/', employee_views.order_create, name='order_create_for_jobcard'),
    path('employee/targets/', employee_views.employee_targets, name='employee_targets'),
    
    

    # Minimal CRM & Jobcards
    path('api/jobcards/create/', views.jobcard_create, name='jobcard_create'),
    path('api/jobcards/my/', views.jobcard_list_my, name='jobcard_list_my'),
    path('api/jobcards/<int:jobcard_id>/status/', views.jobcard_update_status, name='jobcard_update_status'),
    path('api/customers/', views.customers_list, name='customers_list'),
    path('api/customers/create/', views.customers_create, name='customers_create'),
    path('api/nlp/parse-followup/', views.nlp_parse_and_followup, name='nlp_parse_and_followup'),
    path('api/comm/create/', views.comm_create, name='comm_create'),
    path('api/comm/list/', views.comm_list, name='comm_list'),
    path('api/cadence/generate/', views.cadence_generate, name='cadence_generate'),
    path('api/email/send/', views.email_send_stub, name='email_send_stub'),
    path('api/whatsapp/webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
]
