##############################################################################
# INELODApp — Makefile
# Orquesta todo el pipeline: normalización de CSV, CONSTRUCTs, validación,
# cálculo de indicadores, carga del KOS, API REST y servidor del visor.
#
# Uso:
#   make all              # Ejecuta todo el pipeline de datos
#   make api              # Levanta la API REST (producción)
#   make api-dev          # Levanta la API REST (desarrollo con reload)
#   make viewer           # Levanta el servidor del visor HTML
#   make dev              # Levanta API + visor simultáneamente
#   make clean            # Elimina ficheros generados
#   make help             # Muestra esta ayuda
##############################################################################

.PHONY: all clean clean-all help install-deps normalize construct indicators \
        api api-dev viewer dev serve check-deps check-api download-deps view-sample

# ── Variables ──────────────────────────────────────────────────────────────────
SHELL := /bin/bash
JAVA_OPTS := -Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8

# Rutas
DATA_RAW       := data/raw
DATA_CLEAN     := data/clean
DATA_GEO       := data/geo
BUILD          := build
SCRIPTS        := scripts
CONSTRUCT_DIR  := construct

# Herramientas
SPARQL_ANYTHING_VERSION := 1.1.0
SPARQL_ANYTHING_JAR := tools/sparql-anything/sparql-anything-v$(SPARQL_ANYTHING_VERSION).jar
SPARQL_ANYTHING_URL := https://github.com/SPARQL-Anything/sparql.anything/releases/download/v$(SPARQL_ANYTHING_VERSION)/sparql-anything-v$(SPARQL_ANYTHING_VERSION).jar

# Ficheros de entrada (CSV del INE)
CSV_31097  := $(DATA_RAW)/31097.csv
CSV_31105  := $(DATA_RAW)/31105.csv
CSV_37727  := $(DATA_RAW)/37727.csv
CSV_5      := $(DATA_RAW)/5.csv

# Ficheros limpios (UTF-8, sin BOM)
CSV_31097_CLEAN := $(DATA_CLEAN)/31097-clean.csv
CSV_31105_CLEAN := $(DATA_CLEAN)/31105-clean.csv
CSV_37727_CLEAN := $(DATA_CLEAN)/37727-clean.csv
CSV_5_CLEAN     := $(DATA_CLEAN)/5-clean.csv

# Ficheros TTL generados
TTL_31097       := $(BUILD)/31097.ttl
TTL_31105       := $(BUILD)/31105.ttl
TTL_37727       := $(BUILD)/37727.ttl
TTL_5_1         := $(BUILD)/5_1.ttl
TTL_5_2         := $(BUILD)/5_2.ttl
TTL_5_3         := $(BUILD)/5_3.ttl
TTL_5_4         := $(BUILD)/5_4.ttl
TTL_INDICADORES := $(BUILD)/indicadores.ttl

# KOS de distritos
KOS_DISTRITOS   := Mad_Distritos_KOS

# Cartografía
GEOJSON_MADRID  := $(DATA_GEO)/secciones_censales_madrid.geojson

# API
API_FILE        := api.py
API_MODULE      := api
API_HOST        := 0.0.0.0
API_PORT        := 8000

# Visor
VIEWER_FILE     := ineapp_viewer.html
VIEWER_PORT     := 8080


# ── Targets ────────────────────────────────────────────────────────────────────

help:
	@echo "INELODApp — Makefile"
	@echo ""
	@echo "Pipeline de datos:"
	@echo "  make all                 Ejecuta todo el pipeline de datos"
	@echo "  make normalize           Normaliza CSV (UTF-8, sin tildes)"
	@echo "  make construct           Genera Turtle de los cubos brutos"
	@echo "  make indicators          Calcula indicadores de gentrificación"
	@echo ""
	@echo "Virtuoso (carga manual de TTL):"
	@echo "  make load-instructions   Muestra los comandos de carga en Virtuoso"
	@echo ""
	@echo "API REST:"
	@echo "  make api                 Levanta API en producción (sin reload)"
	@echo "  make api-dev             Levanta API en desarrollo (con reload)"
	@echo "  make check-api           Verifica que la API está operativa"
	@echo ""
	@echo "Visor:"
	@echo "  make viewer              Levanta servidor del visor HTML (puerto $(VIEWER_PORT))"
	@echo "  make dev                 Levanta API + visor simultáneamente (con check-deps)
	@echo "  make serve               Levanta API + visor directamente (sin checks)"
	@echo ""
	@echo "Mantenimiento:"
	@echo "  make install-deps        Instala dependencias Python"
	@echo "  make download-deps       Descarga SPARQL-Anything"
	@echo "  make check-deps          Verifica todas las dependencias"
	@echo "  make clean               Elimina ficheros generados (data/clean, build)"
	@echo "  make clean-all           Limpieza completa (mantiene CSV originales)"
	@echo ""


