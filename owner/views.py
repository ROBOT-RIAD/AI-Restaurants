from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import UserRestaurantSerializerInfo,RestaurantSerializerInfo,RestaurantStatsSerializer
from restaurants.models import Restaurant
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from accounts.translations import translate_text
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsOwnerRole
from AIvapi.update_agent import UpdateAgent
from AIvapi.models import Assistance
from order.models import Order
from table.models import Reservation
from customerService.models import CustomerService
from AIvapi.models import CallInformations , Assistance
from django.db.models import Count, Sum ,F,Q,FloatField
from django.db.models.functions import Cast
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth
from datetime import datetime



class UserRestaurantDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retrieve user restaurant details",
        responses={200: UserRestaurantSerializerInfo},
        tags=['Restaurant'],
        manual_parameters=[
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        lean = request.query_params.get('lean', 'EN').upper()
        user = request.user
        
        user_serializer = UserRestaurantSerializerInfo(user,context ={'request': request})
        
        if lean != 'EN' and user_serializer.data.get('restaurant'):
            restaurant_data = user_serializer.data['restaurant']
            
            if 'resturent_name' in restaurant_data:
                restaurant_data['resturent_name'] = translate_text(restaurant_data['resturent_name'], lean)
            
            if 'address' in restaurant_data:
                restaurant_data['address'] = translate_text(restaurant_data['address'], lean)
        
        return Response(user_serializer.data)
    



class UpdateRestaurantInfo(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    @swagger_auto_schema(
        operation_description="Update the authenticated user's restaurant information.",
        request_body=RestaurantSerializerInfo,
        responses={
            200: RestaurantSerializerInfo,
            400: 'Bad Request - Validation errors',
            404: 'No restaurant found for this user'
        },
        tags=['Restaurant'],
        manual_parameters=[
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
    )
    def patch(self, request, *args, **kwargs):
        lean = request.query_params.get('lean', 'EN').upper()
        user = request.user
        try:
            restaurant = user.restaurants.first()
        except Restaurant.DoesNotExist:
            return Response({"error": "No restaurant found for this user."}, status=status.HTTP_404_NOT_FOUND)
        
        if lean != 'EN':
            resturent_name = request.data.get('resturent_name')
            address = request.data.get('address')

            if resturent_name:
                request.data['resturent_name'] = translate_text(resturent_name, 'EN')
            if address:
                request.data['address'] = translate_text(address, 'EN')
        old_phone_number = restaurant.phone_number_1
        serializer = RestaurantSerializerInfo(
            restaurant, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            data =serializer.data
            new_phone_number = serializer.validated_data.get('phone_number_1')
            if new_phone_number and new_phone_number != old_phone_number:
                try:
                    assistance = restaurant.ai_assistance
                except Assistance.DoesNotExist:
                    pass
                else:
                    agent = UpdateAgent(agent_id=assistance.assistant_id, phone_id=assistance.vapi_phone_number_id)
                    try:
                        agent.update_restaurant_no(updated_fallback=new_phone_number)
                    except Exception as e:
                        print(f"Failed to update restaurant fallback number in VAPI: {e}")
            if lean != 'EN':
                data['resturent_name'] = translate_text(data['resturent_name'], lean)
                data['address'] = translate_text(data['address'], lean)
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class RestaurantMonthlyStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get total orders and reservations grouped by month for a restaurant's assistant.",
        responses={200: 'Success', 404: 'Restaurant not found or no assistance available'},
        tags=["Overview"]
    )
    def get(self, request):

        restaurants = Restaurant.objects.filter(owner=request.user)

        assistance = Assistance.objects.filter(restaurant__in=restaurants).first()

        if not assistance:
            return Response({"error": "No assistance found for this restaurant."}, status=status.HTTP_404_NOT_FOUND)
        


        # Optionally, handle a query parameter for filtering by last X days
        last_x_days = request.query_params.get('days', None)
        if last_x_days:
            days_ago = timezone.now() - timedelta(days=int(last_x_days))
            call_filter = CallInformations.objects.filter(
                assistant_id=assistance.assistant_id,
                call_date_utc__gte=days_ago
            )
        else:
            call_filter = CallInformations.objects.filter(assistant_id=assistance.assistant_id)



        current_year = timezone.now().year



        all_months = [datetime(current_year, month, 1) for month in range(1, 13)]
        all_months_formatted = [month.strftime('%b') for month in all_months]


        # Aggregate data by month for 'order' type
        order_data = call_filter.filter(type='order') \
            .annotate(month=TruncMonth('call_date_utc')) \
            .values('month') \
            .annotate(total_orders=Count('id')) \
            .order_by('month')
        

        # Aggregate data by month for 'reservation' type
        reservation_data = call_filter.filter(type='reservation') \
            .annotate(month=TruncMonth('call_date_utc')) \
            .values('month') \
            .annotate(total_reservations=Count('id')) \
            .order_by('month')

        # Initialize result dictionaries with 0 values
        order_months = {month: 0 for month in all_months_formatted}
        reservation_months = {month: 0 for month in all_months_formatted}

        # Update the order_months with the actual data
        for order in order_data:
            month_str = order['month'].strftime('%b')
            if month_str in order_months:
                order_months[month_str] = order['total_orders']

        # Update the reservation_months with the actual data
        for reservation in reservation_data:
            month_str = reservation['month'].strftime('%b')
            if month_str in reservation_months:
                reservation_months[month_str] = reservation['total_reservations']


        return Response({
            'order': [{month: count} for month, count in order_months.items()],
            'reservation': [{month: count} for month, count in reservation_months.items()]
        })
    



class RestaurantStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    start_date_param = openapi.Parameter(
        'start_date', openapi.IN_QUERY,
        description="Start date for filtering (format: YYYY-MM-DD). Defaults to today if not provided.",
        type=openapi.TYPE_STRING
    )

    end_date_param = openapi.Parameter(
        'end_date', openapi.IN_QUERY,
        description="End date for filtering (format: YYYY-MM-DD). Defaults to today if not provided.",
        type=openapi.TYPE_STRING
    )

    @swagger_auto_schema(
        operation_description="Get detailed statistics for the restaurant filtered by start_date and end_date.",
        responses={200: RestaurantStatsSerializer, 404: "Assistance not found for this restaurant"},
        tags=["Overview"],
        manual_parameters=[start_date_param, end_date_param]
    )
    def get(self, request):
        restaurants = Restaurant.objects.filter(owner=request.user)
        assistance = Assistance.objects.filter(restaurant__in=restaurants).first()

        if not assistance:
            return Response({"error": "No assistance found for this restaurant."}, status=404)

        # --- Date filtering setup ---
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        today = timezone.localdate()

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else today
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else today
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # --- Query Data ---
        orders = Order.objects.filter(
            restaurant__in=restaurants,
            created_at__range=(start_datetime, end_datetime)
        )
        reservations = Reservation.objects.filter(
            table__restaurant__in=restaurants,
            created_at__range=(start_datetime, end_datetime)
        )

        # ===============================
        # 📊 ORDER METRICS
        # ===============================
        total_orders = orders.count()
        total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0

        # Aggregate by phone (customer)
        customer_order_counts = (
            orders.values('phone')
            .annotate(order_count=Count('id'), total_spent=Sum('total_price'))
        )

        # Separate new vs returning customers
        new_customers = [c['phone'] for c in customer_order_counts if c['order_count'] == 1]
        returning_customers = [c['phone'] for c in customer_order_counts if c['order_count'] > 1]

        # Revenue splits
        new_customer_revenue = (
            orders.filter(phone__in=new_customers).aggregate(total=Sum('total_price'))['total'] or 0
        )
        returning_customer_revenue = (
            orders.filter(phone__in=returning_customers).aggregate(total=Sum('total_price'))['total'] or 0
        )

        # Order counts
        number_of_new_customer_orders = orders.filter(phone__in=new_customers).count()
        number_of_returning_customer_orders = orders.filter(phone__in=returning_customers).count()

        # Percentages
        new_customer_order_percentage = (
            (number_of_new_customer_orders / total_orders) * 100 if total_orders > 0 else 0
        )
        returning_customer_order_percentage = (
            (number_of_returning_customer_orders / total_orders) * 100 if total_orders > 0 else 0
        )

        # ===============================
        # 📅 RESERVATION METRICS
        # ===============================
        total_reservations = reservations.count()
        total_reservation_guests = reservations.aggregate(Sum('guest_no'))['guest_no__sum'] or 0

        # Group by phone
        reservation_counts = (
            reservations.values('phone_number')
            .annotate(res_count=Count('id'))
        )

        new_reservation_customers = [r['phone_number'] for r in reservation_counts if r['res_count'] == 1]
        returning_reservation_customers = [r['phone_number'] for r in reservation_counts if r['res_count'] > 1]

        number_of_new_customer_reservations = reservations.filter(phone_number__in=new_reservation_customers).count()
        number_of_returning_customer_reservations = reservations.filter(phone_number__in=returning_reservation_customers).count()

        # Percentages
        new_customer_reservation_percentage = (
            (number_of_new_customer_reservations / total_reservations) * 100 if total_reservations > 0 else 0
        )
        returning_customer_reservation_percentage = (
            (number_of_returning_customer_reservations / total_reservations) * 100 if total_reservations > 0 else 0
        )

        # ===============================
        # 📦 FINAL RESPONSE
        # ===============================
        stats = {
            # --- Orders ---
            "total_orders": total_orders,
            "revenus_from_orders": total_revenue,
            "average_order_value": round(average_order_value, 2),
            "new_customer_order_revenue": new_customer_revenue,
            "returning_customer_order_revenue": returning_customer_revenue,
            "number_of_new_customer_orders": number_of_new_customer_orders,
            "number_of_returning_customer_orders": number_of_returning_customer_orders,
            "new_customer_order_percentage": round(new_customer_order_percentage, 2),
            "returning_customer_order_percentage": round(returning_customer_order_percentage, 2),

            # --- Reservations ---
            "number_of_reservations": total_reservations,
            "number_of_reservation_guests": total_reservation_guests,
            "number_of_new_customer_reservations": number_of_new_customer_reservations,
            "number_of_returning_customer_reservations": number_of_returning_customer_reservations,
            "new_customer_reservation_percentage": round(new_customer_reservation_percentage, 2),
            "returning_customer_reservation_percentage": round(returning_customer_reservation_percentage, 2),
        }

        return Response(stats, status=status.HTTP_200_OK)





