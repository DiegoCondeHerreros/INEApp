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

# ── Configuración ──────────────────────────────────────────────────────────────
VIRTUOSO_ENDPOINT = "https://stats.linkeddata.es/sparql"

# Namespaces
INE = "http://lod.ine.es/def/vocabulary/"
IND_BASE = "http://lod.ine.es/recurso/indicadores/gentrificacion/"
KOS_SECCIONES = "http://lod.ine.es/kos/secciones-censales/SECCIONES_CENSALES/"
KOS_DISTRITOS = "http://lod.ine.es/kos/distritos/DISTRITOS/"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="INELODApp API",
    description="API REST para consultar indicadores de gentrificación a nivel de sección censal en Madrid",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos Pydantic ───────────────────────────────────────────────────────────
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


class DistritoAgreagado(BaseModel):
    codigo: str
    label: str
    media_i01: float
    media_i02: float
    media_i03: float
    media_i04: float
    num_secciones: int


class ComparacionSecciones(BaseModel):
    seccion1: SeccionCensal
    seccion2: SeccionCensal


# ── Helpers ────────────────────────────────────────────────────────────────────
def query_virtuoso(query: str) -> List[dict]:
    """Ejecuta una consulta SPARQL contra Virtuoso."""
    try:
        sw = SPARQLWrapper(VIRTUOSO_ENDPOINT)
        sw.setQuery(query)
        sw.setReturnFormat(JSON)
        results = sw.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logger.error(f"Error consultando Virtuoso: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando Virtuoso: {str(e)}")


def format_uri(uri: str) -> str:
    """Extrae la parte local de una URI."""
    return uri.split("/")[-1]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["Raíz"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "nombre": "INELODApp API",
        "descripción": "API REST para indicadores de gentrificación en Madrid",
        "endpoints": {
            "indicadores_madrid": "/indicadores/madrid",
            "sección_censal": "/secciones/{cusec}",
            "distrito": "/distritos/{codigo}",
            "comparar": "/comparar?sec1=...&sec2=...",
            "distritos_agregado": "/distritos/agregado"
        },
        "docs": "/docs"
    }


@app.get("/indicadores/madrid", response_model=List[SeccionCensal], tags=["Indicadores"])
async def indicadores_madrid(
    indicador: Optional[str] = Query(None, description="Filtrar por indicador (I-01, I-02, I-03, I-04)"),
    limit: int = Query(100, description="Límite de resultados", ge=1, le=2500)
):
    """
    Obtiene los indicadores de gentrificación para todas las secciones censales de Madrid.
    Opcionalmente filtrado por indicador específico.
    """
    
    # Filtro de indicador si se especifica
    indicador_filter = ""
    if indicador:
        indicador_filter = f'FILTER (STRSTARTS(STR(?ind), "{IND_BASE}{indicador}"))'
    
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX sdmx: <http://purl.org/linked-data/sdmx/2009/dimension#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?sec_uri ?sec_label ?dist_uri ?dist_label ?ind ?ind_label ?valor
FROM <http://lod.ine.es/recurso/cubes/gentrificacion>
WHERE {{
  ?obs qb:dataSet <http://lod.ine.es/recurso/cubes/gentrificacion> ;
       ine:censusSection ?sec_uri ;
       ine:indicator ?ind ;
       ine:gentrificationIndex ?valor .
  
  ?sec_uri skos:prefLabel ?sec_label ;
           skos:broader ?dist_uri .
  ?dist_uri skos:prefLabel ?dist_label .
  
  # Mapeo de indicador a label
  BIND (IF(?ind = ind:I-01, "Índice compuesto de gentrificación",
      IF(?ind = ind:I-02, "Variación renta 2020→2023",
      IF(?ind = ind:I-03, "Variación Gini 2020→2023",
      IF(?ind = ind:I-04, "% viviendas turísticas",
                         "Desconocido")))) AS ?ind_label)
  
  {indicador_filter}
}}
ORDER BY ?sec_uri
LIMIT {limit}
"""
    
    results = query_virtuoso(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron indicadores")
    
    # Agrupar por sección censal
    secciones_dict = {}
    for row in results:
        sec_uri = row["sec_uri"]["value"]
        cusec = format_uri(sec_uri)
        sec_label = row["sec_label"]["value"]
        dist_codigo = format_uri(row["dist_uri"]["value"])
        dist_label = row["dist_label"]["value"]
        ind_uri = row["ind"]["value"]
        ind_codigo = format_uri(ind_uri)
        ind_label = row["ind_label"]["value"]
        valor = float(row["valor"]["value"])
        
        if cusec not in secciones_dict:
            secciones_dict[cusec] = {
                "cusec": cusec,
                "label": sec_label,
                "distrito_codigo": dist_codigo,
                "distrito_label": dist_label,
                "indicadores": []
            }
        
        secciones_dict[cusec]["indicadores"].append({
            "codigo": ind_codigo,
            "label": ind_label,
            "valor": valor
        })
    
    return [SeccionCensal(**v) for v in secciones_dict.values()]


@app.get("/secciones/{cusec}", response_model=SeccionCensal, tags=["Secciones"])
async def obtener_seccion(cusec: str):
    """
    Obtiene todos los indicadores y datos de una sección censal específica.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX sdmx: <http://purl.org/linked-data/sdmx/2009/dimension#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?sec_label ?dist_uri ?dist_label ?ind ?ind_label ?valor
