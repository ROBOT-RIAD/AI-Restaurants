from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Item
from restaurants.models import Restaurant
from .serializers import ItemSerializer,MenuFileSerializer
from accounts.translations import translate_text
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from .pdf2menu import extract_from_pdf
from .image2menu import validate_images, jpgs_to_pdf
from .models import Item
import os
import shutil
import tempfile
import json
import traceback
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer




class ItemCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Create a new Item for the logged-in owner's restaurant.",
        request_body=ItemSerializer,
        responses={
            201: openapi.Response("Item created successfully", ItemSerializer),
            400: "Bad Request",
            401: "Unauthorized",
        },
        tags=['Item'],
        # manual_parameters=[
        #     openapi.Parameter(
        #         'lean', 
        #         openapi.IN_QUERY, 
        #         description="Language code for translation (default is 'en').", 
        #         type=openapi.TYPE_STRING,
        #         default='EN'
        #     ),
        # ],
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        # lean = request.query_params.get('lean')  
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        item_name = request.data.get("item_name")
        status_value = request.data.get("status")
        descriptions = request.data.get("descriptions")
        image = request.data.get("image")
        category = request.data.get("category")
        price = request.data.get("price")
        discount = request.data.get("discount")
        preparation_time = request.data.get("preparation_time")

        # if lean != 'EN':
        #         item_name = translate_text(item_name, 'EN')
        #         descriptions = translate_text(descriptions, 'EN')
        #         category = translate_text(category, 'EN')
                

        item_data = {
            "item_name": item_name,
            "status": status_value,
            "descriptions": descriptions,
            "image": image,
            "category": category,
            "price": price,
            "discount": discount,
            "preparation_time": preparation_time,
            "restaurant": restaurant.id
        }

        serializer = ItemSerializer(data=item_data,context={'request':request})
        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            data = serializer.data

            # if lean != 'EN':
            #     data['item_name'] = translate_text(data['item_name'] , lean)
            #     data['descriptions'] = translate_text(data['descriptions'], lean)
            #     data['category'] = translate_text(data['category'], lean)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "item_created",
                    "item": data,
                }
            )
            return Response(data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class ItemListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all items of the logged-in owner's restaurant. Supports search and filter.",
        manual_parameters=[
            openapi.Parameter(
                'item_name',
                openapi.IN_QUERY,
                description="Search items by name",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Filter items by category",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
        responses={200: ItemSerializer(many=True)},
        tags=['Item'],
        
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        lean = request.query_params.get('lean')
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        items = Item.objects.filter(restaurant=restaurant)

        item_name = request.query_params.get('item_name')
        category = request.query_params.get('category')

        if lean != 'EN':
            if item_name:
                item_name = translate_text(item_name, 'EN')
            if category:
                category = translate_text(category, 'EN')

        if item_name:
            items = items.filter(item_name__icontains=item_name)

        if category:
            items = items.filter(category__iexact=category)

        serializer = ItemSerializer(items, many=True,context = {'request' : request})
        data = serializer.data

        if lean != 'EN':
            for item in data:
                if item.get('item_name'):
                    item['item_name'] = translate_text(item['item_name'], lean)
                if item.get('descriptions'):
                    item['descriptions'] = translate_text(item['descriptions'], lean)
                if item.get('category'):
                    item['category'] = translate_text(item['category'], lean)
        return Response(data, status=status.HTTP_200_OK)
    



class ItemDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a single item of the logged-in owner's restaurant by ID.",
        responses={
            200: ItemSerializer,
            404: "Not Found"
        },
        tags=['Item'],
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
    def get(self, request, pk, *args, **kwargs):
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
            item = Item.objects.get(pk=pk, restaurant=restaurant)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found in your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ItemSerializer(item,context = {'request': request})
        data = serializer.data

        if lean != 'EN':
            data['item_name'] = translate_text(data['item_name'] , lean)
            data['descriptions'] = translate_text(data['descriptions'], lean)
            data['category'] = translate_text(data['category'], lean)

        return Response(data, status=status.HTTP_200_OK)




class ItemUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Partially update an item belonging to the logged-in owner's restaurant.",
        request_body=ItemSerializer,
        responses={
            200: openapi.Response("Item updated successfully", ItemSerializer),
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
        tags=['Item'],
        # manual_parameters=[
        #     openapi.Parameter(
        #         'lean', 
        #         openapi.IN_QUERY, 
        #         description="Language code for translation (default is 'en').", 
        #         type=openapi.TYPE_STRING,
        #         default='EN'
        #     ),
        # ],
    )
    def patch(self, request, pk, *args, **kwargs):
        user = request.user
        # lean = request.query_params.get('lean')
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = Item.objects.get(pk=pk, restaurant=restaurant)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found in your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        item_name = request.data.get("item_name", item.item_name)
        status_value = request.data.get("status", item.status)
        descriptions = request.data.get("descriptions", item.descriptions)
        image = request.data.get("image", item.image)
        category = request.data.get("category", item.category)
        price = request.data.get("price", item.price)
        discount = request.data.get("discount", item.discount)
        preparation_time = request.data.get("preparation_time", item.preparation_time)


        # if lean != 'EN':
        #         item_name = translate_text(item_name, 'EN')
        #         descriptions = translate_text(descriptions, 'EN')
        #         category = translate_text(category, 'EN')


        item_data = {
            "item_name": item_name,
            "status": status_value,
            "descriptions": descriptions,
            "image": image,
            "category": category,
            "price": price,
            "discount": discount,
            "preparation_time": preparation_time,
            "restaurant": restaurant.id
        }

        serializer = ItemSerializer(item, data=item_data, partial=True,context = {'request': request})
        if serializer.is_valid():
            serializer.save()
            data = serializer.data

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"restaurant_{restaurant.id}",
                {
                    "type": "item_updated",
                    "item": data,
                }
            )

            # if lean != 'EN':
            #     data['item_name'] = translate_text(data['item_name'] , lean)
            #     data['descriptions'] = translate_text(data['descriptions'], lean)
            #     data['category'] = translate_text(data['category'], lean)

            return Response(data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ItemDeleteAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Delete an item belonging to the logged-in owner's restaurant.",
        responses={
            200: "Item deleted successfully",
            404: "Item not found",
            400: "No restaurant assigned",
            401: "Unauthorized",
        },
        tags=['Item'],
    )
    def delete(self, request, pk, *args, **kwargs):
        user = request.user

        # Check if user has a restaurant
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get item and ensure it belongs to user's restaurant
        try:
            item = Item.objects.get(pk=pk, restaurant=restaurant)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found in your restaurant."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete item
        item.delete()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"restaurant_{restaurant.id}",
            {
                "type": "item_deleted",
                "item_id": item,
            }
        )
        return Response({"message": "Item deleted successfully."}, status=status.HTTP_200_OK)





class RestaurantCategoriesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all unique item categories for a restaurant",
        manual_parameters=[
            openapi.Parameter(
                'lean', 
                openapi.IN_QUERY, 
                description="Language code for translation (default is 'en').", 
                type=openapi.TYPE_STRING,
                default='EN'
            ),
        ],
        tags=['Item'],
        responses={200: openapi.Response(
            description="List of unique categories",
            examples={
                "application/json": {
                    "categories": ["Beverages", "Desserts", "Main Course"]
                }
            }
        )}
    )
    def get(self, request):

        user = request.user
        lean = request.query_params.get('lean')
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        categories = Item.objects.filter(restaurant_id=restaurant.id) \
                                 .values_list('category', flat=True) \
                                 .distinct()
        categories = list(categories)
        if lean != 'EN':
            categories = [translate_text(cat, lean) for cat in categories]
        return Response({"categories": categories}, status=status.HTTP_200_OK)
    



