#!/usr/bin/env python3
"""
API REST FastAPI para INELODApp.
Consulta indicadores de gentrificación y datos territoriales desde Virtuoso.

Uso:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

Documentación interactiva:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from SPARQLWrapper import SPARQLWrapper, JSON
import logging

# ── Configuración ──────────────────────────────────────────────────────────
VIRTUOSO_ENDPOINT = "https://stats.linkeddata.es/sparql"

# Namespaces
INE      = "http://lod.ine.es/def/vocabulary/"
IND_BASE = "http://lod.ine.es/recurso/indicadores/gentrificacion/"
OGC      = "http://www.ogc.org/"
GEO      = "http://www.opengis.net/ont/geosparql#"

# Grafos
GRAFO_DATOS = "http://lod.ine.es/recurso/cubes/gentrificacion"
GRAFO_GEO   = "http://lod.ine.es/recurso/cubes/secciones_censales"
GRAFO_KOS   = "http://lod.ine.es/kos/"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(
    title="INELODApp API",
    description="API REST para consultar indicadores de gentrificación a nivel de sección censal en Madrid",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos Pydantic ───────────────────────────────────────────────────────
class Indicador(BaseModel):
    codigo: str
    label: str
    valor: float


class SeccionCensal(BaseModel):
    cusec: str
    label: str
    distrito_codigo: str
    distrito_label: str
    indicadores: List[Indicador]


class SeccionGeo(BaseModel):
    cusec:          str
    label:          str
    distrito_label: str
    i01:            Optional[float]
    i02:            Optional[float]
    i03:            Optional[float]
    i04:            Optional[float]
    geometria:      str   # GeoJSON como string


class DistritoAgregado(BaseModel):
    codigo:       str
    label:        str
    media_i01:    float
    media_i02:    float
    media_i03:    float
    media_i04:    float
    num_secciones: int


class ComparacionSecciones(BaseModel):
    seccion1: SeccionCensal
    seccion2: SeccionCensal


# ── Helpers ────────────────────────────────────────────────────────────────
def query_virtuoso(query: str) -> List[dict]:
    """Ejecuta una consulta SPARQL contra Virtuoso."""
    try:
        sw = SPARQLWrapper(VIRTUOSO_ENDPOINT)
        sw.setQuery(query)
        sw.setReturnFormat(JSON)
        sw.setTimeout(30)  # 30 segundos máximo
        results = sw.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logger.error(f"Error consultando Virtuoso: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando Virtuoso: {str(e)}")


def format_uri(uri: str) -> str:
    """Extrae la parte local de una URI."""
    return uri.split("/")[-1]


def fval(row: dict, key: str) -> Optional[float]:
    """Extrae float de un binding SPARQL o devuelve None."""
    v = row.get(key)
    return float(v["value"]) if v and v.get("value") else None


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Raíz"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "nombre": "INELODApp API",
        "versión": "0.2.0",
        "descripción": "API REST para indicadores de gentrificación en Madrid",
        "endpoints": {
            "indicadores_madrid":  "/indicadores/madrid",
            "sección_censal":      "/secciones/{cusec}",
            "secciones_geo":       "/secciones/geo/madrid",
            "distritos_agregado":  "/distritos/agregado",
            "distrito":            "/distritos/{codigo}",
            "comparar":            "/comparar?sec1=...&sec2=...",
            "stats":               "/stats",
            "health":              "/health"
        },
        "docs": "/docs"
    }


# ── Secciones ──────────────────────────────────────────────────────────────

@app.get("/indicadores/madrid", response_model=List[SeccionCensal], tags=["Indicadores"])
async def indicadores_madrid(
    indicador: Optional[str] = Query(None, description="Filtrar por indicador (I-01, I-02, I-03, I-04)"),
    limit: int = Query(100, description="Límite de resultados", ge=1, le=2500)
):
    """
    Obtiene los indicadores de gentrificación para todas las secciones censales de Madrid.
    Opcionalmente filtrado por indicador específico.
    Los nombres de distrito se resuelven desde el KOS.
    """
    indicador_filter = ""
    if indicador:
        indicador_filter = f'FILTER (STRSTARTS(STR(?ind), "{IND_BASE}{indicador}"))'

    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?sec_uri ?sec_label ?dist_uri ?dist_notation ?dist_label ?ind ?ind_label ?valor
WHERE {{
  GRAPH <{GRAFO_DATOS}> {{
    ?obs qb:dataSet <{GRAFO_DATOS}> ;
         ine:censusSection ?sec_uri ;
         ine:indicator ?ind ;
         ine:gentrificationIndex ?valor .

    ?sec_uri skos:prefLabel ?sec_label ;
             skos:broader ?dist_uri .

    ?dist_uri skos:notation ?dist_notation .

    BIND (IF(?ind = ind:I-01, "Índice compuesto de gentrificación",
        IF(?ind = ind:I-02, "Variación renta 2020→2023",
        IF(?ind = ind:I-03, "Variación Gini 2020→2023",
        IF(?ind = ind:I-04, "% viviendas turísticas",
                           "Desconocido")))) AS ?ind_label)
    {indicador_filter}
  }}

  # Nombre legible del distrito desde el KOS
  OPTIONAL {{
    GRAPH <{GRAFO_KOS}> {{
      ?kos_dist skos:notation ?dist_notation ;
                skos:prefLabel ?dist_label .
      FILTER(LANG(?dist_label) = "es")
    }}
  }}
}}
ORDER BY ?sec_uri
LIMIT {limit}
"""
    results = query_virtuoso(query)

    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron indicadores")

    secciones_dict = {}
    for row in results:
        sec_uri      = row["sec_uri"]["value"]
        cusec        = format_uri(sec_uri)
        sec_label    = row["sec_label"]["value"]
        dist_codigo  = format_uri(row["dist_uri"]["value"])
        dist_label   = row.get("dist_label", {}).get("value") or row.get("dist_notation", {}).get("value", dist_codigo)
        ind_codigo   = format_uri(row["ind"]["value"])
        ind_label    = row["ind_label"]["value"]
        valor        = float(row["valor"]["value"])

        if cusec not in secciones_dict:
            secciones_dict[cusec] = {
                "cusec": cusec, "label": sec_label,
                "distrito_codigo": dist_codigo, "distrito_label": dist_label,
                "indicadores": []
            }
        secciones_dict[cusec]["indicadores"].append({
            "codigo": ind_codigo, "label": ind_label, "valor": valor
        })

    return [SeccionCensal(**v) for v in secciones_dict.values()]


