# scripts/ping.py
import os, requests
from requests.auth import HTTPDigestAuth

ep = os.environ["VIRTUOSO_ENDPOINT"]
r = requests.get(
    f"{ep}/sparql",
    params={"query": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }", "format": "json"},
)
print(r.status_code, r.json())

# Y una de escritura: crear y borrar un grafo de prueba
from requests.auth import HTTPDigestAuth
test_graph = "https://inelod.org/graph/_smoke-test"
auth = HTTPDigestAuth(os.environ["VIRTUOSO_USER"], os.environ["VIRTUOSO_PASSWORD"])
r = requests.post(
    f"{ep}/sparql-auth",
    data={"update": f"INSERT DATA {{ GRAPH <{test_graph}> {{ <urn:a> <urn:b> <urn:c> }} }}"},
    auth=auth,
)
r.raise_for_status()
r = requests.post(
    f"{ep}/sparql-auth",
    data={"update": f"CLEAR GRAPH <{test_graph}>"},
    auth=auth,
)
print("Write OK")