class MenuExtractorView(APIView):
    """
    API view to extract menu data from uploaded PDF or images.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        user  = request.user
        serializer = MenuFileSerializer(data=request.data)  
        try:
            restaurant = Restaurant.objects.get(owner=user)
        except Restaurant.DoesNotExist:
            return Response(
                {"error": "You don't have a restaurant assigned."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(restaurant)

        if serializer.is_valid():
            files = serializer.validated_data['files']

            if not files:
                return Response({"error": "No files uploaded."}, status=status.HTTP_400_BAD_REQUEST)
            temp_dir = tempfile.mkdtemp()

            try:
                # Case 1: Single PDF
                if len(files) == 1 and files[0].name.lower().endswith(".pdf"):
                    pdf_path = os.path.join(temp_dir, files[0].name)
                    with open(pdf_path, "wb") as f:
                        f.write(files[0].read())

                    menu_data = extract_from_pdf(pdf_path)
                else:
                    for file in files:
                        file_path = os.path.join(temp_dir, file.name)
                        with open(file_path, "wb") as f:
                            f.write(file.read())

                    validate_images(temp_dir)

                    pdf_path = os.path.join(temp_dir, "output_menu.pdf")
                    jpgs_to_pdf(temp_dir, pdf_path)
                    menu_data = extract_from_pdf(pdf_path)

                data =json.loads(menu_data)

                if isinstance(data, list):
                    items = data
                else:
                    items = data.get("items", [])

                items_created = []
                for item_data in items:
                    try:
                        item = Item(
                            item_name=item_data.get('item_name'),
                            status=item_data.get('status') or 'available',
                            descriptions=item_data.get('descriptions') or "",
                            image=None,  # handle later if needed
                            category=item_data.get('category'),
                            price=item_data.get('price') or 0,
                            discount=item_data.get('discount') or 0,
                            preparation_time=item_data.get('preparation_time'),
                            restaurant=restaurant
                        )
                        item.save()
                        items_created.append(item.id)
                    except Exception:
                        print("❌ Error saving item:", traceback.format_exc())
                        continue

                return Response(
                    {"message": "Menu processed successfully.", "items_created": items_created},
                    status=status.HTTP_200_OK
                )

            except Exception as e:
                return Response({"error": f"Failed to process files: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    






