#!/usr/bin/env python3
"""
Calcula indicadores usando índices pre-calculados en lugar de SPARQL queries.
"""

import uuid
import numpy as np
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, SKOS, XSD

# ── Configuración ─────────────────────────────────────────────────────────────
TTL_ADRH_31097 = Path("data/ttl/31097.ttl")
TTL_ADRH_31105 = Path("data/ttl/31105.ttl")
TTL_ADRH_37727 = Path("data/ttl/37727.ttl")

# Los 4 ficheros del VUT (tabla 5)
TTL_VUT_01_VIVIENDAS = Path("data/ttl/5_1.ttl")
TTL_VUT_02_PLAZAS = Path("data/ttl/5_2.ttl")
TTL_VUT_03_RATIO = Path("data/ttl/5_3.ttl")
TTL_VUT_04_PORCENTAJE = Path("data/ttl/5_4.ttl")

TTL_OUT = Path("build/indicadores-gentrificacion.ttl")

INE      = Namespace("http://lod.ine.es/def/vocabulary/")
QB       = Namespace("http://purl.org/linked-data/cube#")
SDMX_DIM = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
SDMX_ATT = Namespace("http://purl.org/linked-data/sdmx/2009/attribute#")
IND_BASE = Namespace("http://lod.ine.es/recurso/indicadores/gentrificacion/")
OBS_BASE = "http://lod.ine.es/recurso/cubes/gentrificacion/o"
DATASET  = URIRef("http://lod.ine.es/recurso/cubes/gentrificacion")

PESO = 1/3


# ── Helpers ───────────────────────────────────────────────────────────────────
def cargar_grafos(*rutas: Path) -> Graph:
    """Carga varios ficheros TTL en un único grafo rdflib."""
    g = Graph()
    for ruta in rutas:
        if not ruta.exists():
            raise FileNotFoundError(f"Fichero no encontrado: {ruta}")
        tamaño_kb = ruta.stat().st_size // 1024
        print(f"  Cargando {ruta.name} ({tamaño_kb} KB)...")
        g.parse(str(ruta), format="turtle")
    print(f"  Total tripletas: {len(g)}\n")
    return g


def percentile_rank(values: np.ndarray, v: float) -> float:
    """Calcula el percentil de v en la distribución."""
    return float(np.sum(values <= v) / len(values) * 100)


def normalize_series(values: list) -> list:
    """Normaliza una lista de valores a percentil rank [0..100]."""
    arr = np.array(values, dtype=float)
    return [percentile_rank(arr, v) for v in arr]


def nueva_obs(g_out: Graph, sec_uri: URIRef, periodo, ind_uri: URIRef,
              valor: float, unidad: str):
    """Añade una observación al grafo de salida."""
    obs = URIRef(f"{OBS_BASE}{uuid.uuid4()}")
    g_out.add((obs, RDF.type, QB.Observation))
    g_out.add((obs, QB.dataSet, DATASET))
    g_out.add((obs, INE.censusSection, sec_uri))
    g_out.add((obs, SDMX_DIM.refPeriod, periodo))
    g_out.add((obs, INE.indicator, ind_uri))
    g_out.add((obs, INE.gentrificationIndex,
               Literal(round(valor, 4), datatype=XSD.decimal)))
    g_out.add((obs, SDMX_ATT.unitMeasure, Literal(unidad)))


# ── 1. Cargar los Turtle ──────────────────────────────────────────────────────
print("Cargando ficheros TTL ADRH...")
g_adrh = cargar_grafos(TTL_ADRH_31097, TTL_ADRH_31105, TTL_ADRH_37727)

print("Cargando ficheros TTL Viviendas Turísticas (4 fragmentos)...")
g_vut = cargar_grafos(TTL_VUT_01_VIVIENDAS, TTL_VUT_02_PLAZAS,
                      TTL_VUT_03_RATIO, TTL_VUT_04_PORCENTAJE)


# ── 2. Pre-indexar observaciones ADRH ──────────────────────────────────────────
print("Pre-indexando observaciones ADRH...")

# Índice: {(sec_uri, año_str): {propiedad: valor, ...}}
adrh_obs_por_sec_año = defaultdict(dict)

for obs, _, _ in g_adrh.triples((None, RDF.type, QB.Observation)):
    # Obtener sección censal
    secciones = list(g_adrh.objects(obs, INE.censusSection))
    if not secciones:
        continue
    sec = secciones[0]
    
    # Obtener periodo
    periodos = list(g_adrh.objects(obs, SDMX_DIM.refPeriod))
    if not periodos:
        continue
    período_str = str(periodos[0])
    
    # Obtener todas las propiedades de valor (renta, gini, demografía)
    # Del ADRH extraemos: eurosPerInhabitant, giniIndex, meanAge, 
    # percentageOfYoungPopulation, percentageOfElderlyPopulation, 
    # meanHouseholdSize, percentageOfSingleHouseholds, totalPopulation,
    # percentageOfSpanishPopulation
    for prop in [
        INE.eurosPerInhabitant, INE.giniIndex, INE.meanAge,
        INE.percentageOfYoungPopulation, INE.percentageOfElderlyPopulation,
        INE.meanHouseholdSize, INE.percentageOfSingleHouseholds,
        INE.totalPopulation, INE.percentageOfSpanishPopulation
    ]:
        valores = list(g_adrh.objects(obs, prop))
        if valores:
            adrh_obs_por_sec_año[(sec, período_str)][prop] = float(valores[0])

