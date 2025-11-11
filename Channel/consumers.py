import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection



class RestaurantConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(self.scope["user"])
        self.restaurant_id = self.scope['url_route']['kwargs']['restaurant_id']
        self.room_group_name = f'restaurant_{self.restaurant_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)



    # --- Item events ---
    async def item_created(self, event):
        item_data = event['item']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "event": "item_created",
            "data": item_data
        }))

    
    async def item_updated(self, event):
        await self.send(text_data=json.dumps({
            "event": "item_updated",
            "data": event['item']
        }))


    async def item_deleted(self, event):
        await self.send(text_data=json.dumps({
            "event": "item_deleted",
            "data": {
                "item_id": event["item_id"]
            }
        }))


    # --- Order Created ---

    async def order_created(self, event):
        await self.send(text_data=json.dumps({
            "event": "order_created",
            "data": event["order"]
        }))
        

    async def order_updated(self, event):
        await self.send(text_data=json.dumps({
            "event": "order_updated",
            "data": event["order"]
        }))

    
    # --- Customer service created ---

    async def customer_service_created(self, event):
        await self.send(text_data=json.dumps({
            "event": "customer_service_created",
            "data": event["service"]
        }))


    
    # --- Support Events ---

    async def support_created(self, event):
        await self.send(text_data=json.dumps({
            "event": "support_created",
            "data": event["support"]
        }))

    
    async def support_updated(self, event):
        await self.send(text_data=json.dumps({
            "event": "support_updated",
            "data": event["support"]
        }))

    
    # --- Reservation Events ---

    async def reservation_created(self, event):
        await self.send(text_data=json.dumps({
            "event": "reservation_created",
            "data": event["reservation"]
        }))

    
    async def reservation_updated(self, event):
        await self.send(text_data=json.dumps({
            "event": "reservation_updated",
            "data": event["reservation"]
        }))

    

    