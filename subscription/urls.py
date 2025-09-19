from django.urls import path
from .views import CreateCheckoutSessionView,StripeWebhookView,CancelSubscriptionView,SubscriptionStatusView

urlpatterns = [
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('cancel-subscription/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('subscription-status/', SubscriptionStatusView.as_view(), name='subscription-status'),
]