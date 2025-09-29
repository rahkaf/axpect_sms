from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


class UserModel(UserAdmin):
    ordering = ('email',)


admin.site.register(CustomUser, UserModel)
admin.site.register(Manager)
admin.site.register(Employee)
admin.site.register(Division)
admin.site.register(Department)
admin.site.register(City)
admin.site.register(Customer)
admin.site.register(CustomerContact)
admin.site.register(Item)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(JobCard)
admin.site.register(JobCardAction)
admin.site.register(StaffScoresDaily)
admin.site.register(CommunicationLog)
admin.site.register(Targets)

# Additional PRD models
admin.site.register(Attendance)
admin.site.register(AttendanceReport)
admin.site.register(LeaveReportEmployee)
admin.site.register(LeaveReportManager)
admin.site.register(FeedbackEmployee)
admin.site.register(FeedbackManager)
admin.site.register(NotificationManager)
admin.site.register(NotificationEmployee)
admin.site.register(EmployeeSalary)
admin.site.register(StaffCapability)
admin.site.register(CustomerCapability)
admin.site.register(PriceList)
admin.site.register(Payment)
admin.site.register(PaymentInstrument)
admin.site.register(BusinessCalendar)
admin.site.register(RateAlert)
admin.site.register(CityWeekdayPlan)
admin.site.register(Notification)
admin.site.register(AIProcessingLog)
