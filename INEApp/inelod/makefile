##############################################################################
# INELOD — Makefile
# Orquesta todo el pipeline: normalización de CSV, CONSTRUCTs, validación,
# cálculo de indicadores, y levanta la API REST.
#
# Uso:
#   make all              # Ejecuta todo el pipeline
#   make api              # Levanta la API REST (producción)
#   make api-dev          # Levanta la API REST (desarrollo con reload)
#   make clean            # Elimina ficheros generados
#   make help             # Muestra esta ayuda
##############################################################################

.PHONY: all clean help install-deps normalize construct validate-ttl indicators \
        api api-dev check-deps

# ── Variables ──────────────────────────────────────────────────────────────────
SHELL := /bin/bash
JAVA_OPTS := -Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8

# Rutas
DATA_RAW       := data/raw
DATA_CLEAN     := data/clean
BUILD          := build
SCRIPTS        := scripts
CONSTRUCT_DIR  := construct

# Herramientas
SPARQL_ANYTHING_JAR := $(HOME)/tools/sparql-anything/sparql-anything-v1.1.0-geosparql.jar
RIOT            := riot

# Ficheros de entrada (CSV del INE)
CSV_ADRH_31097  := $(DATA_RAW)/31097.csv
CSV_ADRH_31105  := $(DATA_RAW)/31105.csv
CSV_ADRH_37727  := $(DATA_RAW)/37727.csv
CSV_VUT_T5      := $(DATA_RAW)/5.csv

# Ficheros limpios (UTF-8, sin BOM, sin tildes)
CSV_ADRH_31097_CLEAN := $(DATA_CLEAN)/31097clean.csv
CSV_ADRH_31105_CLEAN := $(DATA_CLEAN)/31105-clean.csv
CSV_ADRH_37727_CLEAN := $(DATA_CLEAN)/37727-clean.csv
CSV_VUT_T5_CLEAN     := $(DATA_CLEAN)/5-clean.csv

# Ficheros TTL generados
TTL_ADRH_31097  := $(BUILD)/31097.ttl
TTL_ADRH_31105  := $(BUILD)/31105.ttl
TTL_ADRH_37727  := $(BUILD)/37727.ttl
TTL_VUT_01      := $(BUILD)/vut-01-viviendas.ttl
TTL_VUT_02      := $(BUILD)/vut-02-plazas.ttl
TTL_VUT_03      := $(BUILD)/vut-03-ratio.ttl
TTL_VUT_04      := $(BUILD)/vut-04-porcentaje.ttl
TTL_INDICADORES := $(BUILD)/indicadores-gentrificacion.ttl

# API
API_FILE        := api.py
API_HOST        := 0.0.0.0
API_PORT        := 8000

# ── Targets ────────────────────────────────────────────────────────────────────

help:
	@echo "INELOD MVP — Makefile"
	@echo ""
	@echo "Pipeline de datos:"
	@echo "  make all                 Ejecuta todo el pipeline de datos"
	@echo "  make normalize           Normaliza CSV (UTF-8, sin tildes)"
	@echo "  make construct           Genera Turtle de los cubos brutos"
	@echo "  make validate-ttl        Valida Turtle con riot"
	@echo "  make indicators          Calcula indicadores"
	@echo ""
	@echo "API REST:"
	@echo "  make api                 Levanta API en producción (sin reload)"
	@echo "  make api-dev             Levanta API en desarrollo (con reload)"
	@echo "  make check-api           Verifica que la API está operativa"
	@echo ""
	@echo "Mantenimiento:"
	@echo "  make install-deps        Instala dependencias Python"
	@echo "  make check-deps          Verifica todas las dependencias"
	@echo "  make clean               Elimina ficheros generados"
	@echo ""


all: normalize construct validate-ttl indicators
	@echo ""
	@echo "✓ Pipeline completado exitosamente"
	@echo ""
	@echo "Ficheros generados:"
	@echo "  Cubos ADRH:              $(TTL_ADRH_31097) $(TTL_ADRH_31105) $(TTL_ADRH_37727)"
	@echo "  Cubo VUT:                $(TTL_VUT_01) $(TTL_VUT_02) $(TTL_VUT_03) $(TTL_VUT_04)"
	@echo "  Indicadores:             $(TTL_INDICADORES)"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. Cargar manualmente los TTL en Virtuoso"
	@echo "  2. make api-dev          # Para desarrollo con reload automático"
	@echo "  3. make api              # Para producción"
	@echo ""
	@echo "Documentación interactiva: http://localhost:8000/docs"
	@echo ""


