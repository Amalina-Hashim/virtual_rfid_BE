from rest_framework import serializers
from .models import User, Location, ChargingLogic, TransactionHistory, Day, Month, Year, Payment

class DayField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Day.objects.get_or_create(name=data)[0]

class MonthField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Month.objects.get_or_create(name=data)[0]

class YearField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        return Year.objects.get_or_create(year=int(data))[0]

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'balance', 'role', 'first_login']

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

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'country', 'latitude', 'longitude', 'address_name', 'location_name', 'radius', 'polygon_points']

class ChargingLogicSerializer(serializers.ModelSerializer):
    days = DayField(slug_field='name', queryset=Day.objects.all(), many=True)
    months = MonthField(slug_field='name', queryset=Month.objects.all(), many=True)
    years = YearField(slug_field='year', queryset=Year.objects.all(), many=True)
    location_name = serializers.SerializerMethodField()
    location = LocationSerializer()  

    class Meta:
        model = ChargingLogic
        fields = ['id', 'location', 'start_time', 'end_time', 'amount_to_charge', 'amount_rate', 'days', 'months', 'years', 'location_name', 'is_enabled']

    def get_location_name(self, obj):
        return obj.location.location_name if obj.location else None

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        days_data = validated_data.pop('days')
        months_data = validated_data.pop('months')
        years_data = validated_data.pop('years')
        
        location = Location.objects.create(**location_data)
        charging_logic = ChargingLogic.objects.create(location=location, **validated_data)

        # Set many-to-many relationships
        charging_logic.days.set(days_data)
        charging_logic.months.set(months_data)
        charging_logic.years.set(years_data)

        return charging_logic

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        days = validated_data.pop('days', None)
        months = validated_data.pop('months', None)
        years = validated_data.pop('years', None)

        if location_data:
            for attr, value in location_data.items():
                setattr(instance.location, attr, value)
            instance.location.save()

        if days:
            instance.days.set(days)
        if months:
            instance.months.set(months)
        if years:
            instance.years.set(years)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class TransactionHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    userId = serializers.IntegerField(source='user.id', read_only=True)
    location = LocationSerializer()

    class Meta:
        model = TransactionHistory
        fields = ['id', 'userId', 'username', 'location', 'amount', 'timestamp', 'amount_rate']
        read_only_fields = ['id', 'user', 'timestamp', 'location']


    def create(self, validated_data):
        location_id = validated_data.pop('location_id')
        location = Location.objects.get(id=location_id)
        user = self.context['request'].user
        transaction = TransactionHistory.objects.create(user=user, location=location, **validated_data)
        return transaction

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['id', 'user', 'timestamp']