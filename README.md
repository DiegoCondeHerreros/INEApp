# INELOD · Prototipo del visor de gentrificación (Madrid · MVP 0.3)

Prototipo navegable del visor de gentrificación del proyecto **INELOD — Framework
semántico para la explotación de la estadística pública española**.

Versión MVP a cuatro semanas, restringida al municipio de Madrid sobre dos
operaciones del INE: *Atlas de Distribución de Renta de los Hogares* (ADRH) y
*Medición del número de viviendas turísticas en España*.

## Demo

Una vez activado GitHub Pages (ver más abajo), la demo queda accesible en:

```
https://<usuario>.github.io/<nombre-del-repo>/
```

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

Los datos del prototipo son **sintéticos pero calibrados con literatura
empírica** sobre gentrificación en Madrid. Se han ajustado de modo que Centro
(que contiene Lavapiés), Tetuán y Chamberí marquen alto en el indicador
compuesto, en línea con los casos documentados en la bibliografía. Las
periferias norte y sur quedan en valores bajos.

Las **geometrías de los distritos** son aproximaciones tipo Voronoi sobre los
21 centroides reales, recortadas por un polígono que aproxima el término
municipal. Suficientes para validar el aspecto y flujo de la aplicación pero
no aptas para análisis cartográfico riguroso. La implementación final
consumirá GeoJSON real del INE y geometrías administrativas del IGN.

Datos disponibles en `data/`:

- `madrid-distritos.geojson` — 21 distritos del municipio de Madrid.
- `indicators.json` — 4 indicadores elementales y 3 configuraciones del
  compuesto, para el periodo 2018–2023.

## Estructura del repositorio

```
.
├── index.html                  Aplicación autocontenida (HTML + CSS + JS + Leaflet inline)
├── data/
│   ├── madrid-distritos.geojson
│   └── indicators.json
├── .github/workflows/
│   └── pages.yml               Despliegue automático en GitHub Pages
├── README.md
└── LICENSE
```

`index.html` es **autocontenido**: incluye Leaflet, los datos y todo el
código necesario en un único fichero. Funciona abriéndolo directamente en
cualquier navegador moderno (`file://`) sin servidor ni conexión a Internet.

Los ficheros de `data/` se publican por separado para facilitar la
reutilización por terceros y la inspección manual de los datos.

## Despliegue en GitHub Pages

Para publicar el prototipo en GitHub Pages basta con:

1. Crear un repositorio nuevo en GitHub y subir todo el contenido de esta
   carpeta a la rama `main`.
2. Ir a **Settings → Pages** del repositorio.
3. En *Source*, seleccionar **GitHub Actions**.
4. El workflow de `.github/workflows/pages.yml` se ejecutará automáticamente
   tras el primer push y la URL pública aparecerá en la pestaña *Pages* en
   uno o dos minutos.

Como alternativa, sin GitHub Actions, basta con:

1. **Settings → Pages → Source: Deploy from a branch**.
2. Seleccionar `main` y carpeta `/ (root)`.
3. Esperar 1–2 minutos a que GitHub publique el sitio.

## Ejecución local

No requiere build ni dependencias. Cualquiera de estas opciones funciona:

- Abrir directamente `index.html` con doble clic.
- Servir la carpeta con un servidor estático sencillo:

```bash
python3 -m http.server 8000
# y abrir http://localhost:8000/
```

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

Código bajo licencia MIT (ver `LICENSE`).