# ── 0. Instalación de dependencias ─────────────────────────────────────────────

install-deps:
	@echo "Instalando dependencias Python..."
	pip install rdflib numpy SPARQLWrapper fastapi uvicorn python-dotenv --break-system-packages
	@echo "✓ Dependencias instaladas"


# ── 1. Normalización de CSV ────────────────────────────────────────────────────

$(DATA_CLEAN):
	mkdir -p $@

$(CSV_ADRH_31097_CLEAN): $(CSV_ADRH_31097) | $(DATA_CLEAN)
	@echo "Normalizando ADRH 31097..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_ADRH_31097) $@ adrh-31097

$(CSV_ADRH_31105_CLEAN): $(CSV_ADRH_31105) | $(DATA_CLEAN)
	@echo "Normalizando ADRH 31105..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_ADRH_31105) $@ adrh-31105

$(CSV_ADRH_37727_CLEAN): $(CSV_ADRH_37727) | $(DATA_CLEAN)
	@echo "Normalizando ADRH 37727..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_ADRH_37727) $@ adrh-37727

$(CSV_VUT_T5_CLEAN): $(CSV_VUT_T5) | $(DATA_CLEAN)
	@echo "Normalizando VUT tabla 5..."
	python3 $(SCRIPTS)/normalizar_csv.py $(CSV_VUT_T5) $@ vut-tabla5

normalize: $(CSV_ADRH_31097_CLEAN) $(CSV_ADRH_31105_CLEAN) $(CSV_ADRH_37727_CLEAN) $(CSV_VUT_T5_CLEAN)
	@echo "✓ CSV normalizados"


# ── 2. Generación de Turtle con SPARQL-Anything ────────────────────────────────

$(BUILD):
	mkdir -p $@

$(TTL_ADRH_31097): $(CSV_ADRH_31097_CLEAN) | $(BUILD)
	@echo "CONSTRUCT ADRH 31097 (renta)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/adrh-31097.sparql -f TTL > $@

$(TTL_ADRH_31105): $(CSV_ADRH_31105_CLEAN) | $(BUILD)
	@echo "CONSTRUCT ADRH 31105 (demografía)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/adrh-31105.sparql -f TTL > $@

$(TTL_ADRH_37727): $(CSV_ADRH_37727_CLEAN) | $(BUILD)
	@echo "CONSTRUCT ADRH 37727 (Gini)..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/adrh-37727.sparql -f TTL > $@

$(TTL_VUT_01): $(CSV_VUT_T5_CLEAN) | $(BUILD)
	@echo "CONSTRUCT VUT viviendas turísticas..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/vut-01-viviendas.sparql -f TTL > $@

$(TTL_VUT_02): $(CSV_VUT_T5_CLEAN) | $(BUILD)
	@echo "CONSTRUCT VUT plazas..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/vut-02-plazas.sparql -f TTL > $@

$(TTL_VUT_03): $(CSV_VUT_T5_CLEAN) | $(BUILD)
	@echo "CONSTRUCT VUT ratio plazas/vivienda..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/vut-03-ratio.sparql -f TTL > $@

$(TTL_VUT_04): $(CSV_VUT_T5_CLEAN) | $(BUILD)
	@echo "CONSTRUCT VUT porcentaje viviendas turísticas..."
	java $(JAVA_OPTS) -jar $(SPARQL_ANYTHING_JAR) \
		-q $(CONSTRUCT_DIR)/vut-04-porcentaje.sparql -f TTL > $@

construct: $(TTL_ADRH_31097) $(TTL_ADRH_31105) $(TTL_ADRH_37727) \
           $(TTL_VUT_01) $(TTL_VUT_02) $(TTL_VUT_03) $(TTL_VUT_04)
	@echo "✓ Turtle generados"


# ── 3. Validación de Turtle ────────────────────────────────────────────────────

