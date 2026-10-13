"""Cria somente ambientes ausentes; nunca sobrescreve configuração existente."""
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for destination, example in [
    (ROOT / "backend/.env", ROOT / "backend/.env.example"),
    (ROOT / "web/.env.local", ROOT / "web/.env.local.example"),
]:
    if destination.exists():
        print(f"Preservado: {destination.relative_to(ROOT)}")
        continue
    content = example.read_text(encoding="utf-8")
    if destination.parent.name == "backend":
        content = content.replace("DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_hex(32) + "\n")
    destination.write_text(content, encoding="utf-8")
    print(f"Criado: {destination.relative_to(ROOT)}")
