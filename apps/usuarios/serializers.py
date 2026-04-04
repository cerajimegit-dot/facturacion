"""Serializers for authentication and user management."""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Usuario, Membership
from apps.empresas.models import Empresa


class EmpresaSimpleSerializer(serializers.ModelSerializer):
    """Serializer for empresa info in login response."""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = ['id', 'codigo', 'nombre', 'logo', 'logo_url', 'moneda_principal']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None


class EmailTokenObtainSerializer(serializers.Serializer):
    """Login with email + password, return JWT tokens."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Look up user by email
        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError('Credenciales inválidas.')

        if not user.check_password(password):
            raise serializers.ValidationError('Credenciales inválidas.')

        if not user.is_active:
            raise serializers.ValidationError('Cuenta desactivada.')

        refresh = RefreshToken.for_user(user)
        
        # Build user response with empresa info
        user_data = {
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'rol': user.rol,
        }
        
        # Include empresa info from Membership (first accessible empresa)
        empresa_data = None
        membership = Membership.objects.filter(
            usuario=user, 
            activo=True
        ).select_related('empresa').first()
        
        if membership:
            serializer = EmpresaSimpleSerializer(
                membership.empresa, 
                context={'request': getattr(self, '_context', {}).get('request')}
            )
            empresa_data = serializer.data
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data,
            'empresa': empresa_data,
        }


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)
    empresa_codigo = serializers.CharField(required=False, allow_blank=True, write_only=True)
    empresa_nombre = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'telefono', 'password', 'password2', 'empresa_codigo', 'empresa_nombre',
        ]
        read_only_fields = ['id']

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password': 'Las contraseñas no coinciden.'}
            )
        # Auto-generate username from email if not provided
        if not attrs.get('username'):
            base = attrs['email'].split('@')[0]
            username = base
            counter = 1
            while Usuario.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            attrs['username'] = username
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        empresa_codigo = validated_data.pop('empresa_codigo', None)
        empresa_nombre = validated_data.pop('empresa_nombre', None)
        
        # Create user
        user = Usuario(**validated_data)
        user.set_password(password)
        
        # Create empresa if both codigo and nombre provided
        if empresa_codigo and empresa_nombre:
            empresa, _ = Empresa.objects.get_or_create(
                codigo=empresa_codigo,
                defaults={'nombre': empresa_nombre}
            )
            user.empresa = empresa
            user.rol = 'admin'  # First user of company is admin
        
        user.save()
        
        # Create Membership for access control
        if user.empresa:
            Membership.objects.get_or_create(
                usuario=user,
                empresa=user.empresa,
                defaults={'rol': user.rol, 'activo': True}
            )
        
        return user


class UsuarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    empresa_id = serializers.CharField(source='empresa.id', read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'telefono', 'avatar', 'idioma', 'zona_horaria', 'rol',
            'empresa_id', 'empresa_nombre',
            'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined', 'empresa_id', 'empresa_nombre']


class CambiarPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Contraseña actual incorrecta.')
        return value


class MembershipSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id', 'usuario', 'empresa', 'rol', 'activo',
            'usuario_nombre', 'empresa_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvitarUsuarioSerializer(serializers.Serializer):
    """Serializer to invite a new user to an empresa."""
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    rol = serializers.ChoiceField(choices=['admin', 'vendedor', 'contador'])
    
    def validate_email(self, value):
        # Check if user already has a membership to THIS empresa
        empresa = self.context.get('empresa')
        user = Usuario.objects.filter(email=value).first()
        if user and Membership.objects.filter(usuario=user, empresa=empresa).exists():
            raise serializers.ValidationError('Este usuario ya tiene acceso a esta empresa.')
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        rol = validated_data['rol']
        empresa = self.context['empresa']
        
        # Check if user exists
        user = Usuario.objects.filter(email=email).first()
        
        if not user:
            # Create new user with temporary password
            import uuid
            temp_password = str(uuid.uuid4())[:12]
            username = email.split('@')[0]
            counter = 1
            while Usuario.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}{counter}"
                counter += 1
            
            user = Usuario(
                email=email,
                username=username,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
            )
            user.set_password(temp_password)
            user.save()
        
        # Always create/update membership to this empresa
        membership, created = Membership.objects.get_or_create(
            usuario=user,
            empresa=empresa,
            defaults={'rol': rol, 'activo': True}
        )
        
        if not created:
            # Update existing membership
            membership.rol = rol
            membership.activo = True
            membership.save()
        
        return user
