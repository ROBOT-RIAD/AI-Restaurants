from django.shortcuts import render
import stripe
from django.conf import settings
from .serializers import PackageSerializer
from .models import Package,Subscription,StripeEventLog
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.decorators import method_decorator
from rest_framework import viewsets,permissions,status,generics
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.translations import translate_text
from rest_framework.response import Response
from rest_framework.views import APIView
from subscription.models import Subscription
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from accounts.models import User
from restaurants.models import Restaurant

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.



@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Packages'], manual_parameters=[openapi.Parameter('lean', openapi.IN_QUERY, description="Language code for translation (default is 'en').", type=openapi.TYPE_STRING, default='EN')]))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Packages'], manual_parameters=[openapi.Parameter('lean', openapi.IN_QUERY, description="Language code for translation (default is 'en').", type=openapi.TYPE_STRING, default='EN')]))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Packages'], manual_parameters=[openapi.Parameter('lean', openapi.IN_QUERY, description="Language code for translation (default is 'en').", type=openapi.TYPE_STRING, default='EN')]))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Packages']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Packages'], manual_parameters=[openapi.Parameter('lean', openapi.IN_QUERY, description="Language code for translation (default is 'en').", type=openapi.TYPE_STRING, default='EN')]))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Packages']))
class PackageViewSet(viewsets.ModelViewSet):

    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        data = serializer.validated_data
        lean = self.request.query_params.get('lean')

        name = data['name']
        description = data.get('description')

        if lean != 'EN':
            name = translate_text(name, 'EN')
            print(name)
            description = translate_text(description, 'EN')

        # Create Stripe Product
        stripe_product = stripe.Product.create(
            name=name,
            description=description,
            images=[]
        )

        # Create Stripe Price
        recurring_config = {
            "interval": data['billing_interval'],
            "interval_count": data.get('interval_count', 1)
        } if data['recurring'] else None

        price = stripe.Price.create(
            product=stripe_product.id,
            unit_amount=int(data['amount'] * 100),
            currency='usd',
            recurring=recurring_config
        )

        # Save the data, including Stripe IDs
        instance = serializer.save(
                product_id=stripe_product.id,
                price_id=price.id,
                name=name,
                description=description,
            )
        if lean != 'EN':
            instance.name = translate_text(instance.name, lean)
            instance.description = translate_text(instance.description, lean)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    


    def perform_update(self, serializer):
        
        instance = serializer.instance
        data = serializer.validated_data
        lean = self.request.query_params.get('lean')

        name = data.get('name', instance.name)
        description = data.get('description', instance.description)

        # Translate the name and description if 'lean' is not 'EN'
        if lean != 'EN':
            name = translate_text(name, 'EN')
            print(name)
            description = translate_text(description, 'EN')

        print("jdjjdjdj",description,name)

        # Update Stripe Product if necessary
        if instance.product_id:
            try:
                stripe.Product.modify(
                    instance.product_id,
                    name=name,
                    description=description
                )
            except Exception as e:
                print(f"Stripe product update error: {e}")

        amount = data.get('amount', instance.amount)
        billing_interval = data.get('billing_interval', instance.billing_interval)
        interval_count = data.get('interval_count', instance.interval_count)
        recurring = data.get('recurring', instance.recurring)

        # Check if price needs to be updated
        price_needs_update = (
            amount != instance.amount or
            billing_interval != instance.billing_interval or
            interval_count != instance.interval_count or
            recurring != instance.recurring
        )

        if price_needs_update:
            recurring_config = {
                "interval": billing_interval,
                "interval_count": interval_count
            } if recurring else None

            try:
                new_price = stripe.Price.create(
                    product=instance.product_id,
                    unit_amount=int(amount * 100),
                    currency='usd',
                    recurring=recurring_config
                )
                serializer.save(price_id=new_price.id)
                return
            except Exception as e:
                print(f"Stripe price create error: {e}")

        # Otherwise just save updated fields
        instance = serializer.save(
            name=name,
            description=description
        )

        if lean != 'EN':
            instance.name = translate_text(instance.name, lean)
            instance.description = translate_text(instance.description, lean)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)



    def retrieve(self, request, *args, **kwargs):
        # Retrieve the package and check for translation
        instance = self.get_object()
        lean = request.query_params.get('lean')

        if lean != 'EN':
            instance.name = translate_text(instance.name, lean)
            instance.description = translate_text(instance.description, lean)

        # Serialize the instance
        serializer = self.get_serializer(instance)
        return Response(serializer.data)



    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.product_id:
            try:
                stripe.Product.modify(instance.product_id, active=False)
            except Exception as e:
                print(f"Stripe product deactivate error: {e}")

        self.perform_destroy(instance)
        return Response({'message': "Delete success"}, status=status.HTTP_200_OK)



    def perform_destroy(self, instance):
        instance.delete()

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by('id')
        lean = request.query_params.get('lean')

        # Translate name/description if lean is not EN
        if lean and lean != 'EN':
            for package in queryset:
                package.name = translate_text(package.name, lean)
                package.description = translate_text(package.description, lean)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)




