from django.urls import path,include
from rest_framework.routers import DefaultRouter
from customer.views import CustomerViewSet

from restaurants.views import OpenAndCloseTimeAPIView, OpenAndCloseTimeDetailAPIView
from .views import UserRestaurantDetailView,UpdateRestaurantInfo,RestaurantStatsAPIView,RestaurantMonthlyStatsAPIView
from items.views import ItemCreateAPIView,ItemListAPIView,ItemDetailAPIView,ItemUpdateAPIView,ItemDeleteAPIView,RestaurantCategoriesAPIView,MenuExtractorView
from table.views import TableCreateView,TableListView,TableDetailApiView,TableUpdateAPIView,TableDeleteApiView,ReservationCreateAPIView,RestaurantReservationsAPIView,TableReservationStatusUpdateView,ReservationDetailView,ReservationUpdateAPIView,ReservationStatsView,TableReservationsView
from order.views import OrderCreateAPIView,OrderUpdateAPIView,RestaurantOrdersView,CustomerOrdersByPhoneAPIView,RestaurantOrderStatsAPIView,RestaurantSingleOrderView
from customerService.views import CustomerSummaryAPIView,PendingCallbacksView
from AIvapi.views import UserCallInformationAPIView,UserSingleCallInformationAPIView,UpdateCallCallbackAPIView,UpdateVoiceIdAPIView,UpdateTwilioCredsAPIView,GetRestaurantAssistantAPIView
from support.views import CreateSupportView
from extras.views import ExtraViewSet
from delivery_management.views import AreaManagementListCreateView, AreaManagementDetailView
router = DefaultRouter()

router.register("customers", CustomerViewSet, basename="customers")
router.register(r'extras', ExtraViewSet, basename='extras')


urlpatterns = [
    path('profile/', UserRestaurantDetailView.as_view(), name='user_profile'),
    path('resturant/', UpdateRestaurantInfo.as_view(), name='resturant'),
    path('items/create/', ItemCreateAPIView.as_view(), name='item-create'),
    path('items/', ItemListAPIView.as_view(), name='item-list'),
    path('items/<int:pk>/', ItemDetailAPIView.as_view(), name='item-detail'),
    path('items/update/<int:pk>/', ItemUpdateAPIView.as_view(), name='item-update'),
    path('items/delete/<int:pk>/', ItemDeleteAPIView.as_view(), name='item-delete'),
    path('restaurants/categories/', RestaurantCategoriesAPIView.as_view(), name='restaurant-categories'),
    path('extract-menu/', MenuExtractorView.as_view(), name='extract-menu'),
    path('table/create/', TableCreateView.as_view(), name='table-create'),
    path('table/', TableListView.as_view(), name='table-list'),
    path('table/<int:pk>/', TableDetailApiView.as_view(), name='table-detail'),
    path('table/update/<int:pk>/', TableUpdateAPIView.as_view(), name='table-update'),
    path('table/delete/<int:pk>/', TableDeleteApiView.as_view(), name='table-delete'),
    path('reservations/create/', ReservationCreateAPIView.as_view(), name='reservation-create'),
    path('reservations/', RestaurantReservationsAPIView.as_view(), name='restaurant-reservations'),
    path('update-table-status/', TableReservationStatusUpdateView.as_view(), name='update-table-status'),
    path('items/<int:pk>/', ItemDetailAPIView.as_view(), name='item-detail'),
    path('reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation_detail'),
    path('reservations/update/<int:pk>/', ReservationUpdateAPIView.as_view(), name='reservation-update'),
    path('reservation-stats/', ReservationStatsView.as_view(), name='reservation_stats'),
    path('table-reservations/', TableReservationsView.as_view(), name='table_reservations'),
    path("create/order/", OrderCreateAPIView.as_view(), name="order-create"),
    path("order/update/<int:pk>/", OrderUpdateAPIView.as_view(), name="order-update"),
    path("my-orders/", RestaurantOrdersView.as_view(), name="restaurant-orders"),
    path('orders/<int:pk>/', RestaurantSingleOrderView.as_view(), name='restaurant-single-order'),
    path("customers/summary/", CustomerSummaryAPIView.as_view(), name="customer-summary"),
    path("orders/by-phone/", CustomerOrdersByPhoneAPIView.as_view(), name="customer-orders-by-phone"),
    path("callbacks/", PendingCallbacksView.as_view(), name="pending-callbacks"),
    path("callbacks/<int:id>/", PendingCallbacksView.as_view(), name="update-callback-status"),
    path('user-calls/', UserCallInformationAPIView.as_view(), name='user_calls'),
    path('user-call/<int:call_id>/', UserSingleCallInformationAPIView.as_view(), name='user-single-call'),
    path('user-call/callback/<int:call_id>/', UpdateCallCallbackAPIView.as_view(), name='update-call-callback'),
    path('assistance/update-voice/', UpdateVoiceIdAPIView.as_view(), name='update-voice-id'),
    path('assistance/update-twilio-creds/', UpdateTwilioCredsAPIView.as_view(), name='update-twilio-creds'),
    path('stats/', RestaurantStatsAPIView.as_view(), name='restaurant-stats'),
    path('restaurant/monthly-stats/', RestaurantMonthlyStatsAPIView.as_view(), name='restaurant-monthly-stats'),
    path('restaurant/order-stats/', RestaurantOrderStatsAPIView.as_view(), name='restaurant_order_stats'),
    path('create-support/', CreateSupportView.as_view(), name='create_support'),
    path('areas/', AreaManagementListCreateView.as_view(), name='area-list-create'),
    path('areas/<int:pk>/', AreaManagementDetailView.as_view(), name='area-detail'),
    path('my/assistant/', GetRestaurantAssistantAPIView.as_view(), name='my-assistant'),
    path('open-close-times/', OpenAndCloseTimeAPIView.as_view(), name='open-close-times'),
    path('open-close-times/<int:pk>/', OpenAndCloseTimeDetailAPIView.as_view(), name='open-close-time-detail'),
    path('', include(router.urls)),
]

