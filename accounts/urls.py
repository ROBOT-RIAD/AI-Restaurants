from django.urls import path
from .views import RegisterApiView,LoginAPIView,CustomTokenRefreshView,SendOTPView,VerifyOTPView,ResetPasswordView,RestaurantFullDataAPIView
from subscription.views import PublicPackageListView
from customerService.views import CreateCustomerService
from table.views import PublicReservationCreateAPIView
from order.views import PublicOrderCreateAPIView


urlpatterns = [
    path('register/', RegisterApiView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('packages/', PublicPackageListView.as_view(), name='public-package-list'),
    path('create-customer-service/', CreateCustomerService.as_view(), name='create-customer-service'),
    path("restaurants/full-data/", RestaurantFullDataAPIView.as_view(), name="restaurant-full-data"),
    path("public/reservations/create/", PublicReservationCreateAPIView.as_view(), name="public-reservation-create"),
    path("public/orders/create/", PublicOrderCreateAPIView.as_view(), name="public-order-create"),
]
