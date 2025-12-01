from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from restaurants.models import Restaurant
from .serializers import TableSerializer,ReservationSerializer
from accounts.translations import translate_text
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from restaurants.models import Restaurant
from .models import Table,Reservation
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils.timezone import now
from customer.models import Customer
# Create your views here.
from django.utils import timezone
from pytz import timezone as pytz_timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import format_html
from django.db.models import Sum
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils.timezone import localtime
from .signals import send_reservation_confirmation_email_manual





class TableCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Create a new Table for the logged-in owner's restaurant.",
        request_body=TableSerializer,
        responses={status.HTTP_201_CREATED: TableSerializer},
        tags=['table'],
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
    def post(self, request, *args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean') 
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        table_name = request.data.get('table_name')
        total_set = request.data.get('total_set')
        if lean != 'EN':
                table_name = translate_text(table_name, 'EN')

        table_data ={
            "table_name": table_name,
            "total_set": total_set,           
        }

        serializer = TableSerializer(data=table_data)
        if serializer.is_valid():
            table = serializer.save(restaurant=restaurant)  # ✅ Force restaurant assignment
            response_data = TableSerializer(table).data

            if lean != 'EN':
                response_data['table_name'] = translate_text(table.table_name, lean)

            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TableListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all items of the logged-in owner's restaurant. Supports search and filter.",
        manual_parameters=[
            openapi.Parameter(
                'table_name',
                openapi.IN_QUERY,
                description="Search table by name",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
            openapi.Parameter(
            'date', 
            openapi.IN_QUERY, 
            description="Filter reservations by reservation date (format: YYYY-MM-DD).", 
            type=openapi.TYPE_STRING
        ),
        ],
        responses={200: TableSerializer(many=True)},
        tags=['table'],
    )
    def get(self , request ,*args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')
        table_name = request.query_params.get('table_name')

        date_str = request.query_params.get("date")
        if date_str:
            try:
                today = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Please use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            today = datetime.today().date()


        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        restaurant_timezone = pytz_timezone('Europe/Berlin')
        tables = Table.objects.filter(restaurant=restaurant)
        current_time = timezone.now().astimezone(restaurant_timezone)

        if table_name:
            if lean != 'EN':
                table_name = translate_text(table_name, 'EN')
            tables = tables.filter(table_name__icontains=table_name)

        
        for table in tables:
            has_reservation = Reservation.objects.filter(
                table=table,
                date=today,
                status__in=['reserved', 'walk-in']
            ).exists()

            is_reserved = False
            if has_reservation:
                reservations = Reservation.objects.filter(
                    table=table,
                    date=today,
                    status__in=['reserved', 'walk-in']
                )
                for reservation in reservations:
                    from_datetime = timezone.make_aware(
                        datetime.combine(today, reservation.from_time), 
                        timezone=restaurant_timezone
                    )
                    to_datetime = timezone.make_aware(
                        datetime.combine(today, reservation.to_time), 
                        timezone=restaurant_timezone
                    )

                    if from_datetime.time() == datetime.strptime('00:00:00', "%H:%M:%S").time() and to_datetime.time() == datetime.strptime('23:59:59', "%H:%M:%S").time():
                        is_reserved = True
                        break

                    time_before_1_hour = from_datetime - timedelta(hours=1)
                    time_after_10_min = to_datetime + timedelta(minutes=10)

                    if time_before_1_hour <= current_time <= time_after_10_min:
                        is_reserved = True
                        break 
            new_status = 'reserved' if is_reserved else 'available'
            if table.reservation_status != new_status:
                table.reservation_status = new_status
                table.save()
                print(f"Table {table.table_name} status updated to '{new_status}'.")

        serializer = TableSerializer(tables, many=True)
        data = serializer.data

        if lean != 'EN':
            for table in data:
                if table.get('table_name'):
                    table['table_name'] = translate_text(table['table_name'], lean)

        return Response(data)



class TableDetailApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a single item of the logged-in owner's restaurant by ID.",
        responses={
            200: TableSerializer,
            404: "Not Found"
        },
        tags=['table'],
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
    def get(self , request , pk ,*args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')

        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            table = Table.objects.get(pk=pk, restaurant=restaurant)
        except Table.DoesNotExist:
            return Response(
                {"error": "Table not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TableSerializer(table)
        data = serializer.data

        if lean != 'EN':
            if data.get('table_name'):
                data['table_name'] = translate_text(data['table_name'], lean)

        return Response(data)



class TableUpdateAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_description="Update a single table of the logged-in owner's restaurant by ID.",
        request_body=TableSerializer,
        responses={
            200: TableSerializer,
            404: "Not Found"
        },
        tags=['table'],
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
    def put(self, request, pk, *args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')

        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            table = Table.objects.get(pk=pk, restaurant=restaurant)
        except Table.DoesNotExist:
            return Response(
                {"error": "Table not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        table_name = request.data.get('table_name', table.table_name)
        total_set = request.data.get('total_set', table.total_set)
        status = request.data.get('status', table.status)
        reservation_status = request.data.get('reservation_status', table.reservation_status)

        if lean != 'EN':
            if table_name:
                table_name = translate_text(table_name, "EN")

        table_data ={
            'table_name': table_name,
            'total_set': total_set,
            'status': status,
            'reservation_status': reservation_status
        }

        serializer = TableSerializer(table, data=table_data)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data

            if lean != 'EN':
                if data.get('table_name'):
                    data['table_name'] = translate_text(data['table_name'], lean)

            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TableDeleteApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Delete a table belonging to the logged-in owner's restaurant.",
        responses={
            200: "table deleted successfully",
            404: "table not found",
            400: "No restaurant assigned",
            401: "Unauthorized",
        },
        tags=['table'],
    )
    def delete(self, request, pk, *args, **kwargs):
        user = request.user
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            table = Table.objects.get(pk=pk, restaurant=restaurant)
        except Table.DoesNotExist:
            return Response(
                {"error": "Table not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        table.delete()
        return Response({"message": "Table deleted successfully."}, status=status.HTTP_200_OK)



class ReservationCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Create a new reservations for the logged-in owner's restaurant.",
        request_body=ReservationSerializer,
        responses={status.HTTP_201_CREATED: ReservationSerializer},
        tags=['reservations'],
    )  
    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        
        customer_name = data.get('customer_name')
        phone_number = data.get('phone_number')
        email = data.get('email')
        address = data.get('address')
        table_id = data.get('table')

        if not phone_number:
            raise ValidationError("Phone number is required for customer.")

        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not table_id:
            raise ValidationError("Table is required.")
        try:
            table = Table.objects.get(id=table_id , restaurant=restaurant)
        except Table.DoesNotExist:
            raise ValidationError("Invalid table ID provided.")
        
        date = request.data.get('date')
        from_time = request.data.get('from_time')
        to_time = request.data.get('to_time')

        date = datetime.strptime(date, '%Y-%m-%d').date()

        from_time = datetime.strptime(f"{date} {from_time}", '%Y-%m-%d %H:%M:%S')
        to_time = datetime.strptime(f"{date} {to_time}", '%Y-%m-%d %H:%M:%S')

        conflicting_reservations = Reservation.objects.filter(
            table=table,
            date=date
        )

        for reservation in conflicting_reservations:
            # Convert reservation times to datetime objects using the same date
            reservation_from_time = datetime.combine(date, reservation.from_time)
            reservation_to_time = datetime.combine(date, reservation.to_time)

            # Check for conflicts (1 hour before and 10 minutes after)
            if (from_time < reservation_to_time + timedelta(minutes=10)) and (to_time > reservation_from_time - timedelta(minutes=60)):
                raise ValidationError(f"This table is already reserved during the selected time slot. Please choose a different time.")
            
        

        customer, created = Customer.objects.get_or_create(phone=phone_number)
        
        customer.customer_name = customer_name or customer.customer_name
        customer.email = email or customer.email
        customer.address = address or customer.address
        customer.save()
        
        serializer_data = {
            "customer": customer.id,
            "guest_no": data.get("guest_no"),
            "date": date,
            "from_time": request.data.get('from_time'),
            "to_time": request.data.get('to_time'),
            "table": table.id,
            "allergy": data.get("allergy", ""),
            "status": data.get("status", "reserved"),
        }

        serializer = ReservationSerializer(data=serializer_data)

        if serializer.is_valid():
            verified_status = True
            if phone_number:
                has_unfinished = Reservation.objects.filter(
                    customer__phone=phone_number
                ).exclude(status='finished').exists()
                if has_unfinished:
                    verified_status = False
            reservation = serializer.save(verified=verified_status,customer=customer)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "reservation_created",
                    "reservation": ReservationSerializer(reservation).data
                }
            )    
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class RestaurantReservationsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated] 

    @swagger_auto_schema(
        operation_description="Retrieve all reservations of the logged-in owner's restaurant. Supports search and filter.",
        responses={200: ReservationSerializer(many=True)},
        tags=['reservations'],
        manual_parameters=[
        openapi.Parameter(
            'customer_name', 
            openapi.IN_QUERY, 
            description="Filter reservations by customer's name.", 
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'phone_number', 
            openapi.IN_QUERY, 
            description="Filter reservations by customer's phone number.", 
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'table_name', 
            openapi.IN_QUERY, 
            description="Filter reservations by table name.", 
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'email', 
            openapi.IN_QUERY, 
            description="Filter reservations by customer's email address.", 
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'date', 
            openapi.IN_QUERY, 
            description="Filter reservations by reservation date (format: YYYY-MM-DD).", 
            type=openapi.TYPE_STRING
        ),
    ]
    )
    def get(self, request, *args, **kwargs):
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer_name = request.GET.get('customer_name', '')
        phone_number = request.GET.get('phone_number', '')
        table_name = request.GET.get('table_name', '')
        email = request.GET.get('email', '')
        reservation_date = request.GET.get('date', None)

        reservations = Reservation.objects.filter(table__restaurant=restaurant)

        if customer_name:
            reservations = reservations.filter(customer__customer_name__icontains=customer_name)
        if phone_number:
            reservations = reservations.filter(customer__phone__icontains=phone_number)
        if table_name:
            reservations = reservations.filter(table__table_name__icontains=table_name)
        if email:
            reservations = reservations.filter(customer__email__icontains=email)
        if reservation_date:
            reservations = reservations.filter(date=reservation_date)

        serializer = ReservationSerializer(reservations, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)




class TableReservationStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    table_status_param = openapi.Parameter(
        'date', openapi.IN_QUERY, description="Date to filter reservations. Format: YYYY-MM-DD", type=openapi.TYPE_STRING
    )
    @swagger_auto_schema(
        operation_description="Fetch and update reservation status for all tables for the logged-in user's restaurant based on reservations for the specified or current date.",
        manual_parameters=[table_status_param],
        responses={
            200: TableSerializer(many=True),
            400: openapi.Response('Bad Request', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'error': openapi.Schema(type=openapi.TYPE_STRING)
            }))
        },
        tags=['Table Reservation']
    )
    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                today = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Please use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            today = datetime.today().date()
        
        user = request.user
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        restaurant_timezone = pytz_timezone('Europe/Berlin')
        tables = Table.objects.filter(restaurant=restaurant)
        current_time = timezone.now().astimezone(restaurant_timezone)

        for table in tables:
            has_reservation = Reservation.objects.filter(
                table=table,
                date=today,
                status__in=['reserved', 'walk-in']
            ).exists()

            is_reserved = False
            if has_reservation:
                reservations = Reservation.objects.filter(
                    table=table,
                    date=today,
                    status__in=['reserved', 'walk-in']
                )
                for reservation in reservations:
                    from_datetime = timezone.make_aware(
                        datetime.combine(today, reservation.from_time), 
                        timezone=restaurant_timezone
                    )
                    to_datetime = timezone.make_aware(
                        datetime.combine(today, reservation.to_time), 
                        timezone=restaurant_timezone
                    )

                    if from_datetime.time() == datetime.strptime('00:00:00', "%H:%M:%S").time() and to_datetime.time() == datetime.strptime('23:59:59', "%H:%M:%S").time():
                        is_reserved = True
                        break

                    time_before_1_hour = from_datetime - timedelta(hours=1)
                    time_after_10_min = to_datetime + timedelta(minutes=10)

                    if time_before_1_hour <= current_time <= time_after_10_min:
                        is_reserved = True
                        break 
            new_status = 'reserved' if is_reserved else 'available'
            if table.reservation_status != new_status:
                table.reservation_status = new_status
                table.save()
                print(f"Table {table.table_name} status updated to '{new_status}'.")

        serializer = TableSerializer(tables, many=True)
        return Response(serializer.data)




class ReservationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Fetch reservation details for a specific reservation ID.",
        responses={
            200: ReservationSerializer(),
            404: openapi.Response('Not Found', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'error': openapi.Schema(type=openapi.TYPE_STRING)
            }))
        },
        tags=['reservations']
    )
    def get(self, request, pk, *args, **kwargs):
        restaurant = Restaurant.objects.filter(owner=request.user).first()

        if not restaurant:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reservation = Reservation.objects.get(id=pk, table__restaurant=restaurant)
        except Reservation.DoesNotExist:
            return Response(
                {"error": f"Reservation with ID {pk} not found for your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ReservationSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)




class ReservationUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


    @swagger_auto_schema(
        operation_description="Partially update a reservation belonging to the logged-in owner's restaurant.",
        request_body=ReservationSerializer,
        responses={
            200: openapi.Response("Reservation updated successfully", ReservationSerializer),
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
        tags=['reservations'],
        manual_parameters=[
            openapi.Parameter(
            'date', 
            openapi.IN_QUERY, 
            description="Filter reservations by reservation date (format: YYYY-MM-DD).", 
            type=openapi.TYPE_STRING
        ),
        ]
    )

    def patch(self, request, pk, *args, **kwargs):
        restaurant = Restaurant.objects.filter(owner=request.user).first()

        if not restaurant:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reservation = Reservation.objects.get(id=pk, table__restaurant=restaurant)
        except Reservation.DoesNotExist:
            return Response(
                {"error": f"Reservation with ID {pk} not found for your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReservationSerializer(reservation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "reservation_updated",
                    "reservation": serializer.data
                }
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ReservationStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    date_param = openapi.Parameter(
        'date',
        openapi.IN_QUERY,
        description="Filter reservations by date. Format: YYYY-MM-DD",
        type=openapi.TYPE_STRING,
        required=True
    )

    @swagger_auto_schema(
        operation_description="Get reservation statistics (total guests, reservations, and walk-ins) for the authenticated user's restaurant on a given date.",
        manual_parameters=[date_param],
        tags=['reservations'],
        responses={
            200: openapi.Response(
                description="Reservation statistics",
                examples={
                    "application/json": {
                        "total_guests": 15,
                        "total_reservations": 5,
                        "total_walk_in": 2
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {"error": "Date parameter is required."}
                }
            ),
            404: openapi.Response(
                description="Not Found",
                examples={
                    "application/json": {"error": "No reservations found for this date."}
                }
            ),
        }
    )
    
    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get('date')
        
        if not date_str:
            return Response(
                {"error": "Date parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        restaurant = Restaurant.objects.get(owner=request.user)

        if not restaurant:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservations = Reservation.objects.filter(
            table__restaurant=restaurant, 
            date=date
        )
        
        if not reservations.exists():
            return Response(
                {"error": "No reservations found for this date."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calculate total number of guests (sum of guest_no)
        total_guests = reservations.aggregate(Sum('guest_no'))['guest_no__sum'] or 0

        # Count total reservations
        total_reservations = reservations.count()

        # Count walk-in customers (reservations with status 'walk-in')
        total_walk_in = reservations.filter(status='walk-in').count()

        # Prepare the response data
        data = {
            "total_guests": total_guests,
            "total_reservations": total_reservations,
            "total_walk_in": total_walk_in,
        }

        return Response(data, status=status.HTTP_200_OK)
    


class TableReservationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Fetch all tables and their reservations for a specific date for the restaurant owned by the logged-in user.",
        manual_parameters=[
            openapi.Parameter(
            'date', 
            openapi.IN_QUERY, 
            description="Filter reservations by reservation date (format: YYYY-MM-DD).", 
            type=openapi.TYPE_STRING
        ),
        ],
        responses={
            200: openapi.Response(
                description="List of tables with their reservations for the specified date.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'table_name': openapi.Schema(type=openapi.TYPE_STRING, description="The name of the table"),
                            'reservations': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'guest_no': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'from_time': openapi.Schema(type=openapi.TYPE_STRING),
                                        'to_time': openapi.Schema(type=openapi.TYPE_STRING),
                                        'status': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                )
                            )
                        }
                    )
                )
            ),
            400: openapi.Response(description="Bad Request (e.g., invalid date format)"),
            404: openapi.Response(description="Not Found (e.g., no tables or reservations found)"),
        },
       
        tags=['reservations'],
    )
    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get('date')

        if not date_str:
            return Response(
                {"error": "Date parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the restaurant of the logged-in user
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all tables for the restaurant, and fetch reservations for the given date
        tables = Table.objects.filter(restaurant=restaurant)
        tables_with_reservations = []

        for table in tables:
            # Get reservations for the table on the given date
            reservations = Reservation.objects.filter(table=table, date=date)
            reservations_data = [
                {
                    "customer_name": reservation.customer.customer_name if reservation.customer else "Unknown",
                    "guest_no": reservation.guest_no,
                    "from_time": reservation.from_time.strftime('%H:%M:%S'),
                    "to_time": reservation.to_time.strftime('%H:%M:%S'),
                    "status": reservation.status
                }
                for reservation in reservations
            ]

            tables_with_reservations.append({
                "table_name": table.table_name,
                "reservations": reservations_data
            })

        if not tables_with_reservations:
            return Response(
                {"error": "No reservations found for this date."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(tables_with_reservations, status=status.HTTP_200_OK)




class PublicReservationCreateAPIView(APIView):
    permission_classes = [AllowAny]
    # parser_classes = [MultiPartParser, FormParser]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_description="Create a new reservations for the logged-in owner's restaurant.",
        request_body=ReservationSerializer,
        responses={status.HTTP_201_CREATED: ReservationSerializer},
        tags=['Webhook'],
    )  
    def post(self, request, *args, **kwargs):
        data = request.data


        table_id = data.get('table')
        customer_name = data.get('customer_name')
        phone_number = data.get('phone_number')
        email = data.get('email')
        address = data.get('address')

        if not table_id:
            raise ValidationError("Table is required.")
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            raise ValidationError("Invalid table ID provided.")
        
        restaurant = table.restaurant
        
        date = request.data.get('date')
        from_time = request.data.get('from_time')
        to_time = request.data.get('to_time')

        date = datetime.strptime(date, '%Y-%m-%d').date()

        from_time = datetime.strptime(f"{date} {from_time}", '%Y-%m-%d %H:%M:%S')
        to_time = datetime.strptime(f"{date} {to_time}", '%Y-%m-%d %H:%M:%S')

        conflicting_reservations = Reservation.objects.filter(
            table=table,
            date=date
        )

        for reservation in conflicting_reservations:
            # Convert reservation times to datetime objects using the same date
            reservation_from_time = datetime.combine(date, reservation.from_time)
            reservation_to_time = datetime.combine(date, reservation.to_time)

            # Check for conflicts (1 hour before and 10 minutes after)
            if (from_time < reservation_to_time + timedelta(minutes=10)) and (to_time > reservation_from_time - timedelta(minutes=60)):
                raise ValidationError(f"This table is already reserved during the selected time slot. Please choose a different time.")
            
        

        customer, created = Customer.objects.get_or_create(phone=phone_number)
        
        customer.customer_name = customer_name or customer.customer_name
        customer.email = email or customer.email
        customer.address = address or customer.address
        customer.save()

        serializer_data = {
            "customer": customer.id, 
            "guest_no": data.get("guest_no"),
            "date": date,
            "from_time": request.data.get('from_time'),
            "to_time": request.data.get('to_time'),
            "table": table.id,
            "allergy": data.get("allergy", ""),
            "status": data.get("status", "reserved"),
        }

        serializer = ReservationSerializer(data=serializer_data)
        if serializer.is_valid():
            verified_status = True
            if phone_number:
                has_unfinished = Reservation.objects.filter(
                    customer__phone=phone_number
                ).exclude(status='finished').exists()
                if has_unfinished:
                    verified_status = False
            reservation = serializer.save(verified=verified_status,customer=customer)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "reservation_created",
                    "reservation": ReservationSerializer(reservation).data
                }
            ) 
            return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ReservationAutoVerifyView(APIView):
    """
    Public endpoint: verifies reservation and displays all reservation info.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Auto-verify a reservation by ID (public)",
        operation_description=(
            "When this endpoint is visited (e.g. via email link), "
            "it automatically verifies the reservation (sets `verified=True` if not yet verified) "
            "and returns an HTML confirmation page with full reservation details."
        ),
        tags=["reservations"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Reservation ID (primary key)",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="HTML confirmation page showing reservation info"),
            404: "Reservation not found",
        },
    )
    def get(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        table = reservation.table
        restaurant = table.restaurant
        customer = reservation.customer


        if not reservation.verified:
            reservation.verified = True
            reservation.save(update_fields=["verified", "updated_at"])
            send_reservation_confirmation_email_manual(reservation)

        customer_name = customer.customer_name if customer else "Valued Customer"
        phone_number = customer.phone if customer else "N/A"
        email = customer.email if customer else "N/A"
        address = customer.address if customer else "N/A"

        html = f"""
        <html>
        <head>
            <title>Reservation Confirmation</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f8f9fa;
                    padding: 40px;
                    color: #333;
                }}
                .container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h2 {{
                    text-align: center;
                    color: green;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f1f1f1;
                }}
                .footer {{
                    margin-top: 25px;
                    text-align: center;
                    font-size: 14px;
                    color: gray;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ Thank you, {customer_name}!</h2>
                <p>Your reservation has been successfully verified.</p>

                <h3>Reservation Details</h3>
                <table>
                    <tr><th>Reservation ID</th><td>{reservation.id}</td></tr>
                    <tr><th>Status</th><td>{reservation.status}</td></tr>
                    <tr><th>Guests</th><td>{reservation.guest_no}</td></tr>
                    <tr><th>Date</th><td>{reservation.date}</td></tr>
                    <tr><th>From Time</th><td>{reservation.from_time}</td></tr>
                    <tr><th>To Time</th><td>{reservation.to_time}</td></tr>
                    <tr><th>Table</th><td>{table.table_name}</td></tr>
                    <tr><th>Restaurant</th><td>{restaurant.resturent_name}</td></tr>
                    <tr><th>Phone</th><td>{phone_number}</td></tr>
                    <tr><th>Email</th><td>{email}</td></tr>
                    <tr><th>Address</th><td>{address}</td></tr>
                    <tr><th>Allergy Info</th><td>{reservation.allergy or "None"}</td></tr>
                </table>

                <div class="footer">
                    <p><b>@{restaurant.resturent_name}</b></p>
                    <p><b>{restaurant.phone_number_1 or ''}</b></p>
                    <p>Verified on: {localtime(reservation.updated_at).strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return HttpResponse(html)
    



