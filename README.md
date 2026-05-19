# INELODApp — API REST

API REST para consultar indicadores de gentrificación a nivel de sección censal en Madrid.

## Instalación y Generación de los recursos de INEApp
Para la generación de los ttl que se usan para el cálculo de los indicadores de gentrificación se requiere tener descargados los siguientes ficheros en la carpeta  `data/raw`:  [31097.csv](https://www.ine.es/jaxiT3/Tabla.htm?t=31097&L=0), [31105.csv](https://www.ine.es/jaxiT3/Tabla.htm?t=31105&L=0), [37727.csv](https://www.ine.es/jaxiT3/Tabla.htm?t=37727&L=0), y la tabla 5 de la [medición del número de viviendas turísticas en España](https://www.ine.es/experimental/viv_turistica/exp_viv_turistica_tablas.htm).

### 1. Requisitos previos

- **Java 11+** (para SPARQL-Anything)
- **Apache Jena** (para `riot`)
- **Python 3.8+**
- **Virtuoso remoto** en https://stats.linkeddata.es/sparql con datos ya cargados

### 2. Instalar dependencias

```bash
make install-deps       # Instala dependencias Python
make download-deps      # Descarga SPARQL-Anything automáticamente
```

O ejecuta ambos:
```bash
make install-deps download-deps
```

### 3. Generar datos (si no lo has hecho ya)

```bash
# Coloca los CSV del INE en data/raw/
# - 31097.csv (ADRH - Renta)
# - 31105.csv (ADRH - Demografía)
# - 37727.csv (ADRH - Gini)
# - 5.csv (Viviendas turísticas)

make all
```

Los ficheros TTL generados estarán en `build/`. Cárgalos manualmente en Virtuoso:
- `build/31097.ttl`, `build/31105.ttl`, `build/37727.ttl` → grafo `http://lod.ine.es/recurso/cubes/adrh`
- `build/5_1.ttl`, `build/5_2.ttl`, `build/5_3.ttl`, `build/5_4.ttl` → grafo `http://lod.ine.es/recurso/cubes/viv-tur`
- `build/indicadores.ttl` → grafo `http://lod.ine.es/recurso/cubes/gentrificacion`

### 4. Levantar la API

**Desarrollo** (con reload automático):
```bash
make api-dev
```

**Producción**:
```bash
make api
```

La API estará disponible en `http://localhost:8000`.

## Documentación interactiva

Una vez levantada la API, accede a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints principales

### Indicadores

#### `GET /indicadores/madrid`
Obtiene todos los indicadores de todas las secciones censales de Madrid.

**Parámetros opcionales:**
- `indicador` — Filtrar por indicador específico: `I-01`, `I-02`, `I-03`, `I-04`
- `limit` — Número máximo de resultados (1-2500, default: 100)

**Ejemplo:**
```bash
curl "http://localhost:8000/indicadores/madrid?indicador=I-01&limit=20"
```

#### `GET /secciones/{cusec}`
Obtiene todos los indicadores de una sección censal específica.

**Parámetro:**
- `cusec` — Código de 10 dígitos de la sección censal (ej. 2807901001)

**Ejemplo:**
```bash
curl "http://localhost:8000/secciones/2807901001"
```

### Distritos

#### `GET /distritos/agregado`
Obtiene estadísticas agregadas (media de indicadores) para todos los distritos de Madrid, ordenados por I-01 (gentrificación) descendente.

**Ejemplo:**
```bash
curl "http://localhost:8000/distritos/agregado"
```

#### `GET /distritos/{codigo}`
Obtiene estadísticas agregadas de un distrito específico.

**Parámetro:**
- `codigo` — Código de 7 dígitos del distrito (ej. 2807901)

**Ejemplo:**
```bash
curl "http://localhost:8000/distritos/2807901"
```

### Utilidades

#### `GET /comparar`
Compara los indicadores de dos secciones censales.

**Parámetros:**
- `sec1` — CUSEC de la primera sección
- `sec2` — CUSEC de la segunda sección

**Ejemplo:**
```bash
curl "http://localhost:8000/comparar?sec1=2807901001&sec2=2807904001"
```

#### `GET /stats`
Obtiene estadísticas generales del cubo de indicadores: número de secciones, distritos, observaciones, y distribución del índice de gentrificación.

**Ejemplo:**
```bash
curl "http://localhost:8000/stats"
```

#### `GET /health`
Verifica que la API está operativa y conectada a Virtuoso.

**Ejemplo:**
```bash
curl "http://localhost:8000/health"
```

## Ejemplos de uso

### Python

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Obtener indicadores del Centro (distrito 2807901)
response = requests.get(f"{BASE_URL}/distritos/agregado")
data = response.json()
centro = [d for d in data if d["codigo"] == "2807901"][0]
print(f"Centro: I-01={centro['media_i01']:.2f}")

# Comparar dos secciones
response = requests.get(
    f"{BASE_URL}/comparar",
    params={"sec1": "2807901001", "sec2": "2807904001"}
)
data = response.json()
print(json.dumps(data, indent=2))
```

### JavaScript / cURL

```bash
# Obtener todas las secciones con I-01 > 75
curl "http://localhost:8000/indicadores/madrid?indicador=I-01" \
  | jq '.[] | select(.indicadores[0].valor > 75)'

# Top 5 distritos por gentrificación
curl "http://localhost:8000/distritos/agregado" \
  | jq '.[0:5]'
```

## Respuesta de ejemplo

```json
{
  "cusec": "2807901001",
  "label": "Sección 1 del Centro",
  "distrito_codigo": "2807901",
  "distrito_label": "Centro",
  "indicadores": [
    {
      "codigo": "I-01",
      "label": "Índice compuesto de gentrificación",
      "valor": 87.45
    },
    {
      "codigo": "I-02",
      "label": "Variación renta 2020→2023",
      "valor": 72.34
    },
    {
      "codigo": "I-03",
      "label": "Variación Gini 2020→2023",
      "valor": 65.21
    },
    {
      "codigo": "I-04",
      "label": "% viviendas turísticas",
      "valor": 58.90
    }
  ]
}
```

## Configuración

La API se conecta a Virtuoso en `https://stats.linkeddata.es/sparql`. Para cambiar el endpoint, edita la variable `VIRTUOSO_ENDPOINT` en `api.py`:

```python
VIRTUOSO_ENDPOINT = "https://stats.linkeddata.es/sparql"
# O si usas otro endpoint:
VIRTUOSO_ENDPOINT = "http://tu-servidor:8890/sparql"
```

## Errores comunes

### "Virtuoso no accesible"
- Verifica que Virtuoso remoto está disponible: `curl https://stats.linkeddata.es/sparql`
- Comprueba que tienes conexión a internet
- Verifica que los datos están cargados en los grafos correctos en el servidor remoto

### "Sección censal no encontrada"
- Verifica que el CUSEC tiene 10 dígitos
- Comprueba que es una sección de Madrid (comienza con `28079`)

### "No se encontraron indicadores"
- Verifica que los indicadores están calculados en `build/indicadores-gentrificacion.ttl`
- Asegúrate de que el fichero se cargó en el grafo `http://lod.ine.es/recurso/cubes/gentrificacion`

## Desarrollo

Para añadir nuevos endpoints:

1. Define el modelo Pydantic (ej. `class MiRespuesta(BaseModel)`)
2. Escribe la función con decorador `@app.get()` o `@app.post()`
3. Usa `query_virtuoso()` para ejecutar SPARQL
4. Retorna el modelo Pydantic

Ejemplo:

```python
@app.get("/mi-endpoint", response_model=MiRespuesta, tags=["MiCategoria"])
async def mi_endpoint(param: str = Query(..., description="Mi parámetro")):
    """Descripción del endpoint."""
    query = """
    PREFIX ...
    SELECT ...
    WHERE { ... }
    """
    results = query_virtuoso(query)
    # Procesar resultados
    return MiRespuesta(...)
```
## Equipo

- Diego Conde Herreros
- Luis M. Vilches-Blázquez
- Óscar Corcho

Ontology Engineering Group — ETSI Informáticos, Universidad Politécnica de Madrid.
