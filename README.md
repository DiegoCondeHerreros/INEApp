# INELODApp

Visor web y API REST para consultar indicadores de gentrificación a nivel de sección censal en el municipio de Madrid. Período de análisis: **2020–2023**.

Proyecto desarrollado en el marco de la colaboración entre el **Ontology Engineering Group (UPM)** y el **Instituto Nacional de Estadística (INE)**, como parte de la iniciativa INE-LinkedStats.

---

## Arquitectura

```
Virtuoso (stats.linkeddata.es)
  ├── http://lod.ine.es/recurso/cubes/gentrificacion   ← Indicadores + SKOS territorial
  ├── http://lod.ine.es/recurso/cubes/secciones_censales ← Geometrías GeoJSON (INE 2025)
  └── http://lod.ine.es/kos/                           ← KOS de distritos de Madrid
        ↓ SPARQL federado
      api.py  (FastAPI, puerto 8000)
        ↓ REST
      ineapp_viewer.html  (Leaflet, puerto 8080)
```

Los datos están publicados como **Linked Open Data** siguiendo el estándar RDF Data Cube (QB), accesibles mediante SPARQL.

---

## Instalación y generación de recursos

### Requisitos previos

- **Java 11+** (para SPARQL-Anything)
- **Python 3.8+**
- Acceso a **Virtuoso remoto** en `https://stats.linkeddata.es/sparql`

### 1. Instalar dependencias

```bash
make install-deps       # Instala dependencias Python
make download-deps      # Descarga SPARQL-Anything automáticamente
```

O ambos a la vez:

```bash
make install-deps download-deps
```

### 2. Preparar datos de entrada

Descarga los siguientes ficheros del INE y colócalos en `data/raw/`:

