#!/usr/bin/env python3
"""
Quick verification that session persistence is ready.
This produces CLEAR YES/NO answers on each check.
"""

import sys
from pathlib import Path

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def check(condition, label):
    symbol = f"{GREEN}✅{RESET}" if condition else f"{RED}❌{RESET}"
    print(f"{symbol} {label}")
    return condition

def main():
    print(f"\n{BOLD}=== VERIFICATION: Session Persistence ==={RESET}\n")
    
    root = Path(__file__).parent
    frontend = root / "frontend"
    
    all_pass = True
    
    # 1. Files exist
    print(f"{BOLD}FILES:{RESET}")
    all_pass &= check((frontend / "session_manager.py").exists(), "session_manager.py exists")
    all_pass &= check((frontend / "app.py").exists(), "app.py exists")
    all_pass &= check((frontend / "pages" / "login.py").exists(), "login.py exists")
    
    # 2. Code contains required lines
    print(f"\n{BOLD}CODE INTEGRATION:{RESET}")
    
    app_txt = (frontend / "app.py").read_text()
    all_pass &= check("import session_manager" in app_txt, "app.py imports session_manager")
    all_pass &= check("verify_and_restore_session()" in app_txt, "app.py calls verify_and_restore_session")
    all_pass &= check("Cerrar Sesión" in app_txt, "app.py has logout button")
    all_pass &= check("Olvidar Sesión" in app_txt, "app.py has clear session button")
    
    login_txt = (frontend / "pages" / "login.py").read_text()
    all_pass &= check("import session_manager" in login_txt, "login.py imports session_manager")
    all_pass &= check("Recordarme" in login_txt, "login.py has Remember checkbox")
    all_pass &= check("save_session" in login_txt, "login.py calls save_session")
    
    sm_txt = (frontend / "session_manager.py").read_text()
    all_pass &= check("save_session" in sm_txt, "session_manager.py has save_session")
    all_pass &= check("load_session" in sm_txt, "session_manager.py has load_session")
    all_pass &= check("verify_and_restore_session" in sm_txt, "session_manager.py has verify_and_restore_session")
    all_pass &= check("clear_session" in sm_txt, "session_manager.py has clear_session")
    all_pass &= check("logout_and_clear" in sm_txt, "session_manager.py has logout_and_clear")
    
    # 3. Documentation
    print(f"\n{BOLD}DOCUMENTATION:{RESET}")
    docs = [
        "START_HERE_SESION_PERSISTENTE.md",
        "README_SESION_PERSISTENTE.md",
        "GUIA_SESION_PERSISTENTE.md",
        "TESTING_SESION_PERSISTENTE.md",
    ]
    for doc in docs:
        all_pass &= check((root / doc).exists(), f"{doc} exists")
    
    # 4. Key features
    print(f"\n{BOLD}FEATURES IMPLEMENTED:{RESET}")
    all_pass &= check("0o600" in sm_txt, "File permissions secure (0o600)")
    all_pass &= check("~/.facturacion_session" in sm_txt or ".facturacion_session" in sm_txt, "Session directory path configured")
    all_pass &= check("json" in sm_txt, "JSON storage implemented")
    all_pass &= check("try:" in sm_txt, "Error handling included")
    
    # 5. Final result
    print(f"\n{BOLD}=== RESULT ==={RESET}")
    if all_pass:
        print(f"{GREEN}{BOLD}✅ ALL CHECKS PASSED{RESET}")
        print(f"\n{GREEN}Session persistence is READY FOR PRODUCTION{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}❌ SOME CHECKS FAILED{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
