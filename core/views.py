import logging
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from core.models import User, Location, ChargingLogic, TransactionHistory, Day, Month, Year
from core.serializers import UserSerializer, LocationSerializer, ChargingLogicSerializer, TransactionHistorySerializer

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

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

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

class TransactionHistoryViewSet(viewsets.ModelViewSet):
    queryset = TransactionHistory.objects.all()
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]