all: normalize construct indicators
	@echo ""
	@echo "✓ Pipeline completado exitosamente"
	@echo ""
	@echo "Ficheros generados:"
	@echo "  Cubos ADRH:               $(TTL_31097) $(TTL_31105) $(TTL_37727)"
	@echo "  Cubo Viviendas Turísticas: $(TTL_5_1) $(TTL_5_2) $(TTL_5_3) $(TTL_5_4)"
	@echo "  Indicadores:              $(TTL_INDICADORES)"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. make load-instructions  # Ver comandos de carga en Virtuoso"
	@echo "  2. make dev                # Levanta API + visor"
	@echo ""


# ── 0. Instalación de dependencias ─────────────────────────────────────────────

install-deps:
	@echo "Instalando dependencias Python..."
	pip install rdflib numpy SPARQLWrapper fastapi uvicorn python-dotenv
	@echo "✓ Dependencias Python instaladas"


# ── 0b. Descarga de SPARQL-Anything ────────────────────────────────────────────

$(SPARQL_ANYTHING_JAR):
	@echo "Descargando SPARQL-Anything $(SPARQL_ANYTHING_VERSION)..."
	@mkdir -p tools/sparql-anything
	@which wget > /dev/null && wget -q -O $@ $(SPARQL_ANYTHING_URL) || \
	 which curl > /dev/null && curl -s -L -o $@ $(SPARQL_ANYTHING_URL) || \
	 (echo "❌ No se encontró wget ni curl" && exit 1)
	@if [ ! -s $@ ]; then \
		echo "❌ Error descargando SPARQL-Anything"; \
		rm -f $@; \
		exit 1; \
	fi
	@echo "✓ SPARQL-Anything descargado: $@"

download-deps: $(SPARQL_ANYTHING_JAR)
	@echo "✓ Todas las dependencias descargadas"


# ── 1. Normalización de CSV ────────────────────────────────────────────────────

$(DATA_CLEAN):
	mkdir -p $@

$(CSV_31097_CLEAN): $(CSV_31097) | $(DATA_CLEAN)
	@echo "Normalizando 31097..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_31097) $@ 31097

$(CSV_31105_CLEAN): $(CSV_31105) | $(DATA_CLEAN)
	@echo "Normalizando 31105..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_31105) $@ 31105

$(CSV_37727_CLEAN): $(CSV_37727) | $(DATA_CLEAN)
	@echo "Normalizando 37727..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_37727) $@ 37727

$(CSV_5_CLEAN): $(CSV_5) | $(DATA_CLEAN)
	@echo "Normalizando 5 (Viviendas Turísticas)..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_5) $@ 5

normalize: $(CSV_31097_CLEAN) $(CSV_31105_CLEAN) $(CSV_37727_CLEAN) $(CSV_5_CLEAN)
	@echo "✓ CSV normalizados"


# ── 2. Generación de Turtle con SPARQL-Anything ────────────────────────────────

$(BUILD):
	mkdir -p $@

$(TTL_31097): $(CSV_31097_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 31097..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/31097.sparql -f TTL > $@

$(TTL_31105): $(CSV_31105_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 31105..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/31105.sparql -f TTL > $@

$(TTL_37727): $(CSV_37727_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 37727..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/37727.sparql -f TTL > $@

$(TTL_5_1): $(CSV_5_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 5_1 (Viviendas turísticas)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/5_1.sparql -f TTL > $@

$(TTL_5_2): $(CSV_5_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 5_2 (Plazas)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/5_2.sparql -f TTL > $@

$(TTL_5_3): $(CSV_5_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 5_3 (Ratio plazas/vivienda)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/5_3.sparql -f TTL > $@

$(TTL_5_4): $(CSV_5_CLEAN) $(SPARQL_ANYTHING_JAR) | $(BUILD)
	@echo "CONSTRUCT 5_4 (%% viviendas turísticas)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/5_4.sparql -f TTL > $@

construct: $(TTL_31097) $(TTL_31105) $(TTL_37727) \
           $(TTL_5_1) $(TTL_5_2) $(TTL_5_3) $(TTL_5_4)
	@echo "✓ Turtle generados"


# ── 3. Cálculo de indicadores ──────────────────────────────────────────────────

$(TTL_INDICADORES): $(TTL_31097) $(TTL_31105) $(TTL_37727) \
                    $(TTL_5_1) $(TTL_5_2) $(TTL_5_3) $(TTL_5_4)
	@echo "Calculando indicadores..."
	python3 $(SCRIPTS)/calcular_indicadores.py
	@echo "✓ Indicadores calculados: $(TTL_INDICADORES)"

indicators: $(TTL_INDICADORES)


# ── 4. Instrucciones de carga en Virtuoso ──────────────────────────────────────
# Los TTL y el KOS se cargan manualmente en Virtuoso via isql o interfaz web.

load-instructions:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo " Carga en Virtuoso — comandos isql"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "1. Cubo de gentrificación (indicadores + SKOS):"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_31097)'),   '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_31105)'),   '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_37727)'),   '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_5_1)'),     '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_5_2)'),     '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_5_3)'),     '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_5_4)'),     '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(TTL_INDICADORES)'), '', 'http://lod.ine.es/recurso/cubes/gentrificacion');"
	@echo ""
	@echo "2. KOS de distritos:"
	@echo "   DB.DBA.TTLP_MT (file_to_string_output('$(KOS_DISTRITOS)'), '', 'http://lod.ine.es/kos/');"
	@echo ""
	@echo "3. Cartografía (secciones censales GeoJSON → RDF):"
	@echo "   Cargado en: http://lod.ine.es/recurso/cubes/secciones_censales"
	@echo "   Fichero fuente: $(GEOJSON_MADRID)"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""


