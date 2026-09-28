from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from users.permissions import IsAdminUserOrReadOnly
from .models import Category, Product, ProductVariant, Comment, Like
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer, ProductVariantSerializer

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    pagination_class = StandardResultsSetPagination
    
    # Filtering, Searching, Ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category'] # Custom filters for price will need a FilterSet because price is in ProductVariant, but TZ says product filtering
    search_fields = ['name', 'description']
    ordering_fields = ['created_at'] # We'll handle complex price ordering if needed

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        product = self.get_object()
        user = request.user
        
        # Agar Like bosilgan bo'lsa - o'chiramiz, yo'qsa - yaratamiz (Toggle)
        like_obj, created = Like.objects.get_or_create(product=product, user=user)
        
        if not created:
            like_obj.delete()
            return Response({'status': 'Like olib tashlandi'})
        
        return Response({'status': 'Like bosildi'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def comments(self, request, pk=None):
        product = self.get_object()
        
        if request.method == 'GET':
            comments = Comment.objects.filter(product=product).order_by('-created_at')
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
            
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, product=product)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Foydalanuvchi yoqtirgan hamma mahsulotlari uchun
class LikedProductsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        # Like bosilgan mahsulotlarni ajratib olamiz
        liked_product_ids = Like.objects.filter(user=user).values_list('product_id', flat=True)
        return Product.objects.filter(id__in=liked_product_ids)

class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminUserOrReadOnly]
