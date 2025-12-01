from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import format_html, format_html_join
from decimal import Decimal
from django.template.loader import render_to_string

def send_order_confirmation_email(order):
    """Send order confirmation email after order creation"""
    if not order.customer or not order.customer.email:
        return
    
    customer = order.customer
    restaurant = order.restaurant
    subject = f"Order Confirmation - {restaurant.resturent_name}"

    # Build item rows safely
    item_rows = format_html_join(
        "",
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
        (
            (
                item.item_json['name'],
                item.extras or "-",
                item.quantity,
                "{:.2f}".format(item.item_json['price']),
                "{:.2f}".format(Decimal(item.extras_price or 0)),
                "{:.2f}".format(Decimal(item.item_json['discount'] or 0)),
                "{:.2f}".format(item.price)
            )
            for item in order.order_items.all()
        )
    )
    
    delivery_fee = 0
    if getattr(order, "delivery_area_json", None):
        delivery_fee = order.delivery_area_json.get("delivery_fee", 0)

    # Final message
    message = format_html(
        """
        <h2>✅ Your Order is Confirmed!</h2>
        <p>Hi <b>{}</b>,</p>
        <p>Thank you for ordering from <b>{}</b>. Here are your order details:</p>

        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
            <tr>
                <th>Item</th>
                <th>Extras</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Extras Price</th>
                <th>Discount %</th>
                <th>Total</th>
            </tr>
            {}
            <tr>
            <td colspan="6" align="left"><b>Delivery Fee</b></td>
                <td><b>{}</b></td>
            </tr>
            <tr>
                <td colspan="6" align="left"><b>Total Price</b></td>
                <td><b>{}</b></td>
            </tr>
        </table>

        <h4>Delivery Info</h4>
        <p><b>Order ID:</b> {}</p>
        <p><b>Customer name:</b> {}</p>
        <p><b>Phone:</b> {}</p>
        <p><b>Address:</b> {}</p>
        <hr>
        <p>We look forward to serving you!</p>
        """,
        customer.customer_name,
        restaurant.resturent_name,
        item_rows,
        Decimal(delivery_fee or 0),
        order.total_price,
        order.id,
        customer.customer_name,
        customer.phone or "N/A",
        customer.address or "N/A"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [customer.email],
        html_message=message
    )



def send_order_verified_email(order):
    """
    Sends a 'Your order verification link' email to the customer.
    """
    if not order.customer or not order.customer.email:
        return

    customer = order.customer
    restaurant = order.restaurant
    print(customer.customer_name)

    verify_link = f"https://api.trusttaste.ai/public/order/verify/{order.id}/"

    subject = f"✅ Order #{order.id} Verification Required"

    message = f"""
    Hello {customer.customer_name},

    Your order (ID: {order.id}) has been successfully created.

    Please click the link below to verify your order:
    {verify_link}

    Thank you for choosing {restaurant.resturent_name}!

    🧾 Order Summary:
    - Total Price: ${order.total_price}
    - Address: {customer.address or 'N/A'}
    We appreciate your trust and hope to serve you again soon!

    Regards,  
    {restaurant.resturent_name} Team
    """

    # ✅ Inline HTML version
    html_message = f"""
    <html>
    <head>
        <title>Order Verification</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f8f9fa;
                padding: 40px;
                color: #333;
            }}
            .container {{
                max-width: 650px;
                margin: 0 auto;
                background: #fff;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h2 {{
                text-align: center;
                color: #28a745;
            }}
            p {{
                line-height: 1.6;
            }}
            a.verify-btn {{
                display: inline-block;
                margin: 20px 0;
                padding: 12px 25px;
                background-color: #28a745;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
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
            <h2>🔔 Order Verification Required</h2>
            <p>Hello <b>{customer.customer_name}</b>,</p>
            <p>Your order (<b>ID: {order.id}</b>) has been successfully created.</p>
            <p>Please verify your order by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{verify_link}" class="verify-btn">Verify My Order</a>
            </p>

            <h3>🧾 Order Summary</h3>
            <p><b>Total Price:</b> ${order.total_price}</p>
            <p><b>Address:</b> {customer.address or "N/A"}</p>

            <div class="footer">
                <p><b>@{restaurant.resturent_name}</b></p>
                <p>{restaurant.phone_number_1 or ""}</p>
                <p>Thank you for choosing us!</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Verification email sent to {customer.email}")
    except Exception as e:
        print(f"❌ Failed to send verification email: {e}")
    