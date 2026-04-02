"""Views for authentication and user management."""
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import Usuario, Membership
from .serializers import (
    EmailTokenObtainSerializer,
    RegistroSerializer,
    UsuarioSerializer,
    CambiarPasswordSerializer,
    MembershipSerializer,
)


class EmailLoginView(APIView):
    """Login with email + password, returns JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailTokenObtainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegistroView(generics.CreateAPIView):
    """Public endpoint for user registration."""
    queryset = Usuario.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]


class PerfilView(generics.RetrieveUpdateAPIView):
    """Get/update the authenticated user's profile."""
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class CambiarPasswordView(APIView):
    """Change password for authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response(
            {'detail': 'Contraseña actualizada correctamente.'},
            status=status.HTTP_200_OK,
        )


class MembershipViewSet(viewsets.ModelViewSet):
    """Manage memberships (invite users to empresas)."""
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Membership.objects.select_related('usuario', 'empresa')
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs.filter(
            empresa__memberships__usuario=self.request.user,
            empresa__memberships__activo=True,
        ).distinct()
