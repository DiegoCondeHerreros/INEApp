#!/usr/bin/env python3
"""
Elimina tildes y normaliza cabeceras de los CSV del ADRH.
Ejecutar desde PowerShell: python scripts/normalizar_csv.py
"""
import unicodedata
from pathlib import Path

def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

TABLAS = {
#    "31097.csv": {
#        "Indicadores de renta media y mediana": "Indicadores_renta"
#    },
#    "31105.csv": {
#        "Indicadores demográficos": "Indicadores_demograficos"
#    },
#    "37727.csv": {
#        "Índice de Gini y Distribución de la renta P80/P20": "Indicadores_gini_p8020"
#    },
    "5.csv": {
        "Número de viviendas turísticas, plazas y ratio por sección": "Viviendas_turisticas"
    }
}

RAW_DIR = Path("data/raw")

for fichero, reemplazos in TABLAS.items():
    origen = RAW_DIR / fichero
    if not origen.exists():
        print(f"AVISO: {origen} no encontrado")
        continue

    # Leer con utf-8-sig elimina BOM automáticamente
    lineas = origen.read_text(encoding="iso-8859-1").splitlines(keepends=True)

    # Normalizar cabecera (primera línea)
    for original, nuevo in reemplazos.items():
        lineas[0] = lineas[0].replace(original, nuevo)

    # Quitar tildes de TODAS las líneas para evitar problemas con la JVM
    lineas = [quitar_tildes(l) for l in lineas]

    # Escribir en UTF-8 sin BOM
    destino = RAW_DIR / fichero.replace(".csv", "-clean.csv")
    destino.write_text("".join(lineas), encoding="utf-8")
    print(f"OK: {destino}")