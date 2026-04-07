#!/usr/bin/env python3
"""
Script para DEMOSTRAR la persistencia de sesión.
Ejecutar antes de usar Streamlit para entender cómo funciona.
"""

import json
from pathlib import Path
import sys

print("\n" + "="*70)
print(" 🔐 DEMOSTRACIÓN: PERSISTENCIA DE SESIÓN EN STREAMLIT")
print("="*70 + "\n")

SESSION_DIR = Path.home() / ".facturacion_session"
SESSION_FILE = SESSION_DIR / "session.json"

print(f"📁 Ubicación de sesión guardada:")
print(f"   {SESSION_FILE}\n")

# Verificar estado actual
if SESSION_FILE.exists():
    print("✅ SESIÓN GUARDADA ENCONTRADA")
    with open(SESSION_FILE, 'r') as f:
        session = json.load(f)
    print(f"\n   User: {session['user']['email']}")
    print(f"   Empresa: {session['empresa_activa']['nombre']}")
    print(f"   Token: {session['access_token'][:30]}...\n")
    
    print("💡 Próxima vez que abras Streamlit:")
    print("   → Se cargará AUTOMÁTICAMENTE sin pedir credenciales\n")
    
    print("🧹 Para limpiar la sesión guardada:")
    print("   → En Streamlit: Sidebar → '🗑️ Olvidar Sesión'")
    print("   → O ejecuta: python -c \"from pathlib import Path; ")
    print("      Path.home().joinpath('.facturacion_session').rmdir()\"\n")
else:
    print("❌ NO HAY SESIÓN GUARDADA YET\n")
    
    print("🚀 PRUEBA ESTO:")
    print("   1. Abre Streamlit: streamlit run frontend/app.py")
    print("   2. Inicia sesión con tus credenciales")
    print("   3. ⭐ MARCA ✅ 'Recordarme en este dispositivo'")
    print("   4. Clic en 'Ingresar'")
    print("   5. Se guardará automáticamente\n")
    
    print("   O ejecuta este script nuevamente después de login")
    print("   para ver confirmación\n")

print("📊 DIFERENCIA: CON vs SIN PERSISTENCIA\n")

print("   ANTES (sin persistencia):")
print("   ├─ Login → Trabajar → Cerrar navegador")
print("   └─ Reabrir → DEBE REINGRESAR ❌\n")

print("   AHORA (con persistencia):")
print("   ├─ Login + ✅ Recordarme → Trabajar")
print("   └─ Reabrir → CARGA AUTOMÁTICO ✅\n")

print("🔒 SEGURIDAD:\n")
print("   ✅ Seguro en:")
print("      • PC personal")
print("      • Oficina (si no compartida)")
print("      • Ambiente corporativo controlado\n")

print("   ❌ NO es seguro en:")
print("      • Computadoras compartidas")
print("      • Cybercafés o locales públicos")
print("      • En estos casos: NO marcar 'Recordarme'\n")

print("📱 BOTONES NUEVOS EN STREAMLIT:\n")
print("   🚪 Cerrar Sesión")
print("      └─ Cierra sesión actual")
print("      └─ Sesión guardada permanece")
print("      └─ Próxima vez se carga automático\n")

print("   🗑️ Olvidar Sesión")
print("      └─ Elimina sesión guardada del archivo")
print("      └─ Próxima vez pide credenciales\n")

print("="*70)
print(" Para comenzar: streamlit run frontend/app.py")
print("="*70 + "\n")
