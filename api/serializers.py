from rest_framework import serializers
from django.contrib.auth import authenticate
from main_app.models import (
    CustomUser, Employee, Customer, JobCard, JobCardAction, 
    Order, OrderItem, Payment, Attendance,
    CommunicationLog, City, Item, Notification
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'profile_pic']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Invalid credentials.')
        else:
            raise serializers.ValidationError('Must include email and password.')

        return data


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'country']


class CustomerSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'code', 'city', 'city_name', 'address', 
                 'phone_primary', 'email', 'active']


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'uom', 'category']


class JobCardSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.admin.get_full_name', read_only=True)
    
    class Meta:
        model = JobCard
        fields = ['id', 'type', 'priority', 'status', 'assigned_to', 'assigned_to_name',
                 'customer', 'customer_name', 'city', 'city_name', 'due_at', 
                 'created_reason', 'created_at', 'updated_at']


class JobCardActionSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    
    class Meta:
        model = JobCardAction
        fields = ['id', 'jobcard', 'actor', 'actor_name', 'action', 
                 'timestamp', 'note_text', 'structured_json']


class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by_staff.admin.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'order_date', 
                 'created_by_staff', 'created_by_name', 'status', 
                 'total_bales', 'total_amount', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'item', 'item_name', 'cut', 'rate', 'qty_bales', 'amount']


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'customer', 'customer_name', 'order', 'payment_date', 
                 'method', 'amount', 'notes', 'created_at']




class CommunicationLogSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CommunicationLog
        fields = ['id', 'channel', 'direction', 'customer', 'customer_name',
                 'user', 'user_name', 'subject', 'body', 'timestamp', 'linkages']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'jobcard', 'channel', 'title', 'message',
                 'sent_at', 'delivered_at', 'created_at']