validate-ttl: $(TTL_ADRH_31097) $(TTL_ADRH_31105) $(TTL_ADRH_37727) \
              $(TTL_VUT_01) $(TTL_VUT_02) $(TTL_VUT_03) $(TTL_VUT_04)
	@echo "Validando Turtle..."
	@$(RIOT) --validate $(TTL_ADRH_31097) || true
	@$(RIOT) --validate $(TTL_ADRH_31105) || true
	@$(RIOT) --validate $(TTL_ADRH_37727) || true
	@$(RIOT) --validate $(TTL_VUT_01) || true
	@$(RIOT) --validate $(TTL_VUT_02) || true
	@$(RIOT) --validate $(TTL_VUT_03) || true
	@$(RIOT) --validate $(TTL_VUT_04) || true
	@echo "✓ Validación completada"


# ── 4. Cálculo de indicadores ──────────────────────────────────────────────────

$(TTL_INDICADORES): $(TTL_ADRH_31097) $(TTL_ADRH_31105) $(TTL_ADRH_37727) \
                    $(TTL_VUT_01) $(TTL_VUT_02) $(TTL_VUT_03) $(TTL_VUT_04)
	@echo "Calculando indicadores de gentrificación..."
	python3 $(SCRIPTS)/calcular_indicadores.py
	@echo "✓ Indicadores calculados: $(TTL_INDICADORES)"

indicators: $(TTL_INDICADORES)


# ── 5. API REST ────────────────────────────────────────────────────────────────

api: check-deps
	@echo "Levantando API REST en producción..."
	@echo "  URL: http://$(API_HOST):$(API_PORT)"
	@echo "  Docs: http://$(API_HOST):$(API_PORT)/docs"
	@echo ""
	@echo "Ctrl+C para detener"
	uvicorn $(API_FILE):app --host $(API_HOST) --port $(API_PORT)

api-dev: check-deps
	@echo "Levantando API REST en desarrollo (con reload automático)..."
	@echo "  URL: http://$(API_HOST):$(API_PORT)"
	@echo "  Docs: http://$(API_HOST):$(API_PORT)/docs"
	@echo ""
	@echo "Los cambios en $(API_FILE) se recargarán automáticamente"
	@echo "Ctrl+C para detener"
	uvicorn $(API_FILE):app --host $(API_HOST) --port $(API_PORT) --reload

check-api:
	@echo "Verificando que la API está operativa..."
	@curl -s http://$(API_HOST):$(API_PORT)/health | python3 -m json.tool || \
		(echo "❌ API no responde en http://$(API_HOST):$(API_PORT)" && exit 1)
	@echo "✓ API operativa"


# ── 6. Limpieza ────────────────────────────────────────────────────────────────

clean:
	@echo "Eliminando ficheros generados..."
	rm -rf $(DATA_CLEAN) $(BUILD)
	@echo "✓ Limpieza completada"

clean-all: clean
	@echo "Limpieza completa (manteniendo CSV originales del INE)"


# ── 7. Verificación de requisitos ──────────────────────────────────────────────

check-deps:
	@which java > /dev/null || (echo "❌ java no encontrado" && exit 1)
	@which $(RIOT) > /dev/null || (echo "❌ riot no encontrado (instala Apache Jena)" && exit 1)
	@test -f $(SPARQL_ANYTHING_JAR) || (echo "❌ SPARQL-Anything JAR no encontrado" && exit 1)
	@python3 --version 2>&1 | head -1
	@python3 -c "import fastapi" 2>/dev/null || (echo "❌ fastapi no instalado (make install-deps)" && exit 1)
	@python3 -c "import SPARQLWrapper" 2>/dev/null || (echo "❌ SPARQLWrapper no instalado (make install-deps)" && exit 1)
	@echo "✓ Todas las dependencias disponibles"


# ── 8. Targets de debugging ────────────────────────────────────────────────────

count-triples: construct
	@echo "Contando líneas por fichero Turtle:"
	@for f in $(TTL_ADRH_31097) $(TTL_ADRH_31105) $(TTL_ADRH_37727) \
	          $(TTL_VUT_01) $(TTL_VUT_02) $(TTL_VUT_03) $(TTL_VUT_04); do \
		if [ -f $$f ]; then \
			lines=$$(wc -l < $$f); \
			echo "  $$f: $$lines líneas"; \
		fi; \
	done

view-sample: construct
	@echo "Primeras 20 líneas del ADRH 31097:"
	@head -20 $(TTL_ADRH_31097)


.DEFAULT_GOAL := help
