import logging
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from core.models import User, Location, ChargingLogic, TransactionHistory, Day, Month, Year
from core.serializers import UserSerializer, LocationSerializer, ChargingLogicSerializer, TransactionHistorySerializer
from django.db.models import Q
from math import radians, cos, sin, sqrt, atan2
from django.utils import timezone
from datetime import datetime
import pytz
from django.http import JsonResponse

logger = logging.getLogger(__name__)

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    try:
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
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
    queryset = TransactionHistory.objects.all()
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
def get_charging_logics(request):
    charging_logics = ChargingLogic.objects.all()
    serializer = ChargingLogicSerializer(charging_logics, many=True)
    print("Serialized data:", serializer.data)
    return Response(serializer.data)

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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Distance in kilometers

def is_point_in_polygon(lat, lon, polygon_points):
    num = len(polygon_points)
    j = num - 1
    inside = False

    for i in range(num):
        xi, yi = polygon_points[i]
        xj, yj = polygon_points[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_charging_logic_by_location(request):
    try:
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))

        # Get the current time in the Singapore time zone
        singapore_tz = pytz.timezone('Asia/Singapore')
        current_time = timezone.localtime(timezone.now(), singapore_tz).time()

        logger.debug(f"Received coordinates: latitude={latitude}, longitude={longitude}, current_time={current_time}")

        charging_logics = ChargingLogic.objects.filter(
            Q(start_time__lte=current_time) &
            Q(end_time__gte=current_time)
        )

        logger.debug(f"Number of charging logics found: {charging_logics.count()}")

        for logic in charging_logics:
            location = logic.location
            if location.latitude is not None and location.longitude is not None:
                distance = haversine(latitude, longitude, float(location.latitude), float(location.longitude))
                logger.debug(f"Calculated distance to location {location.location_name}: {distance} km, Radius: {location.radius} km")

                if distance <= float(location.radius):
                    serializer = ChargingLogicSerializer(logic)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            
            if location.polygon_points:
                if is_point_in_polygon(latitude, longitude, location.polygon_points):
                    serializer = ChargingLogicSerializer(logic)
                    return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'error': 'No charging logic found for the given location'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_transaction(request):
    try:
        user = request.user
        location_id = request.data.get('location_id')
        amount = request.data.get('amount')

        if not location_id or not amount:
            return Response({'error': 'Location ID and Amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        location = Location.objects.get(id=location_id)
        amount = float(amount)

        transaction = TransactionHistory.objects.create(user=user, location=location, amount=amount)
        user.balance -= amount
        user.save()

        logger.debug(f"Transaction created: {transaction}, new balance: {user.balance}")

        return Response({'balance': user.balance}, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)