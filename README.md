# INELOD · Prototipo del visor de gentrificación

Prototipo navegable del visor de gentrificación del proyecto **INELOD — Framework
semántico para la explotación de la estadística pública española**.

## Qué incluye el prototipo

Tres vistas navegables desde la barra superior:

- **Visor.** Mapa coroplético de los 21 distritos de Madrid con coloreado por
  percentiles, panel lateral con selector de indicador (5 disponibles),
  configuración de pesos (3 presets), selector de año (2018–2023) y leyenda
  dinámica. Al pulsar un distrito se abre la ficha con el desglose en
  componentes elementales, evolución temporal y procedencia de los datos.

- **Catálogo de indicadores.** Vista que representa el resultado del endpoint
  `GET /indicators`: metadatos canónicos de los cinco indicadores publicados
  en el grafo del MVP (definición, unidades, fuentes, fórmula).

- **Acerca de.** Identidad del proyecto, pila tecnológica, vocabularios
  reutilizados, equipo y aviso del prototipo.

## Datos

Los datos del prototipo son **sintéticos** sobre gentrificación en Madrid. Se han ajustado de modo que Centro (que contiene Lavapiés), Tetuán y Chamberí marquen alto en el indicador compuesto, en línea con los casos documentados en la bibliografía. Las periferias norte y sur quedan en valores bajos.

Las **geometrías de los distritos** son aproximaciones sobre los 21 centroides reales, recortadas por un polígono que aproxima el término municipal. Suficientes para validar el aspecto y flujo de la aplicación pero no aptas para análisis cartográfico riguroso. La implementación final consumirá GeoJSON real del INE y geometrías administrativas del IGN.

Datos disponibles en `data/`:

- `madrid-distritos.geojson` — 21 distritos del municipio de Madrid.
- `indicators.json` — 4 indicadores elementales y 3 configuraciones del
  compuesto, para el periodo 2018–2023.

## Pila técnica del prototipo

- HTML + CSS + JavaScript vanilla, sin frameworks ni build step.
- [Leaflet 1.9.4](https://leafletjs.com/) (embebido inline en `index.html`).
- Estilo visual alineado con la identidad de los portales del INE.

## Pila objetivo de la implementación final

El prototipo es solo una representación visual. La implementación real del
MVP utilizará:

- **SPARQL-Anything** (Facade-X) para virtualizar las fuentes del INE.
- **OpenLink Virtuoso** como triplestore con soporte GeoSPARQL.
- **RDF Data Cube + SDMX-RDF + SKOS + GeoSPARQL + PROV-O** como vocabularios.
- **FastAPI** para la API REST.
- **MapLibre GL JS** para el visor cartográfico (en este prototipo se usa
  Leaflet por simplicidad de empaquetado).

## Equipo

- Diego Conde Herreros
- Luis M. Vilches-Blázquez
- Óscar Corcho

Ontology Engineering Group — ETSI Informáticos, Universidad Politécnica de Madrid.

## Licencia

Código bajo licencia MIT.
