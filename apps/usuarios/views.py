"""Views for authentication and user management."""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import Usuario, Membership, ConfiguracionAcceso, MODULOS_DISPONIBLES, ACCESOS_DEFAULT
from .serializers import (
    EmailTokenObtainSerializer,
    RegistroSerializer,
    UsuarioSerializer,
    CambiarPasswordSerializer,
    MembershipSerializer,
    InvitarUsuarioSerializer,
    ConfiguracionAccesoSerializer,
)


class EmailLoginView(APIView):
    """Login with email + password, returns JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailTokenObtainSerializer(data=request.data, context={'request': request})
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


class InvitarUsuarioView(APIView):
    """Invite a new user to the authenticated user's empresa."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check that user belongs to an empresa
        if not request.user.empresa:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions - only admins can invite
        if request.user.rol != 'admin':
            return Response(
                {'error': 'Solo administradores pueden invitar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InvitarUsuarioSerializer(
            data=request.data,
            context={'empresa': request.user.empresa}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'id': str(user.id),
                'email': user.email,
                'nombre': user.get_full_name(),
                'rol': user.rol,
                'mensaje': 'Usuario invitado correctamente'
            },
            status=status.HTTP_201_CREATED
        )


class ConfiguracionAccesoViewSet(viewsets.ModelViewSet):
    """CRUD de configuración de acceso por rol."""
    serializer_class = ConfiguracionAccesoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ConfiguracionAcceso.objects.all()
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    def create(self, request, *args, **kwargs):
        if request.user.rol != 'admin':
            return Response({'error': 'Solo admins'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.rol != 'admin':
            return Response({'error': 'Solo admins'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class MisPermisosView(APIView):
    """Obtener los módulos permitidos para el usuario actual."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresa_id = request.query_params.get('empresa')
        if not empresa_id and user.empresa:
            empresa_id = str(user.empresa_id)

        rol = user.rol
        if empresa_id:
            membership = Membership.objects.filter(
                usuario=user, empresa_id=empresa_id, activo=True
            ).first()
            if membership:
                rol = membership.rol

        if rol == 'admin':
            modulos = [m[0] for m in MODULOS_DISPONIBLES]
        else:
            modulos = ConfiguracionAcceso.get_modulos_permitidos(
                empresa_id, rol
            ) if empresa_id else ACCESOS_DEFAULT.get(rol, [])

        return Response({
            'rol': rol,
            'modulos_permitidos': modulos,
            'modulos_disponibles': [{"key": k, "label": v} for k, v in MODULOS_DISPONIBLES],
            'defaults': ACCESOS_DEFAULT,
        })
