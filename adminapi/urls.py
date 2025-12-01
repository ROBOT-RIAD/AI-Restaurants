from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminRegisterApiView,AdminRestaurantListAPIView,AdminRestaurantDetailAPIView,ALLRestaurantStatus,RestaurantStatusDetailAPIView,UserApprovalUpdateAPIView,CallSummaryAPIView,TopSellingItemsAPIView,RestaurantCallStatsAPIView,AdminApprovalUpdateView,MonthlyRevenueAPIView,RestaurantAnalysis
from subscription.views import PackageViewSet
from AIvapi.views import AssistantCreateView,UpdateTwilioCredsAPIView
from support.views import SupportListAPIView,SupportDetailAPIView,SupportStatusUpdateAPIView
from accounts.views import AdminRestaurantDeleteAPIView
router = DefaultRouter()
router.register('packages', PackageViewSet)


urlpatterns = [
    path('user/register',AdminRegisterApiView.as_view()),
    path('restaurants/', AdminRestaurantListAPIView.as_view(), name='admin-restaurant-list'),
    path("assistant/create/", AssistantCreateView.as_view(), name="assistant-create"),
    path('admin/restaurant-detail/', AdminRestaurantDetailAPIView.as_view(), name='admin-restaurant-detail'),
    path('supports/', SupportListAPIView.as_view(), name='support-list'),
    path('supports/<int:pk>/', SupportDetailAPIView.as_view(), name='support-detail'),
    path('supports/status/<int:pk>/', SupportStatusUpdateAPIView.as_view(), name='support-update-status'),
    path('all/accounts/status/', ALLRestaurantStatus.as_view(), name='all-accounts-status'),
    path('all/accounts/status/<int:id>/', RestaurantStatusDetailAPIView.as_view(), name='restaurant-detail'),
    path('users/approval/update/<int:user_id>/', UserApprovalUpdateAPIView.as_view(), name='user-approval-update'),
    path('analytics/', CallSummaryAPIView.as_view(), name='analytics'),
    path('top-selling-items/', TopSellingItemsAPIView.as_view(), name='top-selling-items'),
    path('analytics/restaurant-call-stats/', RestaurantCallStatsAPIView.as_view(), name='restaurant-call-stats'),
    path('users/admin-approve/', AdminApprovalUpdateView.as_view(), name='admin-approve-self'),
    path('monthly-revenue/', MonthlyRevenueAPIView.as_view(), name='monthly-revenue'),
    path('assistance/update-twilio-creds/', UpdateTwilioCredsAPIView.as_view(), name='update-twilio-creds'),
    path('restaurant-stats/', RestaurantAnalysis.as_view(), name='restaurant-stats'),
    path('restaurant/delete/', AdminRestaurantDeleteAPIView.as_view(), name='admin-restaurant-delete'),
    path('api/', include(router.urls)),
]
