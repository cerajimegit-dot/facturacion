"""Fix .env encoding to UTF-8 and normalize line endings."""
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
if not env_path.exists():
    raise SystemExit(f".env no existe: {env_path}")

raw = env_path.read_bytes()
try:
    raw.decode('utf-8')
    print('.env ya es UTF-8 válido')
except UnicodeDecodeError as e:
    print(f'UnicodeDecodeError detectado en .env: {e}')
    text = raw.decode('latin-1', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Elimina caracteres de control extraños excepto tab y saltos de línea
    text = ''.join(ch if ch == '\n' or ch == '\t' or (' ' <= ch <= '~') or ord(ch) > 127 else '?' for ch in text)
    env_path.write_text(text, encoding='utf-8', newline='\n')
    print('.env reescrito en UTF-8')
else:
    emsg = raw.decode('utf-8')
    # Normalize 
 -> 

    if '\r' in emsg:
        env_path.write_text(emsg.replace('\r\n', '\n').replace('\r', '\n'), encoding='utf-8', newline='\n')
        print('Normalizado endings en .env')
    else:
        print('No es necesario normalizar .env')
