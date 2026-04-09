"""Test script for session persistence."""
import sys
sys.path.insert(0, 'c:\\Users\\prueb\\CascadeProjects\\facturacion\\frontend')

import session_manager
import json
from pathlib import Path

print("=" * 60)
print("TEST: Session Persistence Manager")
print("=" * 60)

# Test 1: Crear sesión
print("\n[TEST 1] Guardando sesión de prueba...")
test_session = {
    "access_token": "test_token_12345",
    "refresh_token": "test_refresh_67890",
    "user": {"email": "admin@example.com", "id": 1},
    "empresa_activa": {"id": "test-empresa-id", "nombre": "Test Company"}
}

session_manager.save_session(
    test_session["access_token"],
    test_session["refresh_token"],
    test_session["user"],
    test_session["empresa_activa"]
)

print("✅ Sesión guardada exitosamente")

# Test 2: Cargar sesión
print("\n[TEST 2] Cargando sesión guardada...")
loaded_session = session_manager.load_session()

if loaded_session:
    print(f"✅ Sesión cargada:")
    print(f"   - Email: {loaded_session['user']['email']}")
    print(f"   - Empresa: {loaded_session['empresa_activa']['nombre']}")
    print(f"   - Token válido: {len(loaded_session['access_token']) > 0}")
else:
    print("❌ Error cargando sesión")

# Test 3: Verificar ubicación del archivo
print("\n[TEST 3] Verificando ubicación del archivo...")
session_file = Path.home() / ".facturacion_session" / "session.json"
if session_file.exists():
    print(f"✅ Archivo guardado en: {session_file}")
    with open(session_file, 'r') as f:
        file_content = json.load(f)
    print(f"   - Tamaño: {len(str(file_content))} caracteres")
    print(f"   - Claves: {list(file_content.keys())}")
else:
    print(f"❌ Archivo no encontrado en {session_file}")

# Test 4: Limpiar sesión
print("\n[TEST 4] Limpiando sesión guardada...")
session_manager.clear_session()
loaded_after_clear = session_manager.load_session()

if not loaded_after_clear:
    print("✅ Sesión limpiada correctamente")
else:
    print("❌ Error limpiando sesión")

print("\n" + "=" * 60)
print("PRUEBAS COMPLETADAS")
print("=" * 60)
