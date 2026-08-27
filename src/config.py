"""Carga y valida la configuracion desde el archivo .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    service_name: str | None
    sid: str | None
    user: str
    password: str
    instant_client_dir: str
    read_only: bool
    max_rows: int
    query_timeout_seconds: int

    @property
    def dsn_target(self) -> str:
        """Descripcion legible del destino (sin credenciales) para logs."""
        target = self.service_name or self.sid
        return f"{self.host}:{self.port}/{target}"


def load_settings(env_path: str | None = None) -> Settings:
    load_dotenv(dotenv_path=env_path, override=False)

    host = os.getenv("ORACLE_HOST", "").strip()
    port_raw = os.getenv("ORACLE_PORT", "1521").strip()
    service_name = os.getenv("ORACLE_SERVICE_NAME", "").strip() or None
    sid = os.getenv("ORACLE_SID", "").strip() or None
    user = os.getenv("ORACLE_USER", "").strip()
    password = os.getenv("ORACLE_PASSWORD", "")
    instant_client_dir = os.getenv("ORACLE_INSTANT_CLIENT_DIR", "").strip()
    read_only = os.getenv("READ_ONLY", "true").strip().lower() != "false"
    max_rows_raw = os.getenv("MAX_ROWS", "200").strip()
    timeout_raw = os.getenv("QUERY_TIMEOUT_SECONDS", "30").strip()

    missing = [
        name
        for name, value in [
            ("ORACLE_HOST", host),
            ("ORACLE_USER", user),
            ("ORACLE_PASSWORD", password),
            ("ORACLE_INSTANT_CLIENT_DIR", instant_client_dir),
        ]
        if not value
    ]
    if not service_name and not sid:
        missing.append("ORACLE_SERVICE_NAME o ORACLE_SID")
    if missing:
        raise ValueError(
            "Faltan variables de entorno requeridas en .env: " + ", ".join(missing)
        )

    try:
        port = int(port_raw)
        max_rows = int(max_rows_raw)
        query_timeout_seconds = int(timeout_raw)
    except ValueError as exc:
        raise ValueError(
            "ORACLE_PORT, MAX_ROWS y QUERY_TIMEOUT_SECONDS deben ser numeros enteros"
        ) from exc

    return Settings(
        host=host,
        port=port,
        service_name=service_name,
        sid=sid,
        user=user,
        password=password,
        instant_client_dir=instant_client_dir,
        read_only=read_only,
        max_rows=max_rows,
        query_timeout_seconds=query_timeout_seconds,
    )