print(f"  {len(adrh_obs_por_sec_año)} observaciones indexadas\n")


# ── 3. Calcular I-02: variación renta 2020→2023 ───────────────────────────────
print("Calculando I-02 (variación renta 2020→2023)...")

i02_2023 = {}
i02_2020 = {}
for (sec, año_str), props in adrh_obs_por_sec_año.items():
    renta = props.get(INE.eurosPerInhabitant)
    if renta:
        if "2023" in año_str:
            i02_2023[sec] = renta
        elif "2020" in año_str:
            i02_2020[sec] = renta

i02_raw = {}
for sec in i02_2023:
    if sec in i02_2020 and i02_2020[sec] > 0:
        i02_raw[sec] = (i02_2023[sec] - i02_2020[sec]) / i02_2020[sec] * 100

print(f"  Secciones con I-02: {len(i02_raw)}\n")


# ── 4. Calcular I-03: variación Gini 2020→2023 ────────────────────────────────
print("Calculando I-03 (variación Gini 2020→2023)...")

i03_2023 = {}
i03_2020 = {}
for (sec, año_str), props in adrh_obs_por_sec_año.items():
    gini = props.get(INE.giniIndex)
    if gini:
        if "2023" in año_str:
            i03_2023[sec] = gini
        elif "2020" in año_str:
            i03_2020[sec] = gini

i03_raw = {}
for sec in i03_2023:
    if sec in i03_2020 and i03_2020[sec] > 0:
        i03_raw[sec] = (i03_2023[sec] - i03_2020[sec]) / i03_2020[sec] * 100

print(f"  Secciones con I-03 directo: {len(i03_raw)}")

# Imputación desde distrito si falta sección
dist_gini = defaultdict(lambda: {})
for obs, _, _ in g_adrh.triples((None, RDF.type, QB.Observation)):
    dists = list(g_adrh.objects(obs, INE.districts))
    if not dists:
        continue
    dist = dists[0]
    
    periodos = list(g_adrh.objects(obs, SDMX_DIM.refPeriod))
    if not periodos:
        continue
    período_str = str(periodos[0])
    
    ginis = list(g_adrh.objects(obs, INE.giniIndex))
    if ginis:
        dist_gini[dist][período_str] = float(ginis[0])

# Imputar a secciones que no tengan
imputadas = 0
for sec in i02_raw:
    if sec not in i03_raw:
        dists = list(g_adrh.objects(sec, SKOS.broader))
        if dists:
            dist = dists[0]
            if dist in dist_gini:
                g23 = None
                g20 = None
                for año_str, val in dist_gini[dist].items():
                    if "2023" in año_str:
                        g23 = val
                    elif "2020" in año_str:
                        g20 = val
                if g23 and g20 and g20 > 0:
                    i03_raw[sec] = (g23 - g20) / g20 * 100
                    imputadas += 1

print(f"  Total con I-03 (incl. {imputadas} imputadas): {len(i03_raw)}\n")


# ── 5. Pre-indexar VUT ─────────────────────────────────────────────────────────
print("Pre-indexando observaciones VUT...")

# Índice: {(sec_uri, periodo_literal): propiedad → valor}
vut_obs_por_sec_periodo = defaultdict(dict)

for obs, _, _ in g_vut.triples((None, RDF.type, QB.Observation)):
    secs = list(g_vut.objects(obs, INE.censusSection))
    if not secs:
        continue
    sec = secs[0]
    
    periodos = list(g_vut.objects(obs, SDMX_DIM.refPeriod))
    if not periodos:
        continue
    periodo = periodos[0]
    
    # Extraer las 4 medidas del VUT
    for prop in [
        INE.touristDwellings, INE.numberOfBedplaces,
        INE.bedplacesPerTouristDwelling, INE.touristDwellingsRatio
    ]:
        valores = list(g_vut.objects(obs, prop))
        if valores:
            vut_obs_por_sec_periodo[(sec, periodo)][prop] = float(valores[0])

print(f"  {len(vut_obs_por_sec_periodo)} observaciones indexadas\n")


# ── 6. Calcular I-04 e I-05 ───────────────────────────────────────────────────
print("Calculando I-04 (viviendas turísticas)...")

