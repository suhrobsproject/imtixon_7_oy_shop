from django.urls import path
from .views import CartDetailView, CartAddView, CartRemoveView, CheckoutView, OrderHistoryView, PaymentView

urlpatterns = [
    path('cart/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/add/', CartAddView.as_view(), name='cart-add'),
    path('cart/remove/', CartRemoveView.as_view(), name='cart-remove'),
    path('orders/checkout/', CheckoutView.as_view(), name='order-checkout'),
    path('orders/', OrderHistoryView.as_view(), name='order-history'),
    path('orders/<int:order_id>/pay/', PaymentView.as_view(), name='order-pay'),
]