@app.get("/secciones/geo/madrid", response_model=List[SeccionGeo], tags=["Geo"])
async def secciones_geo_madrid(
    limit: int = Query(2500, description="Límite de resultados", ge=1, le=2500)
):
    """
    Devuelve geometría (GeoJSON) + los 4 indicadores de gentrificación
    para cada sección censal de Madrid, con nombre de distrito legible desde el KOS.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>
PREFIX ogc:  <{OGC}>
PREFIX geo:  <{GEO}>

SELECT ?cusec ?sec_label ?dist_notation ?dist_label ?geometria
       (MAX(?_i01) AS ?i01) (MAX(?_i02) AS ?i02)
       (MAX(?_i03) AS ?i03) (MAX(?_i04) AS ?i04)
WHERE {{
  GRAPH <{GRAFO_DATOS}> {{
    ?sec_uri skos:notation ?cusec ;
             skos:prefLabel ?sec_label ;
             skos:broader ?dist_uri .

    ?dist_uri skos:notation ?dist_notation .

    ?obs ine:censusSection ?sec_uri ;
         ine:indicator ?ind ;
         ine:gentrificationIndex ?valor .

    BIND (IF(?ind = ind:I-01, ?valor, ?undef) AS ?_i01)
    BIND (IF(?ind = ind:I-02, ?valor, ?undef) AS ?_i02)
    BIND (IF(?ind = ind:I-03, ?valor, ?undef) AS ?_i03)
    BIND (IF(?ind = ind:I-04, ?valor, ?undef) AS ?_i04)
  }}

  GRAPH <{GRAFO_GEO}> {{
    ?geo_sec ogc:CUSEC ?cusec ;
             geo:hasGeometry ?geometria .
  }}

  # Nombre legible del distrito desde el KOS
  OPTIONAL {{
    GRAPH <{GRAFO_KOS}> {{
      ?kos_dist skos:notation ?dist_notation ;
                skos:prefLabel ?dist_label .
      FILTER(LANG(?dist_label) = "es")
    }}
  }}
}}
GROUP BY ?cusec ?sec_label ?dist_notation ?dist_label ?geometria
ORDER BY ?cusec
LIMIT {limit}
"""
    results = query_virtuoso(query)

    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron secciones con geometría")

    secciones = []
    for row in results:
        dist_label = (
            row.get("dist_label", {}).get("value")
            or row.get("dist_notation", {}).get("value", "")
        )
        secciones.append(SeccionGeo(
            cusec          = row["cusec"]["value"],
            label          = row["sec_label"]["value"],
            distrito_label = dist_label,
            i01            = fval(row, "i01"),
            i02            = fval(row, "i02"),
            i03            = fval(row, "i03"),
            i04            = fval(row, "i04"),
            geometria      = row["geometria"]["value"]
        ))

    return secciones