# I-04: porcentaje directo
i04_raw = {}
for (sec, periodo), props in vut_obs_por_sec_periodo.items():
    pct = props.get(INE.touristDwellingsRatio)
    if pct is not None:
        i04_raw[(sec, periodo)] = pct

# I-05: variación entre periodos consecutivos
#vut_por_sec = defaultdict(list)
#for (sec, periodo), props in vut_obs_por_sec_periodo.items():
#    pct = props.get(INE.touristDwellingsRatio)
#    if pct is not None:
#        vut_por_sec[sec].append((str(periodo), pct))

#i05_raw = {}
#for sec, periodos in vut_por_sec.items():
#    periodos_sorted = sorted(periodos, key=lambda x: x[0])
#    for i in range(1, len(periodos_sorted)):
#        p0, pct0 = periodos_sorted[i - 1]
#        p1, pct1 = periodos_sorted[i]
#        if pct0 > 0:
#            # Convertir periodo string a Literal
#            periodo_lit = Literal(p1, datatype=XSD.gYearMonth)
#            i05_raw[(sec, periodo_lit)] = (pct1 - pct0) / pct0 * 100

print(f"  I-04: {len(i04_raw)} observaciones")
#print(f"  I-05: {len(i05_raw)} observaciones\n")


# ── 7. Normalizar por percentiles ─────────────────────────────────────────────
print("Normalizando por percentiles...")

def norm_dict_simple(d: dict) -> dict:
    """Normaliza dict {sec: valor}."""
    claves = list(d.keys())
    vals = [d[k] for k in claves]
    norms = normalize_series(vals)
    return dict(zip(claves, norms))


def norm_dict_por_periodo(d: dict) -> dict:
    """Normaliza dict {(sec, periodo): valor} por periodo."""
    periodos = set(p for _, p in d.keys())
    result = {}
    for periodo in periodos:
        claves = [(s, p) for s, p in d.keys() if p == periodo]
        vals = [d[k] for k in claves]
        norms = normalize_series(vals)
        result.update(zip(claves, norms))
    return result


i02_norm = norm_dict_simple(i02_raw)
i03_norm = norm_dict_simple(i03_raw)
i04_norm = norm_dict_por_periodo(i04_raw)
#i05_norm = norm_dict_por_periodo(i05_raw)

print("Normalización completada\n")


# ── 8. Calcular I-01 ──────────────────────────────────────────────────────────
print("Calculando I-01 (índice compuesto)...")

i01 = {}
for (sec, periodo) in i04_norm:
#    if (sec, periodo) not in i05_norm:
#        continue
    if sec not in i02_norm:
        continue
    if sec not in i03_norm:
        continue
    i01[(sec, periodo)] = (
        PESO * i02_norm[sec] +
        PESO * i03_norm[sec] +
        PESO * i04_norm[(sec, periodo)]
    )

print(f"  I-01: {len(i01)} observaciones\n")


# ── 9. Construir grafo de salida ──────────────────────────────────────────────
print("Generando grafo de salida...")

g_out = Graph()
g_out.bind("ine", INE)
g_out.bind("qb", QB)
g_out.bind("sdmx-dim", SDMX_DIM)
g_out.bind("sdmx-att", SDMX_ATT)
g_out.bind("ind", IND_BASE)
g_out.bind("xsd", XSD)

# I-02
for sec, valor in i02_norm.items():
    nueva_obs(g_out, sec, Literal("2023", datatype=XSD.gYear),
              IND_BASE["I-02"], valor, "PERCENTILE_RANK")

# I-03
for sec, valor in i03_norm.items():
    nueva_obs(g_out, sec, Literal("2023", datatype=XSD.gYear),
              IND_BASE["I-03"], valor, "PERCENTILE_RANK")

# I-04
for (sec, periodo), valor in i04_norm.items():
    nueva_obs(g_out, sec, periodo, IND_BASE["I-04"], valor, "PERCENTILE_RANK")

# I-05
#for (sec, periodo), valor in i05_norm.items():
#    nueva_obs(g_out, sec, periodo, IND_BASE["I-05"], valor, "PERCENTILE_RANK")

# I-01
for (sec, periodo), valor in i01.items():
    nueva_obs(g_out, sec, periodo, IND_BASE["I-01"], valor, "PERCENTILE_RANK")

TTL_OUT.parent.mkdir(parents=True, exist_ok=True)
g_out.serialize(destination=str(TTL_OUT), format="turtle")

total = (len(i02_norm) + len(i03_norm) + len(i04_norm) + len(i01))

print(f"""
✓ Cálculo completado:
  I-02: {len(i02_norm)} observaciones
  I-03: {len(i03_norm)} observaciones
  I-04: {len(i04_norm)} observaciones
  I-01: {len(i01)} observaciones
  
  Total: {total} observaciones
  Fichero: {TTL_OUT}
""")