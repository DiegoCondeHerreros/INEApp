from pathlib import Path
from rdflib.util import guess_format
from pysparql_anything import PySparqlAnything

# Inicializamos el motor
engine = PySparqlAnything()

# Tu consulta SPARQL (usando la sintaxis Facade-X)
query_path = Path(__file__).resolve().parent / "construct" / "31097.sparql"
query = query_path.read_text(encoding="utf-8")
query_format = guess_format(str(query_path))

# Ejecutar la consulta y obtener resultados
# El método select() devuelve un objeto que puedes iterar
resultados = engine.select(query)

for fila in resultados:
    print(f"Empleado: {fila['nombre']} - Cargo: {fila['rol']}")