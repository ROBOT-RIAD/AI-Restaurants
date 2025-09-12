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
# Create your views here.
from django.utils import timezone
from pytz import timezone as pytz_timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import format_html
from django.db.models import Sum
from rest_framework.permissions import AllowAny





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
        
        restaurant_timezone = pytz_timezone('Asia/Dhaka')
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
        table_id = request.data.get('table') 

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

        serializer = ReservationSerializer(data=request.data)
        if serializer.is_valid():
            reservation = serializer.save()
            customer_email = reservation.email
            customer_name = reservation.customer_name
            customer_phone = reservation.phone_number
            customer_from_time = reservation.from_time.strftime('%I:%M %p')
            customer_to_time = reservation.to_time.strftime('%I:%M %p')
            customer_guest_no = reservation.guest_no

            restaurant_email = restaurant.owner.email 
            restaurant_phone1 = restaurant.phone_number_1  
            restaurant_phone2 = restaurant.twilio_number  
            website = restaurant.website
            restaurant_address = restaurant.address  
            opening_time = restaurant.opening_time.strftime('%H:%M') if restaurant.opening_time else "Not Set"
            closing_time = restaurant.closing_time.strftime('%H:%M') if restaurant.closing_time else "Not Set"
            subject = "Reservation Confirmation"
            message = format_html(
                """
                <h3>Your reservation is confirmed!</h3>
                <p>Thank you for making a reservation with <b>{restaurant_name}</b>.</p>
                <p><b>Reservation Details:</b></p>
                <ul>
                    <li><b>Name:</b> {customer_name}</li>
                    <li><b>Phone:</b> {customer_phone}</li>
                    <li><b>Email:</b> {customer_email}</li>
                    <li><b>Date:</b> {reservation_date}</li>
                    <li><b>Start Time:</b> {customer_from_time}</li>
                    <li><b>End Time:</b> {customer_to_time}</li>
                    <li><b>Guests:</b> {customer_guest_no}</li>
                    <li><b>Table:</b> {table_name}</li>
                </ul>
                <p><b>Restaurant Details:</b></p>
                <ul>
                    <li><b>Email:</b> {restaurant_email}</li>
                    <li><b>Phone:</b> {restaurant_phone1}</li>
                    <li><b>Phone Online:</b> {restaurant_phone2}</li>
                    <li><b>Address:</b> {restaurant_address}</li>
                    <li><b>Website:</b> {website}</li>
                    <li><b>Opening Time:</b> {opening_time}</li>
                    <li><b>Closing Time:</b> {closing_time}</li>
                </ul>
                <p>We look forward to welcoming you!</p>
                <p>For any inquiries, feel free to contact us.</p>
                """,
                restaurant_name=restaurant.resturent_name,
                reservation_date=date,
                from_time=from_time.strftime('%H:%M'),
                to_time=to_time.strftime('%H:%M'),
                table_name=table.table_name,
                restaurant_email=restaurant_email,
                restaurant_phone1=restaurant_phone1,
                restaurant_phone2=restaurant_phone2,
                website=website,
                opening_time=opening_time,
                closing_time=closing_time,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_from_time=customer_from_time,
                customer_to_time=customer_to_time,
                customer_guest_no=customer_guest_no,
                customer_email=customer_email,
                restaurant_address =restaurant_address,
            )
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [customer_email],
                html_message=message
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
            reservations = reservations.filter(Q(customer_name__icontains=customer_name))
        if phone_number:
            reservations = reservations.filter(Q(phone_number__icontains=phone_number))
        if table_name:
            reservations = reservations.filter(Q(table__table_name__icontains=table_name))
        if email:
            reservations = reservations.filter(Q(email__icontains=email))
        
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
        restaurant_timezone = pytz_timezone('Asia/Dhaka')
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
                    "customer_name": reservation.customer_name,
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
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Create a new reservations for the logged-in owner's restaurant.",
        request_body=ReservationSerializer,
        responses={status.HTTP_201_CREATED: ReservationSerializer},
        tags=['Webhook'],
    )  
    def post(self, request, *args, **kwargs):
        table_id = request.data.get('table') 

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

        serializer = ReservationSerializer(data=request.data)
        if serializer.is_valid():
            reservation = serializer.save()
            customer_email = reservation.email
            customer_name = reservation.customer_name
            customer_phone = reservation.phone_number
            customer_from_time = reservation.from_time.strftime('%I:%M %p')
            customer_to_time = reservation.to_time.strftime('%I:%M %p')
            customer_guest_no = reservation.guest_no

            restaurant_email = restaurant.owner.email 
            restaurant_phone1 = restaurant.phone_number_1  
            restaurant_phone2 = restaurant.twilio_number  
            website = restaurant.website
            restaurant_address = restaurant.address  
            opening_time = restaurant.opening_time.strftime('%H:%M') if restaurant.opening_time else "Not Set"
            closing_time = restaurant.closing_time.strftime('%H:%M') if restaurant.closing_time else "Not Set"
            subject = "Reservation Confirmation"
            message = format_html(
                """
                <h3>Your reservation is confirmed!</h3>
                <p>Thank you for making a reservation with <b>{restaurant_name}</b>.</p>
                <p><b>Reservation Details:</b></p>
                <ul>
                    <li><b>Name:</b> {customer_name}</li>
                    <li><b>Phone:</b> {customer_phone}</li>
                    <li><b>Email:</b> {customer_email}</li>
                    <li><b>Date:</b> {reservation_date}</li>
                    <li><b>Start Time:</b> {customer_from_time}</li>
                    <li><b>End Time:</b> {customer_to_time}</li>
                    <li><b>Guests:</b> {customer_guest_no}</li>
                    <li><b>Table:</b> {table_name}</li>
                </ul>
                <p><b>Restaurant Details:</b></p>
                <ul>
                    <li><b>Email:</b> {restaurant_email}</li>
                    <li><b>Phone:</b> {restaurant_phone1}</li>
                    <li><b>Phone Online:</b> {restaurant_phone2}</li>
                    <li><b>Address:</b> {restaurant_address}</li>
                    <li><b>Website:</b> {website}</li>
                    <li><b>Opening Time:</b> {opening_time}</li>
                    <li><b>Closing Time:</b> {closing_time}</li>
                </ul>
                <p>We look forward to welcoming you!</p>
                <p>For any inquiries, feel free to contact us.</p>
                """,
                restaurant_name=restaurant.resturent_name,
                reservation_date=date,
                from_time=from_time.strftime('%H:%M'),
                to_time=to_time.strftime('%H:%M'),
                table_name=table.table_name,
                restaurant_email=restaurant_email,
                restaurant_phone1=restaurant_phone1,
                restaurant_phone2=restaurant_phone2,
                website=website,
                opening_time=opening_time,
                closing_time=closing_time,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_from_time=customer_from_time,
                customer_to_time=customer_to_time,
                customer_guest_no=customer_guest_no,
                customer_email=customer_email,
                restaurant_address =restaurant_address,
            )
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [customer_email],
                html_message=message
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



