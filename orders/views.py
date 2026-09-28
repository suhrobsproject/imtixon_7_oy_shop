from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from django.db import transaction
from django.shortcuts import get_object_or_404

from products.models import ProductVariant
from users.models import Address
from .models import Cart, CartItem, Order, OrderItem, Payment
from .serializers import CartSerializer, OrderSerializer

class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # TZ ga asosan bizda mahsulotlar variantlari mavjud, shuning uchun variant_id qabul qilamiz
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not variant_id:
            return Response({'error': 'variant_id kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)

        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        # Savatda shu mahsulotdan bormi tekshiramiz
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
            
        cart_item.save()
        return Response({'status': 'Mahsulot savatga qo\'shildi', 'quantity': cart_item.quantity}, status=status.HTTP_200_OK)

class CartRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        variant_id = request.data.get('variant_id')
        
        cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)
        cart_item.delete()
        
        return Response({'status': 'Mahsulot savatdan o\'chirildi'}, status=status.HTTP_200_OK)

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    # @transaction.atomic bu tranzaksiya, agar o'rtada xato chiqsa barcha o'zgarishlar rollback (bekor) qilinadi
    @transaction.atomic
    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        address_id = request.data.get('address_id')
        
        if not address_id:
            return Response({'error': 'Yetkazib berish manzili (address_id) kiritilishi shart!'}, status=status.HTTP_400_BAD_REQUEST)
            
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        cart_items = cart.items.all()
        if not cart_items.exists():
            return Response({'error': 'Savatingiz bo\'sh'}, status=status.HTTP_400_BAD_REQUEST)

        total_price = 0
        
        # 1. Ombor(stock)ni tekshiramiz va umumiy summani hisoblaymiz
        for item in cart_items:
            if item.variant.stock < item.quantity:
                return Response(
                    {'error': f'{item.variant.product.name} mahsulotidan omborda yetarli emas. Qoldiq: {item.variant.stock} ta.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            total_price += item.quantity * item.variant.price

        # 2. Buyurtmani (Order) yaratamiz
        order = Order.objects.create(
            user=request.user,
            address=address,
            total_price=total_price,
            status='pending'
        )

        # 3. Buyurtma qismlarini (OrderItem) yaratamiz va ombordan (stock) ayirib tashlaymiz
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price # Sotib olingan paytdagi tarixiy narx saqlanib qoladi
            )
            # Stockni kamaytirish (ombordan chiqarish)
            item.variant.stock -= item.quantity
            item.variant.save()

        # 4. Savatni tozalash (ichidagi narsalarni o'chirish)
        cart_items.delete()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class OrderHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        # Foydalanuvchi faqat o'zining buyurtmalarini ko'radi
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        provider = request.data.get('provider', 'Payme')
        transaction_id = request.data.get('transaction_id', 'TEST-TRANS-123')

        if order.status == 'paid':
            return Response({'error': 'Bu buyurtma uchun allaqachon to\'lov qilingan'}, status=status.HTTP_400_BAD_REQUEST)

        # To'lovni yaratish (Simulyatsiya)
        payment = Payment.objects.create(
            order=order,
            provider=provider,
            amount=order.total_price,
            status='success',
            transaction_id=transaction_id
        )

        # Buyurtma holatini yangilash
        order.status = 'paid'
        order.save()

        return Response({
            'status': 'To\'lov muvaffaqiyatli amalga oshirildi',
            'order_status': order.status,
            'payment_id': payment.id
        }, status=status.HTTP_200_OK)
