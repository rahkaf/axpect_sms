from django import forms
from django.forms import Form
from .models import *
from django.forms.widgets import DateInput, TextInput


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'


class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'gender',  'password','profile_pic', 'address' ]


class EmployeeForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Employee
        fields = CustomUserForm.Meta.fields + \
            ['division', 'department']


class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields


class ManagerForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(ManagerForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Manager
        fields = CustomUserForm.Meta.fields + \
            ['division' ]


class DivisionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(DivisionForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name']
        model = Division


class DepartmentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(DepartmentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Department
        fields = ['name', 'division']


class LeaveReportManagerForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportManagerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportManager
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackManagerForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackManagerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackManager
        fields = ['feedback']


class LeaveReportEmployeeForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportEmployeeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportEmployee
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackEmployeeForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackEmployeeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackEmployee
        fields = ['feedback']


class EmployeeEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(EmployeeEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Employee
        fields = CustomUserForm.Meta.fields 


class ManagerEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(ManagerEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Manager
        fields = CustomUserForm.Meta.fields


class EditSalaryForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(EditSalaryForm, self).__init__(*args, **kwargs)

    class Meta:
        model = EmployeeSalary
        fields = ['department', 'employee', 'base', 'ctc']


class CityForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CityForm, self).__init__(*args, **kwargs)

    class Meta:
        model = City
        fields = ['name', 'state', 'country']


class CustomerForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CustomerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Customer
        fields = ['name', 'code', 'city', 'address', 'phone_primary', 'email', 'active', 'owner_staff']


class JobCardForm(FormSettings):
    """Form for creating and editing job cards"""
    
    # Add title as a form field (not a model field)
    title = forms.CharField(
        max_length=200, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter job card title'})
    )
    
    # Note: estimated_hours field removed - doesn't exist in database
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(JobCardForm, self).__init__(*args, **kwargs)
        
        # Populate title from description if editing
        if self.instance and self.instance.pk and self.instance.description:
            lines = self.instance.description.split('\n')
            if lines:
                self.fields['title'].initial = lines[0].strip()
        
        # Filter assigned_to based on user role - use Employee model
        if self.user:
            if self.user.user_type == '1':  # Admin - can assign to anyone
                from .models import Employee
                self.fields['assigned_to'].queryset = Employee.objects.all().order_by('admin__first_name', 'admin__last_name')
            elif self.user.user_type == '2':  # Manager - can assign to employees in their division
                try:
                    from .models import Manager, Employee
                    manager = Manager.objects.get(admin=self.user)
                    self.fields['assigned_to'].queryset = Employee.objects.filter(
                        division=manager.division
                    ).order_by('admin__first_name', 'admin__last_name')
                except Manager.DoesNotExist:
                    self.fields['assigned_to'].queryset = Employee.objects.none()
        
        # Set widget attributes for existing fields
        if 'due_date' in self.fields:
            self.fields['due_date'].widget = forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            )
        if 'description' in self.fields:
            self.fields['description'].widget = forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Combine title and description into the description field
        title = self.cleaned_data.get('title', '')
        description = self.cleaned_data.get('description', '')
        
        # Create a structured description with title and details
        if title and description:
            instance.description = f"{title}\n\n{description}"
        elif title:
            instance.description = title
        elif description:
            instance.description = description
        
        if commit:
            instance.save()
        return instance
    
    class Meta:
        model = JobCard
        fields = [
            'type', 'description', 'assigned_to', 'priority', 'due_date',
            'customer', 'city', 'related_item'
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'related_item': forms.Select(attrs={'class': 'form-control'}),
        }


class JobCardUpdateForm(FormSettings):
    """Form for updating job card status and progress"""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(JobCardUpdateForm, self).__init__(*args, **kwargs)
        
        # Only show relevant fields based on user role
        if self.user and self.user.user_type == '3':  # Employee
            # Employees can only update status and description
            self.fields = {
                'status': self.fields['status'],
                'description': self.fields['description'],
            }
    
    class Meta:
        model = JobCard
        fields = [
            'status', 'description'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class JobCardCommentForm(FormSettings):
    """Form for adding comments to job cards"""
    
    def __init__(self, *args, **kwargs):
        super(JobCardCommentForm, self).__init__(*args, **kwargs)
        self.fields['comment'].widget = forms.Textarea(
            attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add your comment...'}
        )
    
    class Meta:
        model = JobCardComment
        fields = ['comment']


class JobCardTimeLogForm(FormSettings):
    """Form for logging time on job cards"""
    
    def __init__(self, *args, **kwargs):
        super(JobCardTimeLogForm, self).__init__(*args, **kwargs)
        self.fields['start_time'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        )
        self.fields['end_time'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        )
        self.fields['description'].widget = forms.Textarea(
            attrs={'rows': 2, 'class': 'form-control'}
        )
    
    class Meta:
        model = JobCardTimeLog
        fields = ['start_time', 'end_time', 'description']