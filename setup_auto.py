"""
Script de instalación automática que no requiere input del usuario.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa

User = get_user_model()

print("\n" + "=" * 70)
print("SETUP AUTOMATICO DEL MODULO DE CONTABILIDAD")
print("=" * 70)

# Verificar empresa
print("\n[1] Verificando requisitos...")
try:
    empresa = Empresa.objects.first()
    if not empresa:
        print("[ERROR] No hay empresas en el sistema")
        sys.exit(1)
    print(f"[OK] Empresa encontrada: {empresa.nombre}")
except Exception as e:
    print(f"[ERROR] {str(e)}")
    sys.exit(1)

# Verificar usuario admin
usuario = User.objects.filter(is_superuser=True).first()
if not usuario:
    print("[WARNING] No hay usuarios administradores")
    print("  Creando usuario admin por defecto...")
    try:
        usuario = User.objects.create_superuser(
            username='admin',
            email='admin@localhost',
            password='admin123'
        )
        print(f"[OK] Usuario admin creado: {usuario.username}")
    except Exception as e:
        print(f"[WARNING] No se pudo crear usuario admin: {str(e)}")
        usuario = None
else:
    print(f"[OK] Usuario admin encontrado: {usuario.username}")

# Generar datos demo
print("\n[2] Generando datos de demostración...")
try:
    call_command('generar_demo', '--empresa-id', str(empresa.id), verbosity=1)
    print("[OK] Datos de demostración generados")
except Exception as e:
    print(f"[WARNING] No se pudieron generar datos de demo: {str(e)}")
    print("  Puede intentarlo después con: python manage.py generar_demo")

print("\n" + "=" * 70)
print("SETUP COMPLETADO")
print("=" * 70)

print("""
[OK] La instalacion se completo exitosamente!

PROXIMOS PASOS:

1. VERIFICAR EN ADMIN:
   - Ir a: http://localhost:8000/admin/
   - Revisar: Contabilidad > Plan de Cuentas
   - Revisar: Contabilidad > Asientos

2. TESTEAR API:
   - GET: http://localhost:8000/api/v1/contabilidad/plan-cuentas/
   - GET: http://localhost:8000/api/v1/contabilidad/asientos/

3. CARGAR DATOS REALES:
   python manage.py cargar_plan_cuentas <archivo.xlsx>
   python manage.py importar_proveedores <archivo.xlsx>
   python manage.py importar_productos <archivo.xlsx>
   python manage.py cargar_cotizaciones <archivo.xlsx>

4. GENERAR REPORTES:
   python manage.py reportes balance --empresa-id 1
   python manage.py reportes mayor --empresa-id 1

5. DOCUMENTACION:
   - Leer: apps/contabilidad/README.md
   - Leer: apps/contabilidad/MANAGEMENT_COMMANDS.md
   - Leer: GUIA_RAPIDA_CONTABILIDAD.txt
""")
