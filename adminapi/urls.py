from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminRegisterApiView,AdminRestaurantListAPIView
from subscription.views import PackageViewSet

router = DefaultRouter()
router.register('packages', PackageViewSet)


urlpatterns = [
    path('user/register',AdminRegisterApiView.as_view()),
    path('restaurants/', AdminRestaurantListAPIView.as_view(), name='admin-restaurant-list'),
    path('api/', include(router.urls)),
]
