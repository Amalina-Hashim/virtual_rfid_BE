from rest_framework import serializers
from .models import User, Location, ChargingLogic, TransactionHistory, Day, Month, Year

class DayField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Day.objects.get_or_create(name=data)[0]

class MonthField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Month.objects.get_or_create(name=data)[0]

class YearField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Year.objects.get_or_create(year=data)[0]

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'balance', 'role']

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            role=validated_data.get('role', 'user'),
            is_active=True  
        )
        user.set_password(validated_data['password'])  
        user.save()
        return user

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'country', 'latitude', 'longitude', 'address_name', 'location_name', 'radius', 'polygon_points']

class ChargingLogicSerializer(serializers.ModelSerializer):
    days = DayField(slug_field='name', queryset=Day.objects.all(), many=True)
    months = MonthField(slug_field='name', queryset=Month.objects.all(), many=True)
    years = YearField(slug_field='year', queryset=Year.objects.all(), many=True)

    class Meta:
        model = ChargingLogic
        fields = ['id', 'location', 'start_time', 'end_time', 'amount_to_charge', 'amount_rate', 'days', 'months', 'years']

class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = ['id', 'user', 'location', 'timestamp', 'amount']