| Fichero | Descripción | Enlace |
|---------|-------------|--------|
| `31097.csv` | ADRH — Renta neta media por persona | [INE 31097](https://www.ine.es/jaxiT3/Tabla.htm?t=31097&L=0) |
| `31105.csv` | ADRH — Demografía | [INE 31105](https://www.ine.es/jaxiT3/Tabla.htm?t=31105&L=0) |
| `37727.csv` | ADRH — Índice de Gini | [INE 37727](https://www.ine.es/jaxiT3/Tabla.htm?t=37727&L=0) |
| `5.csv` | Viviendas de Uso Turístico (tabla 5) | [INE VUT](https://www.ine.es/experimental/viv_turistica/exp_viv_turistica_tablas.htm) |

### 3. Ejecutar el pipeline

```bash
make all
```

Genera los ficheros TTL en `build/`. Ver los comandos exactos de carga en Virtuoso:

```bash
make load-instructions
```

Los tres grafos que deben estar cargados en Virtuoso:

| Grafo | Contenido | Ficheros |
|-------|-----------|---------|
| `http://lod.ine.es/recurso/cubes/gentrificacion` | Cubos ADRH + VUT + indicadores calculados + SKOS territorial | `build/*.ttl` |
| `http://lod.ine.es/recurso/cubes/secciones_censales` | Geometrías de secciones censales (GeoServer INE 2025) | `data/geo/secciones_censales_madrid.geojson` → RDF |
| `http://lod.ine.es/kos/` | KOS de distritos de Madrid | `Mad_Distritos_KOS` |

> **Nota sobre la cartografía**: Las geometrías se obtienen del GeoServer del INE mediante la API OGC Features, y se transforman a formato ttl mediante el uso de un [morphgeo](https://github.com/isaacnoya/tfm/tree/main/moprhgeo). El fichero `data/geo/municipio_madrid.ttl` contiene las secciones del municipio de Madrid (CMUN=079) con el campo `CUSEC` como identificador.

### 4. Levantar los servicios

**Desarrollo — API + visor simultáneamente (recomendado):**

```bash
make serve
```

Esto lanza en paralelo:
- API REST en `http://localhost:8000`
- Servidor del visor en `http://localhost:8080/ineapp_viewer.html`

Ctrl+C detiene ambos procesos.

**Por separado:**

```bash
make api-dev    # API con reload automático (desarrollo)
make api        # API sin reload (producción)
make viewer     # Solo el servidor del visor HTML
```

---

## Visor

El fichero `ineapp_viewer.html` es el visor cartográfico. Accede a él en:

```
http://localhost:8080/ineapp_viewer.html
```

**Funcionalidades:**

- **Vista Secciones**: mapa coroplético de ~2.100 secciones censales del municipio de Madrid, coloreadas según el índice I-01. Filtros: Todos / Alto (I-01 ≥ 50) / Bajo (I-01 < 50).
- **Vista Distritos**: agrega los indicadores por distrito, construyendo un MultiPolygon real por distrito. Muestra los 4 indicadores medios al hacer clic.
- **Panel lateral**: al seleccionar una sección o distrito muestra los 4 indicadores con barras de progreso.
- **Pestaña Metodología**: descripción del período de análisis, fuentes de datos, fórmulas de cálculo, normalización y consideraciones.

**Escala de color (I-01):**

| Rango | Clasificación |
|-------|---------------|
| 0–25 | Bajo |
| 25–50 | Medio-Bajo |
| 50–75 | Medio-Alto |
| 75–88 | Alto |
| 88–100 | Muy Alto |

---

## API REST

Documentación interactiva disponible en:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints

#### `GET /indicadores/madrid`
Indicadores de gentrificación para todas las secciones censales de Madrid.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `indicador` | string | Filtrar por indicador: `I-01`, `I-02`, `I-03`, `I-04` |
| `limit` | int | Máximo de resultados (1–2500, default: 100) |

```bash
curl "http://localhost:8000/indicadores/madrid?indicador=I-01&limit=20"
```

#### `GET /secciones/geo/madrid`
Geometría GeoJSON + los 4 indicadores por sección censal en una única consulta SPARQL federada. Endpoint principal del visor.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `limit` | int | Máximo de resultados (1–2500, default: 2500) |

```bash
curl "http://localhost:8000/secciones/geo/madrid?limit=100"
```

#### `GET /secciones/{cusec}`
Todos los indicadores de una sección censal específica.

```bash
curl "http://localhost:8000/secciones/2807901001"
```

#### `GET /distritos/agregado`
Media de indicadores para todos los distritos de Madrid, ordenados por I-01 descendente.

```bash
curl "http://localhost:8000/distritos/agregado"
```

#### `GET /distritos/{codigo}`
Estadísticas agregadas de un distrito específico.

```bash
curl "http://localhost:8000/distritos/2807901"
```

#### `GET /comparar`
Compara los indicadores de dos secciones censales.

| Parámetro | Descripción |
|-----------|-------------|
| `sec1` | CUSEC de la primera sección |
| `sec2` | CUSEC de la segunda sección |

```bash
curl "http://localhost:8000/comparar?sec1=2807901001&sec2=2807904001"
```

#### `GET /stats`
Estadísticas generales: número de secciones, distritos, observaciones y distribución del I-01.

```bash
curl "http://localhost:8000/stats"
```

#### `GET /health`
Verifica conectividad con Virtuoso.

```bash
curl "http://localhost:8000/health"
```

### Respuesta de ejemplo (`/secciones/geo/madrid`)

```json
{
  "cusec": "2807901001",
  "label": "Sección 1 del Centro",
  "distrito_label": "Centro",
  "i01": 87.45,
  "i02": 72.34,
  "i03": 65.21,
  "i04": 58.90,
  "geometria": "{'type': 'MultiPolygon', 'coordinates': [...]}"
}
```

---

## Configuración

La API se conecta a Virtuoso en `https://stats.linkeddata.es/sparql`. Para cambiar el endpoint, edita `api.py`:

```python
VIRTUOSO_ENDPOINT = "https://stats.linkeddata.es/sparql"
```

Los grafos están definidos como constantes en `api.py`:

```python
GRAFO_DATOS = "http://lod.ine.es/recurso/cubes/gentrificacion"
GRAFO_GEO   = "http://lod.ine.es/recurso/cubes/secciones_censales"
GRAFO_KOS   = "http://lod.ine.es/kos/"
```

---

## Referencia del Makefile

| Comando | Descripción |
|---------|-------------|
| `make all` | Pipeline completo: normalizar → construir TTL → calcular indicadores |
| `make normalize` | Normaliza CSV (UTF-8, sin BOM) |
| `make construct` | Genera TTL con SPARQL-Anything |
| `make indicators` | Calcula indicadores de gentrificación |
| `make load-instructions` | Muestra comandos isql para cargar datos en Virtuoso |
| `make serve` | **Lanza API + visor en paralelo** (uso habitual) |
| `make api-dev` | Solo API con reload automático |
| `make api` | Solo API en producción |
| `make viewer` | Solo servidor del visor HTML (puerto 8080) |
| `make dev` | API + visor con verificación previa de dependencias |
| `make install-deps` | Instala dependencias Python |
| `make download-deps` | Descarga SPARQL-Anything |
| `make check-deps` | Verifica dependencias |
| `make check-api` | Verifica que la API responde |
| `make clean` | Elimina `data/clean/` y `build/` |

---

## Errores comunes

**`Virtuoso no accesible`**
- Verifica conectividad: `curl https://stats.linkeddata.es/sparql`
- Comprueba que los tres grafos están cargados en Virtuoso

**`Sección censal no encontrada`**
- El CUSEC debe tener 10 dígitos
- Las secciones del municipio de Madrid comienzan por `28079`

**`Error al cargar geometrías` en el visor**
- Asegúrate de lanzar el visor con `make serve` o `make viewer` desde la raíz del proyecto
- El visor debe servirse por HTTP, no abrirse como fichero local (`file://`)
- Verifica que la API está corriendo en el puerto 8000

**`Could not import module "api.py"` en uvicorn**
- Uvicorn espera el nombre del módulo sin extensión. Usa `make api-dev` o `make serve` en lugar de llamar a uvicorn directamente con `api.py`

---

## Desarrollo

Para añadir nuevos endpoints a `api.py`:

1. Define el modelo Pydantic
2. Escribe la función con decorador `@app.get()`
3. Usa `query_virtuoso()` para ejecutar SPARQL
4. Retorna el modelo Pydantic

```python
@app.get("/mi-endpoint", response_model=MiRespuesta, tags=["MiCategoria"])
async def mi_endpoint(param: str = Query(..., description="Mi parámetro")):
    query = f"""
    PREFIX ine: <{INE}>
    SELECT ...
    WHERE {{ ... }}
    """
    results = query_virtuoso(query)
    return MiRespuesta(...)
```

---

## Equipo

- Diego Conde Herreros
- Luis M. Vilches-Blázquez
- Óscar Corcho

**Ontology Engineering Group** — ETSI Informáticos, Universidad Politécnica de Madrid.
