from rest_framework import serializers
from .models import Order, OrderItem
from items.models import Item
from django.db.models import Sum, Count, Min, Max



class OrderItemCreateSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "item", "quantity", "price", "extras", "extras_price", "special_instructions"]

    def create(self, validated_data):
        order_item = OrderItem.objects.create(**validated_data)
        # Calculate final price with discount and extras
        order_item.price = order_item.get_total_price()
        order_item.save()
        return order_item



class OrderCreateSerializer(serializers.ModelSerializer):
    order_items = OrderItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "phone", "status",
            "total_price", "order_notes", "address", "allergy", "order_items","discount_text", "created_at", "updated_at"
        ]
        read_only_fields = ("total_price", "created_at", "updated_at")

    def create(self, validated_data):
        order_items_data = validated_data.pop("order_items")
        order = Order.objects.create(total_price=0, **validated_data)

        total_price = 0
        for item_data in order_items_data:
            item = item_data["item"]
            order_item = OrderItem.objects.create(
                order=order,
                item=item,
                quantity=item_data["quantity"],
                price=item.price, 
                extras=item_data.get("extras"),
                extras_price=item_data.get("extras_price"),
                special_instructions=item_data.get("special_instructions")
            )
            # Update price using get_total_price()
            order_item.price = order_item.get_total_price()
            order_item.save()
            total_price += order_item.price

        order.total_price = total_price
        order.save()
        return order
    


class OrderUpdateSerializer(serializers.ModelSerializer):
    order_items = OrderItemCreateSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "phone", "status",
            "total_price", "order_notes", "address","discount_text", "allergy", "order_items", "created_at", "updated_at"
        ]
        read_only_fields = ("total_price", "created_at", "updated_at")


    def update(self, instance, validated_data):
        order_items_data = validated_data.pop("order_items", None)

        # Update the non-order item fields (like customer name, address, etc.)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if order_items_data is not None:
            total_price = 0
            for item_data in order_items_data:
                order_item_id = item_data.get("id", None)
                
                if order_item_id:
                    order_item = instance.order_items.get(id=order_item_id)
                    for attr, value in item_data.items():
                        setattr(order_item, attr, value)
                    order_item.price = order_item.get_total_price()
                    order_item.save()
                else:
                    order_item = OrderItem.objects.create(order=instance, **item_data)
                    order_item.price = order_item.get_total_price()
                    order_item.save()

                total_price += order_item.price
            instance.total_price = total_price
            instance.save()
        else:
            total_price = sum([oi.get_total_price() for oi in instance.order_items.all()])
            instance.total_price = total_price
            instance.save()

        return instance



class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__" 
        ref_name = 'OrderItemSerializer'



class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer()

    class Meta:
        model = OrderItem
        fields = [
            "id", "item", "quantity", "price",
            "extras", "extras_price",
            "special_instructions", "created_at", "updated_at"
        ]



class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True) 

    class Meta:
        model = Order
        fields = [
            "id", "restaurant", "customer_name", "email", "status",
            "total_price", "phone", "order_notes","discount_text", "address", "allergy",
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