@method_decorator(name="get",decorator=swagger_auto_schema(
manual_parameters=[
            openapi.Parameter(
                'lean',
                openapi.IN_QUERY,
                description="Language code for translation (default is 'EN').",
                type=openapi.TYPE_STRING,
                default='EN'
            )
        ]
    )
)
class PublicPackageListView(generics.ListAPIView):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        lean = (request.query_params.get('lean') or 'EN').upper()
        print(f"Requested translation language: {lean}")

        if lean != 'EN':
            for pkg in response.data['results']:
                if isinstance(pkg, dict): 
                    pkg['name'] = translate_text(pkg['name'], lean)
                    pkg['description'] = translate_text(pkg['description'], lean)
                else:
                    print(f"Unexpected data structure: {pkg}")

        return response
    



class CreateCheckoutSessionView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        tags=["subscriptions"],
        operation_summary="Create Stripe Checkout Session",
        operation_description="Creates a Stripe Checkout Session for a subscription using the provided Stripe `price_id`.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['price_id'],
            properties={
                'price_id': openapi.Schema(type=openapi.TYPE_STRING, description="Stripe Price ID"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Checkout session created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'url': openapi.Schema(type=openapi.TYPE_STRING, description='Stripe checkout URL'),
                    }
                )
            ),
            400: openapi.Response(description="Bad request or error"),
        }
    )

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            price_id = request.data.get("price_id")
            if not price_id:
                return Response({'error': 'price_id is required'}, status=400)
            

            active_subscription = Subscription.objects.filter(
            user=user,
            is_active=True,
            current_period_end__gt=timezone.now()
            ).first()

            if active_subscription:
                return Response({
                    'error': 'You already have an active subscription. Please cancel it before subscribing to a new package.'
                }, status=400)

            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='http://127.0.0.1:8000/?success=success',
                cancel_url='http://127.0.0.1:8000/?cancel=cancel',
            )

            return Response({'url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        




@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["subscriptions"],)
    
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        # Step 1: Verify webhook
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except Exception as e:
            return JsonResponse({'error': f'Invalid signature: {str(e)}'}, status=400)

        event_id = event['id']
        event_type = event['type']
        data = event['data']['object']

        # Step 2: Prevent duplicate handling
        if StripeEventLog.objects.filter(event_id=event_id).exists():
            return HttpResponse(status=200)

        # Step 3: Log the event
        StripeEventLog.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=event
        )

        # Step 4: Handle event types
        try:
            with transaction.atomic():
                if event_type == 'checkout.session.completed':
                    session = data
                    customer_email = session.get('customer_email')
                    subscription_id = session.get('subscription')

                    user = User.objects.filter(email=customer_email).first()
                    if not user:
                        raise Exception("User not found.")

                    stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=['items'])
                    item = stripe_sub['items']['data'][0] if stripe_sub['items']['data'] else None
                    print("------------------------------------------------------->",item)
                    price = item.get('price') if item else None

                    product_id = price.get('product') if price else None
                    product = stripe.Product.retrieve(product_id) if product_id else None
                    product_name = product.get('name') if product else None
                    product_description = product.get('description') if product else None
            
                    current_period_end = stripe_sub.get('current_period_end') or (
                        item.get('current_period_end') if item else None
                    )
                    if current_period_end:
                        current_period_end = datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc)

                    interval = item.get('plan', {}).get('interval', 'unknown') if item else 'unknown'
                    interval_count = item.get('plan', {}).get('interval_count', 0) if item else 0
                    package_name = f"{product_name}"
                    billing_interval_count = f"{interval_count} {interval}"
                    unit_amount = price.get('unit_amount') / 100 if price and price.get('unit_amount') else None

                    Subscription.objects.create(
                        user=user,
                        stripe_customer_id=stripe_sub['customer'],
                        stripe_subscription_id=stripe_sub['id'],
                        package_name=package_name,
                        billing_interval_count=billing_interval_count,
                        price_id=item['price']['id'] if item else None,
                        price=unit_amount,
                        status=stripe_sub['status'],
                        start_date=timezone.now(),
                        current_period_end=current_period_end,
                        cancel_at_period_end=stripe_sub.get('cancel_at_period_end', False),
                        latest_invoice=stripe_sub.get('latest_invoice'),
                        is_active=True
                    )
                    
                    restaurant = Restaurant.objects.filter(owner=user).first()
                    packagedata = Package.objects.filter(product_id=product_id).first()

                    if restaurant and packagedata:
                        restaurant.total_vapi_minutes = (restaurant.total_vapi_minutes or 0) + (packagedata.vapi_minutes or 0)
                        restaurant.save()

                elif event_type == 'customer.subscription.deleted':
                    sub_id = data['id']
                    sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
                    if sub:
                        sub.is_active = False
                        sub.status = "canceled"
                        sub.end_date = timezone.now()
                        sub.save()

                elif event_type == 'customer.subscription.updated':
                    sub_id = data['id']
                    sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
                    if sub:
                        current_period_end = data.get('current_period_end')
                        if current_period_end:
                            sub.current_period_end = datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc)

                        sub.status = data.get('status', sub.status)
                        sub.cancel_at_period_end = data.get('cancel_at_period_end', sub.cancel_at_period_end)
                        sub.latest_invoice = data.get('latest_invoice', sub.latest_invoice)
                        sub.updated_at = timezone.now()
                        sub.save()

        except Exception as e:
            print(f"Webhook processing error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

        return HttpResponse(status=200)
    



class CancelSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["subscriptions"],
        operation_summary="Cancel active subscription",
        operation_description="Cancels the current active subscription for the logged-in user. This cancels it in Stripe and updates the local database.",
        responses={
            200: openapi.Response(description="Subscription cancelled successfully"),
            400: openapi.Response(description="No active subscription found"),
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user

        # Step 1: Find active subscription
        active_sub = Subscription.objects.filter(
            user=user,
            is_active=True,
            current_period_end__gt=timezone.now()
        ).first()

        if not active_sub:
            return Response({'error': 'No active subscription found.'}, status=400)

        try:
            # Step 2: Cancel subscription in Stripe (at period end)
            stripe.Subscription.modify(
                active_sub.stripe_subscription_id,
                cancel_at_period_end=True
            )

            # Step 3: Update local DB
            active_sub.cancel_at_period_end = True
            active_sub.is_active = False
            active_sub.updated_at = timezone.now()
            active_sub.save()

            return Response({'message': 'Subscription will be cancelled at the end of the billing period.'}, status=200)

        except Exception as e:
            return Response({'error': str(e)}, status=400)
        



class SubscriptionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["subscriptions"],
        operation_summary="Get current subscription status",
        operation_description="Returns the status and details of the user's current active subscription.",
        responses={
            200: openapi.Response(
                description="Subscription status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'package_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'current_period_end': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                        'cancel_at_period_end': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            ),
            404: openapi.Response(description="No active subscription found"),
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user

        subscription = Subscription.objects.filter(
            user=user,
            is_active=True,
            current_period_end__gt=timezone.now()
        ).first()

        if not subscription:
            return Response({'detail': 'No active subscription found.'}, status=404)

        return Response({
            'package_name': subscription.package_name,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
        })