@app.get("/secciones/{cusec}", response_model=SeccionCensal, tags=["Secciones"])
async def obtener_seccion(cusec: str):
    """Obtiene todos los indicadores de una sección censal específica."""
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?sec_label ?dist_uri ?dist_notation ?dist_label ?ind ?ind_label ?valor
WHERE {{
  GRAPH <{GRAFO_DATOS}> {{
    ?sec_uri skos:notation "{cusec}" ;
             skos:prefLabel ?sec_label ;
             skos:broader ?dist_uri .
    ?dist_uri skos:notation ?dist_notation .

    ?obs ine:censusSection ?sec_uri ;
         ine:indicator ?ind ;
         ine:gentrificationIndex ?valor .

    BIND (IF(?ind = ind:I-01, "Índice compuesto de gentrificación",
        IF(?ind = ind:I-02, "Variación renta 2020→2023",
        IF(?ind = ind:I-03, "Variación Gini 2020→2023",
        IF(?ind = ind:I-04, "% viviendas turísticas",
                           "Desconocido")))) AS ?ind_label)
  }}

  OPTIONAL {{
    GRAPH <{GRAFO_KOS}> {{
      ?kos_dist skos:notation ?dist_notation ;
                skos:prefLabel ?dist_label .
      FILTER(LANG(?dist_label) = "es")
    }}
  }}
}}
"""
    results = query_virtuoso(query)

    if not results:
        raise HTTPException(status_code=404, detail=f"Sección censal {cusec} no encontrada")

    first       = results[0]
    sec_label   = first["sec_label"]["value"]
    dist_codigo = format_uri(first["dist_uri"]["value"])
    dist_label  = (
        first.get("dist_label", {}).get("value")
        or first.get("dist_notation", {}).get("value", dist_codigo)
    )

    indicadores = [{
        "codigo": format_uri(row["ind"]["value"]),
        "label":  row["ind_label"]["value"],
        "valor":  float(row["valor"]["value"])
    } for row in results]

    return SeccionCensal(
        cusec=cusec, label=sec_label,
        distrito_codigo=dist_codigo, distrito_label=dist_label,
        indicadores=indicadores
    )


# ── Distritos ──────────────────────────────────────────────────────────────
# IMPORTANTE: /distritos/agregado SIEMPRE antes de /distritos/{codigo}

@app.get("/distritos/agregado", response_model=List[DistritoAgregado], tags=["Distritos"])
async def distritos_agregado():
    """
    Estadísticas agregadas (media de indicadores) para todos los distritos de Madrid.
    Ordenados por I-01 descendente. Nombres de distrito desde el KOS.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?dist_notation ?dist_label
       (AVG(?val_i01) AS ?media_i01) (AVG(?val_i02) AS ?media_i02)
       (AVG(?val_i03) AS ?media_i03) (AVG(?val_i04) AS ?media_i04)
       (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
WHERE {{
  GRAPH <{GRAFO_DATOS}> {{
    ?sec_uri skos:broader ?dist_uri .
    ?dist_uri skos:notation ?dist_notation .

    ?obs ine:censusSection ?sec_uri ;
         ine:indicator ?ind ;
         ine:gentrificationIndex ?valor .

    BIND (IF(?ind = ind:I-01, ?valor, ?undef) AS ?val_i01)
    BIND (IF(?ind = ind:I-02, ?valor, ?undef) AS ?val_i02)
    BIND (IF(?ind = ind:I-03, ?valor, ?undef) AS ?val_i03)
    BIND (IF(?ind = ind:I-04, ?valor, ?undef) AS ?val_i04)
  }}

  OPTIONAL {{
    GRAPH <{GRAFO_KOS}> {{
      ?kos_dist skos:notation ?dist_notation ;
                skos:prefLabel ?dist_label .
      FILTER(LANG(?dist_label) = "es")
    }}
  }}
}}
GROUP BY ?dist_uri ?dist_notation ?dist_label
ORDER BY DESC(?media_i01)
"""
    results = query_virtuoso(query)

    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron distritos")

    distritos = []
    for row in results:
        try:
            dist_label = (
                row.get("dist_label", {}).get("value")
                or row.get("dist_notation", {}).get("value", "")
            )
            distritos.append(DistritoAgregado(
                codigo        = row["dist_notation"]["value"],
                label         = dist_label,
                media_i01     = fval(row, "media_i01") or 0,
                media_i02     = fval(row, "media_i02") or 0,
                media_i03     = fval(row, "media_i03") or 0,
                media_i04     = fval(row, "media_i04") or 0,
                num_secciones = int(row["num_secciones"]["value"]) if row.get("num_secciones") else 0
            ))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Error procesando distrito: {row}, error: {e}")
            continue

    return distritos


@app.get("/distritos/{codigo}", response_model=DistritoAgregado, tags=["Distritos"])
async def obtener_distrito(codigo: str):
    """Estadísticas agregadas de un distrito específico."""
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?dist_label
       (AVG(?val_i01) AS ?media_i01) (AVG(?val_i02) AS ?media_i02)
       (AVG(?val_i03) AS ?media_i03) (AVG(?val_i04) AS ?media_i04)
       (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
WHERE {{
  GRAPH <{GRAFO_DATOS}> {{
    ?dist_uri skos:notation "{codigo}" .
    ?sec_uri skos:broader ?dist_uri .

    ?obs ine:censusSection ?sec_uri ;
         ine:indicator ?ind ;
         ine:gentrificationIndex ?valor .

    BIND (IF(?ind = ind:I-01, ?valor, ?undef) AS ?val_i01)
    BIND (IF(?ind = ind:I-02, ?valor, ?undef) AS ?val_i02)
    BIND (IF(?ind = ind:I-03, ?valor, ?undef) AS ?val_i03)
    BIND (IF(?ind = ind:I-04, ?valor, ?undef) AS ?val_i04)
  }}

  OPTIONAL {{
    GRAPH <{GRAFO_KOS}> {{
      ?kos_dist skos:notation "{codigo}" ;
                skos:prefLabel ?dist_label .
      FILTER(LANG(?dist_label) = "es")
    }}
  }}
}}
GROUP BY ?dist_uri ?dist_label
"""
    results = query_virtuoso(query)

    if not results:
        raise HTTPException(status_code=404, detail=f"Distrito {codigo} no encontrado")

    row        = results[0]
    dist_label = row.get("dist_label", {}).get("value") or codigo

    return DistritoAgregado(
        codigo        = codigo,
        label         = dist_label,
        media_i01     = fval(row, "media_i01") or 0,
        media_i02     = fval(row, "media_i02") or 0,
        media_i03     = fval(row, "media_i03") or 0,
        media_i04     = fval(row, "media_i04") or 0,
        num_secciones = int(row["num_secciones"]["value"]) if row.get("num_secciones") else 0
    )


# ── Utilidades ─────────────────────────────────────────────────────────────

@app.get("/comparar", response_model=ComparacionSecciones, tags=["Utilidades"])
async def comparar_secciones(
    sec1: str = Query(..., description="CUSEC de la primera sección"),
    sec2: str = Query(..., description="CUSEC de la segunda sección")
):
    """Compara los indicadores de dos secciones censales."""
    try:
        seccion1 = await obtener_seccion(sec1)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Sección {sec1} no encontrada")
    try:
        seccion2 = await obtener_seccion(sec2)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Sección {sec2} no encontrada")
    return ComparacionSecciones(seccion1=seccion1, seccion2=seccion2)


@app.get("/stats", tags=["Utilidades"])
async def estadisticas_generales():
    """Estadísticas generales del cubo de indicadores."""
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
       (COUNT(DISTINCT ?dist_uri) AS ?num_distritos)
       (COUNT(?obs) AS ?num_observaciones)
       (MIN(?valor) AS ?min_i01) (MAX(?valor) AS ?max_i01)
       (AVG(?valor) AS ?media_i01)
FROM <{GRAFO_DATOS}>
WHERE {{
  ?obs ine:censusSection ?sec_uri ;
       ine:indicator ind:I-01 ;
       ine:gentrificationIndex ?valor .
  ?sec_uri skos:broader ?dist_uri .
}}
"""
    results = query_virtuoso(query)
    if not results:
        raise HTTPException(status_code=500, detail="No se pudieron obtener estadísticas")

    row = results[0]
    return {
        "num_secciones_censales": int(row["num_secciones"]["value"]),
        "num_distritos":          int(row["num_distritos"]["value"]),
        "num_observaciones":      int(row["num_observaciones"]["value"]),
        "indice_gentrificacion": {
            "minimo": float(row["min_i01"]["value"]),
            "maximo": float(row["max_i01"]["value"]),
            "media":  float(row["media_i01"]["value"])
        }
    }


@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica que la API está operativa y conectada a Virtuoso."""
    try:
        query_virtuoso("SELECT (COUNT(*) as ?count) { ?s ?p ?o . } LIMIT 1")
        return {"status": "ok", "virtuoso": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Virtuoso no accesible: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
