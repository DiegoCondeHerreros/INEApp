from pathlib import Path
from rdflib import Graph
from rdflib.namespace import Namespace
from rdflib.namespace import RDF

SDMX_DIM = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
QB = Namespace("http://purl.org/linked-data/cube#")

g_vut = Graph()
for f in ["data/ttl/5_1.ttl", "data/ttl/5_2.ttl", 
          "data/ttl/5_3.ttl", "data/ttl/5_4.ttl"]:
    g_vut.parse(f, format="turtle")

periodos = set(g_vut.objects(None, SDMX_DIM.refPeriod))
print(f"Periodos únicos en VUT: {len(periodos)}")
for p in sorted(str(x) for x in periodos):
    print(f"  {p}")