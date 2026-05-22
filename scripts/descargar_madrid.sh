#!/bin/bash

OUTPUT_FILE="secciones_censales_madrid.geojson"
LIMIT=1000  # Features por página
OFFSET=0
TEMP_DIR="/tmp/ine_pages"

mkdir -p "$TEMP_DIR"
rm -f "$TEMP_DIR"/page_*.json "$OUTPUT_FILE"

echo "Descargando todas las secciones censales de Madrid..."

# Descargar todas las páginas
PAGE=0
while true; do
  URL="https://www.ine.es/geoserver/ogc/features/v1/collections/WMS_INE_SECCIONES_G01:Secciones_2025/items?f=application%2Fgeo%2Bjson&CMUN=28079&limit=$LIMIT&offset=$OFFSET"
  
  echo "Página $PAGE (offset $OFFSET)..."
  
  curl -s "$URL" -o "$TEMP_DIR/page_$PAGE.json"
  
  # Contar features en esta página
  COUNT=$(grep -o '"type":"Feature"' "$TEMP_DIR/page_$PAGE.json" | wc -l)
  
  if [ $COUNT -eq 0 ]; then
    echo "Fin: No hay más features"
    break
  fi
  
  echo "  → $COUNT features descargados"
  
  OFFSET=$((OFFSET + LIMIT))
  PAGE=$((PAGE + 1))
done

# Combinar todos en un único GeoJSON
echo "Combinando páginas..."
echo '{"type":"FeatureCollection","features":[' > "$OUTPUT_FILE"

FIRST=true
for file in "$TEMP_DIR"/page_*.json; do
  if [ -f "$file" ]; then
    # Extraer solo el array de features de cada página
    FEATURES=$(jq -r '.features[]' "$file" 2>/dev/null)
    
    if [ ! -z "$FEATURES" ]; then
      if [ "$FIRST" = false ]; then
        echo "," >> "$OUTPUT_FILE"
      fi
      echo -n "$FEATURES" >> "$OUTPUT_FILE"
      FIRST=false
    fi
  fi
done

echo "]}}" >> "$OUTPUT_FILE"

echo "✓ Archivo final: $OUTPUT_FILE"
ls -lh "$OUTPUT_FILE"
grep -o '"type":"Feature"' "$OUTPUT_FILE" | wc -l | xargs echo "✓ Total de secciones:"

# Limpiar temp
rm -rf "$TEMP_DIR"