from rest_framework import serializers
from .models import Order, OrderItem
from items.models import Item
from django.db.models import Sum, Count, Min, Max
from .emails import send_order_confirmation_email,send_order_verified_email
from table.signals import send_twilio_sms_via_assistance




class OrderItemCreateSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_json = serializers.JSONField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "item", "quantity", "price", "extras",
            "extras_price", "special_instructions", "item_json"
        ]

    def create(self, validated_data):
        item = validated_data["item"]
        quantity = validated_data.get("quantity", 1)
        extras_price = validated_data.get("extras_price") or 0

        # Calculate total item price
        total_price = float(item.price) * quantity
        if item.discount:
            total_price -= (float(item.discount) / 100) * total_price
        total_price += float(extras_price)


        # Save snapshot of item details
        validated_data["item_json"] = {
            "id": item.id,
            "item_name": item.item_name,
            "status": item.status,
            "descriptions": item.descriptions,
            "image": item.image.url if item.image else None,
            "category": item.category,
            "price": float(item.price),
            "discount": float(item.discount) if item.discount else None,
            "preparation_time": str(item.preparation_time) if item.preparation_time else None,
            "restaurant_id": item.restaurant.id,
        }

        validated_data["price"] = total_price
        return OrderItem(**validated_data)




class OrderCreateSerializer(serializers.ModelSerializer):
    order_items = OrderItemCreateSerializer(many=True, write_only=True)
    delivery_area_json = serializers.JSONField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "phone", "status",
            "total_price", "order_notes", "address", "allergy",
            "order_items", "discount_text", "delivery_area", "delivery_area_json",
            "verified", "order_type", "created_at", "updated_at"
        ]
        read_only_fields = ("total_price", "delivery_area_json", "created_at", "updated_at")


    def create(self, validated_data):
        order_items_data = validated_data.pop("order_items", [])
        delivery_area = validated_data.get("delivery_area")

        if delivery_area:
            validated_data["delivery_area_json"] = {
                "id": delivery_area.id,
                "postalcode": delivery_area.postalcode,
                "estimated_delivery_time": delivery_area.estimated_delivery_time,
                "delivery_fee": float(delivery_area.delivery_fee or 0),
                "restaurant_id": delivery_area.restaurant.id,
            }


        order = Order.objects.create(total_price=0, **validated_data)

        total_price = 0

        for item_data in order_items_data:
            if isinstance(item_data.get("item"), Item):
                item_data["item"] = item_data["item"].id

            item = Item.objects.get(id=item_data["item"])
            quantity = item_data.get("quantity", 1)
            extras_price = float(item_data.get("extras_price") or 0)

            # ✅ Calculate price correctly
            item_base_price = float(item.price)
            total_item_price = item_base_price * quantity

            if item.discount:
                total_item_price -= (float(item.discount) / 100) * total_item_price

            total_item_price += extras_price

            # Save item_json
            item_json = {
                "id": item.id,
                "name": item.item_name,
                "price": float(item.price),
                "discount": float(item.discount) if item.discount else None,
                "description": getattr(item, "description", None),
                "item_name": item.item_name,
                "status": item.status,
                "image": item.image.url if item.image else None,
                "category": item.category,
                "preparation_time": str(item.preparation_time) if item.preparation_time else None,
                "restaurant_id": item.restaurant.id,
            }

            # ✅ Create OrderItem with price set
            order_item = OrderItem.objects.create(
                order=order,
                item=item,
                quantity=quantity,
                price=total_item_price,
                extras=item_data.get("extras"),
                extras_price=extras_price,
                special_instructions=item_data.get("special_instructions"),
                item_json=item_json,
            )

            total_price += total_item_price

        # Add delivery fee if applicable
        if order.order_type == "delivery" and delivery_area:
            # print('💵💵💵💵 Adding delivery fee:', delivery_area.delivery_fee)
            total_price += float(delivery_area.delivery_fee or 0)

        # Save total price
        order.total_price = total_price
        order.save()

        phone = order.phone
        has_previous_verified = False

        if phone:
            has_previous_verified = Order.objects.filter(
                phone=phone,
                verified=True,
                status ="completed",
            ).exists()
        
        if not has_previous_verified:
            order.verified = False
            order.save()
            send_order_verified_email(order)
        else:
            send_order_confirmation_email(order)
        return order




class OrderVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        modele = Order
        fields = ['verified']




class OrderUpdateSerializer(serializers.ModelSerializer):
    order_items = OrderItemCreateSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "phone", "status",
            "total_price", "order_notes", "address", "discount_text",
            "allergy", "order_items", "created_at", "updated_at"
        ]
        read_only_fields = ("total_price", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for PATCH
        for field in self.fields.values():
            field.required = False

    def update(self, instance, validated_data):
        order_items_data = validated_data.pop("order_items", None)

        # --- Update basic fields ---
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        total_price = 0

        if order_items_data is not None:
            instance.order_items.all().delete()

            for item_data in order_items_data:
                item_id = item_data.get("item")
                if not item_id:
                    continue

                item = Item.objects.get(id=item_id)
                quantity = item_data.get("quantity", 1)
                extras_price = float(item_data.get("extras_price") or 0)

                # ✅ Price calculation (same as create)
                item_base_price = float(item.price)
                total_item_price = item_base_price * quantity

                if item.discount:
                    total_item_price -= (float(item.discount) / 100) * total_item_price

                total_item_price += extras_price

                # ✅ Snapshot of item details
                item_json = {
                    "id": item.id,
                    "name": item.item_name,
                    "price": float(item.price),
                    "discount": float(item.discount) if item.discount else None,
                    "description": getattr(item, "description", None),
                    "item_name": item.item_name,
                    "status": item.status,
                    "image": item.image.url if item.image else None,
                    "category": item.category,
                    "preparation_time": str(item.preparation_time) if item.preparation_time else None,
                    "restaurant_id": item.restaurant.id,
                }

                # ✅ Create the updated OrderItem
                order_item = OrderItem.objects.create(
                    order=instance,
                    item=item,
                    quantity=quantity,
                    price=total_item_price,
                    extras=item_data.get("extras"),
                    extras_price=extras_price,
                    special_instructions=item_data.get("special_instructions"),
                    item_json=item_json,
                )

                total_price += total_item_price

        else:
            # No order_items provided → just recalculate total
            total_price = sum([float(oi.price) for oi in instance.order_items.all()])

        # ✅ Add delivery fee if applicable
        if instance.order_type == "delivery" and instance.delivery_area:
            total_price += float(instance.delivery_area.delivery_fee or 0)

        # ✅ Update total price
        instance.total_price = total_price
        instance.save()

        return instance





# class ItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Item
#         fields = "__all__"
#         ref_name = 'OrderItemSerializer'





class OrderItemSerializer(serializers.ModelSerializer):
    # item = ItemSerializer()
    class Meta:
        model = OrderItem
        fields = [
            "id", "quantity", "price",
            "extras", "extras_price",
            "special_instructions",'item_json'
        ]





class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True) 

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "status",
            "total_price", "phone", "order_notes","discount_text", "address",'order_type', "allergy",'delivery_area_json',
            "created_at", "updated_at", "order_items"
        ]





class CustomerOrderGroupSerializer(serializers.Serializer):
    customerInfo = serializers.SerializerMethodField()
    orders = OrderSerializer(many=True)

    def get_customerInfo(self, obj):
        # obj is a dict: {"orders": queryset}
        orders = obj.get("orders", [])

        if not orders:
            return {}

        first_order = orders.first() if hasattr(orders, "first") else orders[0]

        stats = orders.aggregate(
            total_order=Count("id"),
            total_order_price=Sum("total_price"),
            first_order_create_date=Min("created_at"),
            last_order_date=Max("created_at"),
        ) if hasattr(orders, "aggregate") else {
            "total_order": len(orders),
            "total_order_price": sum([float(o.total_price) for o in orders]),
            "first_order_create_date": first_order.created_at,
            "last_order_date": orders[-1].created_at,
        }

        return {
            "name": first_order.customer_name,
            "email": first_order.email,
            "phone": first_order.phone,
            "first_order_create_date": stats["first_order_create_date"],
            "last_order_date": stats["last_order_date"],
            "total_order": stats["total_order"],
            "total_order_price": stats["total_order_price"],
        }





