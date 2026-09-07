"""
Inyecta los cubos JSON de ./data/ dentro de dashboard_template.html y escribe
dos archivos:
  - tablero_fragment.html              -> fragmento (sin <html>/<head>/<body>),
                                           listo para publicar como Artifact
  - tablero_ejecucion_presupuestal.html -> documento HTML completo y
                                           autocontenido para abrir localmente

Uso:
    python inject_data.py
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
TEMPLATE = BASE / "dashboard_template.html"
FRAGMENT_OUT = BASE / "tablero_fragment.html"
STANDALONE_OUT = BASE / "tablero_ejecucion_presupuestal.html"

FILES = [
    "kpis", "serie_mensual", "nivel_gob",
    "departamento_pim", "departamento_ejec",
    "sector_pim", "sector_ejec",
    "funcion_pim", "funcion_ejec",
    "categoria_pim", "categoria_ejec",
    "generica_pim", "generica_ejec",
    "top_pliegos", "top_proyectos",
]

data = {}
for name in FILES:
    data[name] = json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

template = TEMPLATE.read_text(encoding="utf-8")
marker = "/*__DATA_JSON__*/{}"
assert marker in template, "No se encontro el marcador de datos en la plantilla"
fragment = template.replace(marker, payload)
FRAGMENT_OUT.write_text(fragment, encoding="utf-8")
print(f"Escrito {FRAGMENT_OUT.name} ({FRAGMENT_OUT.stat().st_size/1024:.1f} KB)")

standalone = (
    "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n"
    "<meta charset=\"UTF-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    f"{fragment}"
    "\n</body>\n</html>\n"
)
# el fragmento no trae <body>; lo insertamos tras el bloque <style> inicial
standalone = standalone.replace("</style>\n\n<div", "</style>\n</head>\n<body>\n<div", 1)
STANDALONE_OUT.write_text(standalone, encoding="utf-8")
print(f"Escrito {STANDALONE_OUT.name} ({STANDALONE_OUT.stat().st_size/1024:.1f} KB)")
