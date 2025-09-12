from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import UserRestaurantDetailView,UpdateRestaurantInfo
from items.views import ItemCreateAPIView,ItemListAPIView,ItemDetailAPIView,ItemUpdateAPIView,ItemDeleteAPIView,RestaurantCategoriesAPIView,MenuExtractorView
from table.views import TableCreateView,TableListView,TableDetailApiView,TableUpdateAPIView,TableDeleteApiView,ReservationCreateAPIView,RestaurantReservationsAPIView,TableReservationStatusUpdateView,ReservationDetailView,ReservationUpdateAPIView,ReservationStatsView,TableReservationsView
from order.views import OrderCreateAPIView,OrderUpdateAPIView,RestaurantOrdersView,CustomerOrdersByPhoneAPIView
from customerService.views import CustomerSummaryAPIView

router = DefaultRouter()



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
    path("customers/summary/", CustomerSummaryAPIView.as_view(), name="customer-summary"),
    path("orders/by-phone/", CustomerOrdersByPhoneAPIView.as_view(), name="customer-orders-by-phone"),
    path('', include(router.urls)),
]

