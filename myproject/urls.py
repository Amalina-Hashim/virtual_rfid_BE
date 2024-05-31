from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views
from rest_framework.authtoken.views import obtain_auth_token
from core.views import UserProfileUpdateView, disable_charging_logic, enable_charging_logic

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'charging-logics', views.ChargingLogicViewSet)
router.register(r'transactions', views.TransactionHistoryViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', obtain_auth_token, name='api_token_auth'),
    path('api/register/', views.UserCreateView.as_view(), name='register'),
    path('api/charging-logics/', views.get_charging_logics, name='get_charging_logics'),
    path('api/balance/', views.get_balance, name='get_balance'),
    path('api/charging-logic/location/', views.get_charging_logic_by_location, name='get_charging_logic_by_location'),
    path('api/current-user/', views.get_current_user, name='get_current_user'),
    path('api/users/me/', views.get_current_user, name='get_current_user'),
    path('api/profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('api/transactions/create/', views.create_transaction, name='create_transaction'),
    path('api/check-and-charge/', views.check_and_charge_user, name='check_and_charge_user'),
    path('api/make-payment/', views.make_payment, name='make_payment'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('api/charging-logics/<int:pk>/disable/', disable_charging_logic, name='disable_charging_logic'),
    path('api/charging-logics/<int:pk>/enable/', enable_charging_logic, name='enable_charging_logic'),
    path('api/charging-logic/status/', views.get_charging_logic_status, name='charging_logic_status'),
]

