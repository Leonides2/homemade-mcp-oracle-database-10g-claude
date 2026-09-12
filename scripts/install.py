"""Instalador / auto-configurador del proyecto.

Pensado para correr una sola vez justo despues de clonar el repo:

    python scripts/install.py

Que hace:
  1. Crea un entorno virtual en ``.venv`` (si no existe).
  2. Instala las dependencias de ``requirements.txt`` dentro de ese venv.
  3. Copia ``.env.example`` a ``.env`` (si ``.env`` no existe todavia). El
     contenido con credenciales reales lo tiene que llenar la persona a mano,
     eso nunca se automatiza.
  4. Genera ``mcp-config.json`` (gitignored) a partir de
     ``mcp-config.example.json``, con las rutas absolutas ya resueltas para
     esta maquina (al python del venv y a ``src/mcp_server.py``), para
     pegarlo en un cliente MCP tipo Claude Desktop.
  5. Si el CLI ``claude`` esta disponible en el PATH, registra el servidor
     MCP automaticamente con ``claude mcp add`` (scope "user"), sin pedir
     nada a mano.

Es seguro correrlo mas de una vez: no pisa un ``.env`` existente ni vuelve a
registrar el servidor MCP si ya estaba registrado (salvo que se pida
``--force``).

Flags:
    --no-register   No tocar la config de Claude Code (solo venv + deps + .env + mcp-config.json).
    --force         Sobreescribe .env y vuelve a registrar el servidor MCP aunque ya existan.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
MCP_SERVER_NAME = "oracle10g"


def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def step(msg: str) -> None:
    print(f"\n==> {msg}")


def create_venv() -> Path:
    python = venv_python(VENV_DIR)
    if python.exists():
        step(f"Entorno virtual ya existe en {VENV_DIR}, se reutiliza")
        return python

    step(f"Creando entorno virtual en {VENV_DIR}")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    return python


def install_requirements(python: Path) -> None:
    step("Instalando dependencias de requirements.txt")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
        check=True,
        cwd=ROOT,
    )


def setup_env_file(force: bool) -> None:
    env_path = ROOT / ".env"
    example_path = ROOT / ".env.example"

    if env_path.exists() and not force:
        step(".env ya existe, no se toca (usa --force para regenerarlo)")
        return

    step("Creando .env a partir de .env.example")
    shutil.copyfile(example_path, env_path)
    print(
        "    Editalo con tus datos reales antes de usar el proyecto: host, "
        "usuario/password, ORACLE_INSTANT_CLIENT_DIR, etc."
    )


def write_mcp_config(python: Path) -> Path:
    step("Generando mcp-config.json con las rutas de esta maquina")
    config = {
        "mcpServers": {
            MCP_SERVER_NAME: {
                "command": str(python.resolve()),
                "args": [str((ROOT / "src" / "mcp_server.py").resolve())],
            }
        }
    }
    out_path = ROOT / "mcp-config.json"
    out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"    Escrito en {out_path}")
    print(
        "    Este archivo es local (esta en .gitignore): pega su contenido en "
        "la config de mcpServers de tu cliente MCP (Claude Desktop, etc.) si "
        "no usas el registro automatico de Claude Code."
    )
    return out_path


def is_registered_in_claude_code() -> bool:
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return MCP_SERVER_NAME in result.stdout


def register_with_claude_code(python: Path, force: bool) -> None:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        step("CLI 'claude' no encontrado en el PATH, se omite el registro automatico")
        print(
            "    Registralo a mano cuando tengas Claude Code instalado, o usa "
            "mcp-config.json con otro cliente MCP."
        )
        return

    if is_registered_in_claude_code() and not force:
        step(f"El servidor MCP '{MCP_SERVER_NAME}' ya esta registrado en Claude Code, no se toca")
        return

    step(f"Registrando el servidor MCP '{MCP_SERVER_NAME}' en Claude Code (scope user)")
    if force:
        subprocess.run(
            ["claude", "mcp", "remove", MCP_SERVER_NAME, "-s", "user"],
            capture_output=True,
            check=False,
        )
    mcp_server_path = ROOT / "src" / "mcp_server.py"
    result = subprocess.run(
        [
            "claude",
            "mcp",
            "add",
            MCP_SERVER_NAME,
            "-s",
            "user",
            "--",
            str(python.resolve()),
            str(mcp_server_path.resolve()),
        ],
        check=False,
    )
    if result.returncode == 0:
        print(f"    Listo: '{MCP_SERVER_NAME}' registrado para Claude Code.")
    else:
        print("    [ADVERTENCIA] 'claude mcp add' devolvio un error, revisa el mensaje de arriba.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--no-register",
        action="store_true",
        help="No registrar el servidor MCP en Claude Code automaticamente",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobreescribe .env y vuelve a registrar el servidor MCP aunque ya existan",
    )
    args = parser.parse_args()

    python = create_venv()
    install_requirements(python)
    setup_env_file(force=args.force)
    write_mcp_config(python)

    if not args.no_register:
        register_with_claude_code(python, force=args.force)

    step("Instalacion terminada")
    print(
        "    Pendiente: completar .env con tus credenciales reales de Oracle "
        "y la ruta de tu Instant Client antes de correr consultas.\n"
        "    Prueba con: "
        f"{python} scripts/test_connection.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
