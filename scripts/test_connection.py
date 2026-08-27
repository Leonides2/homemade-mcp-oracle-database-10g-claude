"""Fase 0: prueba minima de conexion contra Oracle 10g en modo thick.

Uso:
    python scripts/test_connection.py

Requiere un archivo .env en la raiz del proyecto (ver .env.example).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings
from src.db import get_connection


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"[ERROR] Configuracion invalida: {exc}")
        return 1

    print(f"Conectando a {settings.dsn_target} como {settings.user} (modo thick)...")
    print(f"Instant Client: {settings.instant_client_dir}")

    try:
        with get_connection(settings) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT sysdate, banner FROM v$version WHERE rownum = 1")
                row = cursor.fetchone()
            except Exception:
                # El usuario de solo lectura puede no tener permiso sobre v$version.
                cursor.execute("SELECT sysdate FROM dual")
                row = cursor.fetchone()
            print("[OK] Conexion exitosa.")
            print(f"Resultado: {row}")
    except Exception as exc:  # noqa: BLE001 - queremos ver cualquier error tal cual
        print(f"[ERROR] Fallo la conexion o la consulta: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
