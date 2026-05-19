# scripts/load_graph.py (esquemático)
import requests
from requests.auth import HTTPDigestAuth

def load_turtle(turtle_path, graph_uri, endpoint, user, password):
    with open(turtle_path) as f:
        triples = f.read()
    update = f"INSERT DATA {{ GRAPH <{graph_uri}> {{ {triples} }} }}"
    r = requests.post(
        endpoint + "/sparql-auth",
        data={"update": update},
        auth=HTTPDigestAuth(user, password),
    )
    r.raise_for_status()

def load_turtle_gsp(turtle_path, graph_uri, endpoint, user, password):
    with open(turtle_path, "rb") as f:
        r = requests.post(
            f"{endpoint}/sparql-graph-crud-auth",
            params={"graph": graph_uri},
            data=f,
            headers={"Content-Type": "text/turtle"},
            auth=HTTPDigestAuth(user, password),
        )
    r.raise_for_status()