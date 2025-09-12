from django.shortcuts import render
import stripe
from django.conf import settings
from .serializers import PackageSerializer
from .models import Package
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.decorators import method_decorator
from rest_framework import viewsets,permissions,status,generics
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.translations import translate_text
from rest_framework.response import Response

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