# ── 5. API REST ────────────────────────────────────────────────────────────────

api: check-deps
	@echo "Levantando API REST en producción..."
	@echo "  URL:  http://$(API_HOST):$(API_PORT)"
	@echo "  Docs: http://$(API_HOST):$(API_PORT)/docs"
	@echo ""
	@echo "Ctrl+C para detener"
	uvicorn $(API_MODULE):app --host $(API_HOST) --port $(API_PORT)

api-dev: check-deps
	@echo "Levantando API REST en desarrollo (con reload automático)..."
	@echo "  URL:  http://$(API_HOST):$(API_PORT)"
	@echo "  Docs: http://$(API_HOST):$(API_PORT)/docs"
	@echo ""
	@echo "Los cambios en $(API_FILE) se recargarán automáticamente"
	@echo "Ctrl+C para detener"
	uvicorn $(API_MODULE):app --host $(API_HOST) --port $(API_PORT) --reload

check-api:
	@echo "Verificando que la API está operativa..."
	@curl -s http://$(API_HOST):$(API_PORT)/health | python3 -m json.tool || \
		(echo "❌ API no responde en http://$(API_HOST):$(API_PORT)" && exit 1)
	@echo "✓ API operativa"


# ── 6. Visor HTML ──────────────────────────────────────────────────────────────

viewer:
	@echo "Levantando servidor del visor HTML..."
	@echo "  URL:  http://localhost:$(VIEWER_PORT)/$(VIEWER_FILE)"
	@echo ""
	@echo "Asegúrate de que la API también está corriendo (make api o make api-dev)"
	@echo "Ctrl+C para detener"
	python3 -m http.server $(VIEWER_PORT)

# Levanta API (desarrollo) + visor en paralelo (incluye check-deps)
dev: check-deps

# Levanta API + visor sin verificar dependencias ni regenerar datos
serve:
	@echo "Levantando API REST + visor en paralelo..."
	@echo "  API:   http://$(API_HOST):$(API_PORT)"
	@echo "  Docs:  http://$(API_HOST):$(API_PORT)/docs"
	@echo "  Visor: http://localhost:$(VIEWER_PORT)/$(VIEWER_FILE)"
	@echo ""
	@echo "Ctrl+C para detener ambos procesos"
	@trap 'kill 0' INT; \
	 uvicorn $(API_MODULE):app --host $(API_HOST) --port $(API_PORT) --reload & \
	 python3 -m http.server $(VIEWER_PORT) & \
	 wait
	@echo "Levantando API REST + visor en paralelo..."
	@echo "  API:   http://$(API_HOST):$(API_PORT)"
	@echo "  Docs:  http://$(API_HOST):$(API_PORT)/docs"
	@echo "  Visor: http://localhost:$(VIEWER_PORT)/$(VIEWER_FILE)"
	@echo ""
	@echo "Ctrl+C para detener ambos procesos"
	@trap 'kill 0' INT; \
	 uvicorn $(API_MODULE):app --host $(API_HOST) --port $(API_PORT) --reload & \
	 python3 -m http.server $(VIEWER_PORT) & \
	 wait


# ── 7. Limpieza ────────────────────────────────────────────────────────────────

clean:
	@echo "Eliminando ficheros generados..."
	rm -rf $(DATA_CLEAN) $(BUILD)
	@echo "✓ Limpieza completada"

clean-all: clean
	@echo "✓ Limpieza completa (CSV originales del INE conservados)"


# ── 8. Verificación de requisitos ──────────────────────────────────────────────

check-deps: $(SPARQL_ANYTHING_JAR)
	@which java > /dev/null || (echo "❌ java no encontrado" && exit 1)
	@python3 --version 2>&1 | head -1
	@python3 -c "import fastapi"      2>/dev/null || (echo "❌ fastapi no instalado (make install-deps)" && exit 1)
	@python3 -c "import SPARQLWrapper" 2>/dev/null || (echo "❌ SPARQLWrapper no instalado (make install-deps)" && exit 1)
	@python3 -c "import uvicorn"      2>/dev/null || (echo "❌ uvicorn no instalado (make install-deps)" && exit 1)
	@echo "✓ Todas las dependencias disponibles"


# ── 9. Targets de debugging ────────────────────────────────────────────────────

view-sample: construct
	@echo "Primeras 20 líneas de 31097.ttl:"
	@head -20 $(TTL_31097)


.DEFAULT_GOAL := help
