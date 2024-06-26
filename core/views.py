import logging
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from core.models import User, Location, ChargingLogic, TransactionHistory, Day, Month, Year, Payment
from core.serializers import UserSerializer, LocationSerializer, ChargingLogicSerializer, TransactionHistorySerializer, PaymentSerializer
from django.db.models import Q, F
from math import radians, cos, sin, sqrt, atan2
from django.utils import timezone
from django.conf import settings
import stripe
import pytz
from decimal import Decimal
from django.utils.dateparse import parse_datetime 
from django.http import JsonResponse
from datetime import timedelta
from django.utils.dateparse import parse_datetime
import math
from shapely.geometry import Point, Polygon


logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Distance in meters

def is_point_in_polygon(lat, lon, polygon_points):
    point = Point(lon, lat)
    polygon = Polygon([(lng, lat) for lat, lng in polygon_points])
    logger.debug(f"Point: {point}, Polygon: {polygon}")
    is_within = polygon.contains(point)
    logger.debug(f"Point ({lat}, {lon}) is {'within' if is_within else 'NOT within'} the polygon.")
    return is_within

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.refresh_from_db()
        try:
            token, created = Token.objects.get_or_create(user=user)
        except Exception as e:
            logger.error(f"Error creating token: {str(e)}")
            user.delete()
            return Response({"detail": "Error creating token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user_data = serializer.data
        response_data = {**user_data, 'token': token.key}
        return Response(response_data, status=status.HTTP_201_CREATED)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserProfileUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    try:
        logger.debug(f"Authenticated user: {request.user}")
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving current user: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        logging.info(f"Current instance location_name: {instance.location_name}")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        logging.info(f"Updated location: {serializer.data}")
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()

class ChargingLogicViewSet(viewsets.ModelViewSet):
    queryset = ChargingLogic.objects.all()
    serializer_class = ChargingLogicSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            years = request.data.get('years', [])
            if not all(isinstance(year, int) for year in years):
                years = [int(year) for year in years]

            request.data['years'] = years
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except (ValueError, TypeError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

class TransactionHistoryViewSet(viewsets.ModelViewSet):
    queryset = TransactionHistory.objects.all().order_by('-timestamp')
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return TransactionHistory.objects.all().order_by('-timestamp')
        return TransactionHistory.objects.filter(user=user).order_by('-timestamp')


@api_view(['GET'])
def get_charging_logics(request):
    charging_logics = ChargingLogic.objects.all()
    serializer = ChargingLogicSerializer(charging_logics, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_charging_logic_status(request):
    charging_logics = ChargingLogic.objects.all()
    serializer = ChargingLogicSerializer(charging_logics, many=True)
    return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def enable_charging_logic(request, pk):
    try:
        charging_logic = ChargingLogic.objects.get(pk=pk)
        charging_logic.is_enabled = True
        charging_logic.save()
        logger.debug(f"Charging logic {pk} enabled.")
        return Response({"status": "enabled"}, status=status.HTTP_200_OK)
    except ChargingLogic.DoesNotExist:
        return Response({"error": "Charging logic not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error enabling charging logic: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def disable_charging_logic(request, pk):
    try:
        charging_logic = ChargingLogic.objects.get(pk=pk)
        charging_logic.is_enabled = False
        charging_logic.save()
        logger.debug(f"Charging logic {pk} disabled.")
        return Response({"status": "disabled"}, status=status.HTTP_200_OK)
    except ChargingLogic.DoesNotExist:
        return Response({"error": "Charging logic not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error disabling charging logic: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balance(request):
    try:
        user = request.user
        logger.debug(f"User balance fetched: {user.balance}")
        return Response({'balance': user.balance}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching balance: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_charging_logic_by_location(request):
    try:
        data = request.data
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        timestamp = data.get('timestamp')

        if latitude is None or longitude is None or timestamp is None:
            return Response({'error': 'Invalid data: latitude, longitude, and timestamp are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            parsed_timestamp = parse_datetime(timestamp)
            if parsed_timestamp is None:
                raise ValueError("Invalid ISO format string")
        except (ValueError, TypeError) as e:
            return Response({"error": "Invalid input"}, status=status.HTTP_400_BAD_REQUEST)

        current_datetime = timezone.localtime(parsed_timestamp)
        current_time = current_datetime.time()

        charging_logics = ChargingLogic.objects.filter(
            Q(is_enabled=True) &
            (
                Q(start_time__lte=current_time, end_time__gte=current_time) |
                Q(start_time__lte=current_time, end_time__lte=F('start_time')) |
                Q(start_time__gte=F('end_time'), end_time__gte=current_time)
            )
        )

        for logic in charging_logics:
            location = logic.location
            within_geofence = False

            if location.polygon_points:
                points = [(float(point['lat']), float(point['lng'])) for point in location.polygon_points]
                logger.debug(f"Checking point ({latitude}, {longitude}) within polygon: {points}")
                if is_point_in_polygon(latitude, longitude, points):
                    logger.debug(f"Point ({latitude}, {longitude}) is within the polygon.")
                    within_geofence = True
                else:
                    logger.debug(f"Point ({latitude}, {longitude}) is NOT within the polygon.")

            if location.latitude is not None and location.longitude is not None and location.radius is not None:
                radius = float(location.radius)
                distance = haversine(latitude, longitude, float(location.latitude), float(location.longitude))
                logger.debug(f"Calculated distance to location {location.location_name}: {distance:.2f} meters, Radius: {radius:.2f} meters")
                if distance <= radius:
                    logger.debug(f"Point ({latitude}, {longitude}) is within the radius of {radius} meters.")
                    within_geofence = True
                else:
                    logger.debug(f"Point ({latitude}, {longitude}) is NOT within the radius of {radius} meters.")

            if within_geofence:
                serializer = ChargingLogicSerializer(logic)
                return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'message': 'No charging logic found for the given location'}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_transaction(request):
    logger.debug(f"Request received with method: {request.method}, data: {request.data}")
    if request.method != 'POST':
        logger.debug("Invalid HTTP method used.")
        return Response({"error": "Invalid HTTP method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    serializer = TransactionHistorySerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        logger.debug("Transaction created successfully.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    logger.debug(f"Serializer errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

###
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_and_charge_user(request):
    try:
        data = request.data
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        timestamp = data.get('timestamp')

        if latitude is None or longitude is None or timestamp is None:
            return Response({'error': 'Invalid data: latitude, longitude, and timestamp are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            parsed_timestamp = parse_datetime(timestamp)
            if parsed_timestamp is None:
                raise ValueError("Invalid ISO format string")
        except (ValueError, TypeError) as e:
            return Response({"error": "Invalid input"}, status=status.HTTP_400_BAD_REQUEST)

        current_datetime = timezone.localtime(parsed_timestamp)
        current_time = current_datetime.time()
        current_day = current_datetime.strftime('%A')
        current_month = current_datetime.strftime('%B')
        current_year = current_datetime.year

        charging_logics = ChargingLogic.objects.filter(
            Q(is_enabled=True) &
            (
                Q(start_time__lte=current_time, end_time__gte=current_time) |
                Q(start_time__lte=current_time, end_time__lte=F('start_time')) |
                Q(start_time__gte=F('end_time'), end_time__gte=current_time)
            )
        )

        user = request.user
        original_balance = user.balance  # Capture the original balance
        charge_applied = False

        for logic in charging_logics:
            location = logic.location

            if not logic.days.filter(name__iexact=current_day).exists():
                continue

            if not logic.months.filter(name__iexact=current_month).exists():
                continue

            if not logic.years.filter(year=current_year).exists():
                continue

            within_geofence = False

            if location.polygon_points:
                points = [(float(point['lat']), float(point['lng'])) for point in location.polygon_points]
                if is_point_in_polygon(latitude, longitude, points):
                    within_geofence = True

            if location.latitude is not None and location.longitude is not None and location.radius is not None:
                radius = float(location.radius)
                distance = haversine(latitude, longitude, float(location.latitude), float(location.longitude))
                if distance <= radius:
                    within_geofence = True

            if not within_geofence:
                continue

            if user.last_check_in is None:
                user.last_check_in = current_datetime
                user.save()
                continue  # Skip charging for the first check-in

            time_elapsed = current_datetime - user.last_check_in
            total_seconds_elapsed = time_elapsed.total_seconds()

            interval_elapsed = False
            if logic.amount_rate == 'second' and total_seconds_elapsed >= 1:
                interval_elapsed = True
            elif logic.amount_rate == 'minute' and total_seconds_elapsed >= 60:
                interval_elapsed = True
            elif logic.amount_rate == 'hour' and total_seconds_elapsed >= 3600:
                interval_elapsed = True
            elif logic.amount_rate == 'day' and total_seconds_elapsed >= 86400:
                interval_elapsed = True
            elif logic.amount_rate == 'week' and total_seconds_elapsed >= 604800:
                interval_elapsed = True
            elif logic.amount_rate == 'month' and total_seconds_elapsed >= 2592000:
                interval_elapsed = True

            if interval_elapsed:
                amount_to_deduct = Decimal(logic.amount_to_charge)
                user.balance -= amount_to_deduct
                user.last_check_in = current_datetime
                user.save()

                transaction = TransactionHistory.objects.create(
                    user=user,
                    location=location,
                    amount=amount_to_deduct,
                    amount_rate=logic.amount_rate
                )
                transaction_serializer = TransactionHistorySerializer(transaction)
                location_serializer = LocationSerializer(location)
                response_data = {
                    'transaction': transaction_serializer.data,
                    'location': location_serializer.data,
                    'charging_logic': {
                        'amount_to_charge': logic.amount_to_charge,
                        'amount_rate': logic.amount_rate
                    },
                    'balance': user.balance,
                    'original_balance': original_balance  
                }
                charge_applied = True
                break  # Exit the loop after the first applicable charge

        if not charge_applied:
            return Response({'balance': user.balance, 'original_balance': original_balance}, status=status.HTTP_200_OK)  

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_payment(request):
    user = request.user
    amount = request.data.get('amount')
    payment_method_id = request.data.get('paymentMethodId')

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100), 
            currency='usd',
            payment_method=payment_method_id,
            confirmation_method='manual',
            confirm=True,
            return_url="http://localhost:8000/"
        )

        if payment_intent['status'] == 'succeeded':
            user.balance += Decimal(str(amount))  
            user.save()
            logger.debug(f"Payment succeeded. Updated balance: {user.balance}")

        return Response({
            'client_secret': payment_intent['client_secret'],
            'status': payment_intent['status']
        }, status=status.HTTP_200_OK)

    except stripe.error.CardError as e:
        logger.error(f"Stripe error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error making payment: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    user = request.user
    payments = Payment.objects.filter(user=user).order_by('-timestamp')
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)