FROM <http://lod.ine.es/recurso/cubes/gentrificacion>
WHERE {{
  ?sec_uri skos:notation "{cusec}" ;
           skos:prefLabel ?sec_label ;
           skos:broader ?dist_uri .
  
  ?dist_uri skos:prefLabel ?dist_label .
  
  ?obs ine:censusSection ?sec_uri ;
       ine:indicator ?ind ;
       ine:gentrificationIndex ?valor .
  
  BIND (IF(?ind = ind:I-01, "Índice compuesto de gentrificación",
      IF(?ind = ind:I-02, "Variación renta 2020→2023",
      IF(?ind = ind:I-03, "Variación Gini 2020→2023",
      IF(?ind = ind:I-04, "% viviendas turísticas",
                         "Desconocido")))) AS ?ind_label)
}}
"""
    
    results = query_virtuoso(query)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Sección censal {cusec} no encontrada")
    
    # Procesar resultado
    first = results[0]
    sec_label = first["sec_label"]["value"]
    dist_codigo = format_uri(first["dist_uri"]["value"])
    dist_label = first["dist_label"]["value"]
    
    indicadores = []
    for row in results:
        indicadores.append({
            "codigo": format_uri(row["ind"]["value"]),
            "label": row["ind_label"]["value"],
            "valor": float(row["valor"]["value"])
        })
    
    return SeccionCensal(
        cusec=cusec,
        label=sec_label,
        distrito_codigo=dist_codigo,
        distrito_label=dist_label,
        indicadores=indicadores
    )


@app.get("/distritos/{codigo}", response_model=DistritoAgreagado, tags=["Distritos"])
async def obtener_distrito(codigo: str):
    """
    Obtiene estadísticas agregadas de un distrito: media de indicadores y número de secciones.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?dist_label (AVG(?val_i01) AS ?media_i01) (AVG(?val_i02) AS ?media_i02)
       (AVG(?val_i03) AS ?media_i03) (AVG(?val_i04) AS ?media_i04)
       (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
FROM <http://lod.ine.es/recurso/cubes/gentrificacion>
WHERE {{
  ?dist_uri skos:notation "{codigo}" ;
            skos:prefLabel ?dist_label .
  
  ?sec_uri skos:broader ?dist_uri .
  
  ?obs ine:censusSection ?sec_uri ;
       ine:indicator ?ind ;
       ine:gentrificationIndex ?valor .
  
  BIND (IF(?ind = ind:I-01, ?valor, ?undef) AS ?val_i01)
  BIND (IF(?ind = ind:I-02, ?valor, ?undef) AS ?val_i02)
  BIND (IF(?ind = ind:I-03, ?valor, ?undef) AS ?val_i03)
  BIND (IF(?ind = ind:I-04, ?valor, ?undef) AS ?val_i04)
}}
GROUP BY ?dist_uri ?dist_label
"""
    
    results = query_virtuoso(query)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Distrito {codigo} no encontrado")
    
    row = results[0]
    return DistritoAgreagado(
        codigo=codigo,
        label=row["dist_label"]["value"],
        media_i01=float(row["media_i01"]["value"]) if row.get("media_i01") else 0,
        media_i02=float(row["media_i02"]["value"]) if row.get("media_i02") else 0,
        media_i03=float(row["media_i03"]["value"]) if row.get("media_i03") else 0,
        media_i04=float(row["media_i04"]["value"]) if row.get("media_i04") else 0,
        num_secciones=int(row["num_secciones"]["value"])
    )


@app.get("/distritos/agregado", response_model=List[DistritoAgreagado], tags=["Distritos"])
async def distritos_agregado():
    """
    Obtiene estadísticas agregadas para todos los distritos de Madrid.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT ?dist_codigo ?dist_label (AVG(?val_i01) AS ?media_i01)
       (AVG(?val_i02) AS ?media_i02) (AVG(?val_i03) AS ?media_i03)
       (AVG(?val_i04) AS ?media_i04) (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
FROM <http://lod.ine.es/recurso/cubes/gentrificacion>
WHERE {{
  ?sec_uri skos:broader ?dist_uri .
  ?dist_uri skos:notation ?dist_codigo ;
            skos:prefLabel ?dist_label .
  
  ?obs ine:censusSection ?sec_uri ;
       ine:indicator ?ind ;
       ine:gentrificationIndex ?valor .
  
  BIND (IF(?ind = ind:I-01, ?valor, ?undef) AS ?val_i01)
  BIND (IF(?ind = ind:I-02, ?valor, ?undef) AS ?val_i02)
  BIND (IF(?ind = ind:I-03, ?valor, ?undef) AS ?val_i03)
  BIND (IF(?ind = ind:I-04, ?valor, ?undef) AS ?val_i04)
}}
GROUP BY ?dist_uri ?dist_codigo ?dist_label
ORDER BY DESC(?media_i01)
"""
    
    results = query_virtuoso(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron distritos")
    
    distritos = []
    for row in results:
        distritos.append(DistritoAgreagado(
            codigo=row["dist_codigo"]["value"],
            label=row["dist_label"]["value"],
            media_i01=float(row["media_i01"]["value"]) if row.get("media_i01") else 0,
            media_i02=float(row["media_i02"]["value"]) if row.get("media_i02") else 0,
            media_i03=float(row["media_i03"]["value"]) if row.get("media_i03") else 0,
            media_i04=float(row["media_i04"]["value"]) if row.get("media_i04") else 0,
            num_secciones=int(row["num_secciones"]["value"])
        ))
    
    return distritos


@app.get("/comparar", response_model=ComparacionSecciones, tags=["Utilidades"])
async def comparar_secciones(
    sec1: str = Query(..., description="CUSEC de la primera sección"),
    sec2: str = Query(..., description="CUSEC de la segunda sección")
):
    """
    Compara los indicadores de dos secciones censales.
    """
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
    """
    Obtiene estadísticas generales del cubo de indicadores.
    """
    query = f"""
PREFIX ine:  <{INE}>
PREFIX ind:  <{IND_BASE}>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX qb:   <http://purl.org/linked-data/cube#>

SELECT (COUNT(DISTINCT ?sec_uri) AS ?num_secciones)
       (COUNT(DISTINCT ?dist_uri) AS ?num_distritos)
       (COUNT(?obs) AS ?num_observaciones)
       (MIN(?valor) AS ?min_i01) (MAX(?valor) AS ?max_i01)
       (AVG(?valor) AS ?media_i01)
FROM <http://lod.ine.es/recurso/cubes/gentrificacion>
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
        "num_distritos": int(row["num_distritos"]["value"]),
        "num_observaciones": int(row["num_observaciones"]["value"]),
        "indice_gentrificacion": {
            "minimo": float(row["min_i01"]["value"]),
            "maximo": float(row["max_i01"]["value"]),
            "media": float(row["media_i01"]["value"])
        }
    }


@app.get("/health", tags=["Sistema"])
async def health_check():
    """
    Verifica que la API está operativa y conectada a Virtuoso.
    """
    try:
        # Consulta simple para verificar conexión
        query = "SELECT (COUNT(*) as ?count) { ?s ?p ?o . } LIMIT 1"
        query_virtuoso(query)
        return {"status": "ok", "virtuoso": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Virtuoso no accesible: {str(e)}")


# ── Manejo de errores ──────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
