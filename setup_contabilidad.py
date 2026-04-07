"""
Script de instalación y configuración inicial del módulo de contabilidad.
Execute: python setup_contabilidad.py
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa
from apps.contabilidad.models import PlanCuentas

User = get_user_model()

def print_header(texto):
    print("\n" + "="*70)
    print(f"  {texto}")
    print("="*70)

def print_section(texto):
    print(f"\n[*] {texto}")
    print("-" * 70)

def verificar_prerequisitos():
    """Verifica que el entorno esté listo."""
    print_section("1. Verificando Prerequisitos")
    
    # Django
    print(f"[OK] Django {django.get_version()}")
    
    # Empresas
    empresas = Empresa.objects.count()
    if empresas == 0:
        print("[ERROR] No hay empresas en el sistema")
        print("   Cree al menos una empresa en el admin antes de continuar")
        return False
    print(f"[OK] Empresas en sistema: {empresas}")
    
    # Usuario admin
    admins = User.objects.filter(is_superuser=True).count()
    if admins == 0:
        print("[ERROR] No hay usuarios administradores")
        print("   Cree un superusuario con: python manage.py createsuperuser")
        return False
    print(f"[OK] Usuarios admin: {admins}")
    
    return True

def generar_migraciones():
    """Genera las migraciones para contabilidad."""
    print_section("2. Generando Migraciones")
    
    try:
        print("  - Contabilidad...")
        call_command('makemigrations', 'contabilidad', verbosity=1)
        
        print("  - Compras (Proveedor extendido)...")
        call_command('makemigrations', 'compras', verbosity=1)
        
        print("  - Productos (Producto extendido)...")
        call_command('makemigrations', 'productos', verbosity=1)
        
        print("\n[OK] Migraciones generadas exitosamente")
        return True
    except Exception as e:
        print(f"[ERROR] Error generando migraciones: {str(e)}")
        return False

def aplicar_migraciones():
    """Aplica las migraciones."""
    print_section("3. Aplicando Migraciones")
    
    try:
        call_command('migrate', verbosity=1)
        print("\n[OK] Migraciones aplicadas")
        return True
    except Exception as e:
        print(f"[ERROR] Error aplicando migraciones: {str(e)}")
        return False

def generar_datos_demo():
    """Genera datos de demostración."""
    print_section("4. Generando Datos de Demostración")
    
    empresa = Empresa.objects.first()
    
    try:
        call_command('generar_demo', '--empresa-id', str(empresa.id), verbosity=1)
        print("\n[OK] Datos de demostración generados")
        return True
    except Exception as e:
        print(f"[ERROR] Error generando datos demo: {str(e)}")
        return False

def mostrar_resumen():
    """Muestra un resumen de lo que se ha hecho."""
    print_section("5. Resumen de Instalación")
    
    empresa = Empresa.objects.first()
    
    cuentas = PlanCuentas.objects.filter(empresa=empresa).count()
    
    print(f"Empresa: {empresa.nombre}")
    print(f"Plan de Cuentas: {cuentas} cuentas")
    
    from apps.compras.models import Proveedor
    proveedores = Proveedor.objects.filter(empresa=empresa).count()
    print(f"Proveedores: {proveedores}")
    
    from apps.productos.models import Producto
    productos = Producto.objects.filter(empresa=empresa).count()
    print(f"Productos: {productos}")
    
    from apps.contabilidad.models import Asiento
    asientos = Asiento.objects.filter(empresa=empresa).count()
    print(f"Asientos: {asientos}")
    
    print("\n[OK] Setup completado exitosamente")

def mostrar_proximos_pasos():
    """Muestra los proximos pasos recomendados."""
    print_header("[OK] INSTALACION COMPLETADA!")
    
    print("""
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
   python manage.py reportes mayor --empresa-id 1 --salida reporte.csv
   python manage.py reportes diario --empresa-id 1

5. VERIFICAR SIGNALS:
   - Crear una compra
   - Cambiar estado a 'recepcionada'
   - Verificar que se generó asiento automáticamente

6. DOCUMENTACIÓN:
   - Leer: apps/contabilidad/MANAGEMENT_COMMANDS.md
   - Leer: apps/contabilidad/progress.md

7. PRÓXIMAS IMPLEMENTACIONES:
   - Suite de tests (apps/tests/test_contabilidad_*.py)
   - Dashboard Streamlit (frontend/pages/accounting.py)
   - Automatic cotización loader (scheduler)

⚠️  IMPORTANTE:
   - Revisar migrations generadas antes de producción
   - Hacer backup antes de importar datos masivos
   - Todas las cuentas deben existir antes de crear asientos

¿Preguntas? Ver MANAGEMENT_COMMANDS.md para más detalles.
    """)

def main():
    """Ejecuta el setup completo."""
    print_header("[*] SETUP MODULO DE CONTABILIDAD")
    
    # 1. Verificar
    if not verificar_prerequisitos():
        print("\n[ERROR] Setup cancelado: no se cumplen los prerequisitos")
        return False
    
    # 2. Migraciones
    if not generar_migraciones():
        print("\n[ERROR] Setup cancelado: error en migraciones")
        return False
    
    if not aplicar_migraciones():
        print("\n[ERROR] Setup cancelado: error aplicando migraciones")
        return False
    
    # 3. Demo
    print_section("Está a punto de generar datos de demostración")
    print("Esto creará:")
    print("  - 24 cuentas contables")
    print("  - 3 proveedores de prueba")
    print("  - 3 productos de prueba")
    print("  - 21 cotizaciones diarias")
    print("  - 3 asientos contables")
    respuesta = input("\n¿Desea continuar? (s/n): ").lower().strip()
    
    if respuesta in ['s', 'si', 'yes', 'y']:
        if not generar_datos_demo():
            print("\n[WARNING] Datos de demo no pudieron generarse")
            print("  Puede intentar despues con: python manage.py generar_demo")
    else:
        print("[SKIP] Saltando generacion de datos de demostración")
        print("  Puede hacerlo despues con: python manage.py generar_demo")
    
    # 4. Resumen
    mostrar_resumen()
    
    # 5. Proximos pasos
    mostrar_proximos_pasos()
    
    return True

if __name__ == '__main__':
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
