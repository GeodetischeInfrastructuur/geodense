# DOCS

## Densify command

See the following flowchart for a highlevel schematic overview of the `densify` functionality of `geodense`:

```mermaid
flowchart
    input([fa:fa-database input data]) --> p_1[get input-crs]
    p_1 --> d_1{input-crs<br>type and<br>densification method}
    d_1 -->|geographic and linear| output_error([fa:fa-exclamation-triangle error: cannot do linear densification<br> on data in a geographic crs])
    d_1 -->|geographic and geodesic| p_3
    d_1 -->|projected and linear| p_4[linear densify in input-crs]
    d_1 -->|projected and geodesic| p_2    
    p_4-->d_4
    p_3["geodesic densify with<br>ellipse of input-crs or base-geographic-crs"]
    p_2[convert to LatLon in<br>base-geographic-crs<br> of input-crs]
    p_2 --> p_3
    p_3-->d_4{input-crs<br>type and<br>densification method}
    d_4 -->|projected and geodesic| p_5[convert back to input-crs]
    p_5 -->output
    d_4 -->|geographic and geodesic| output([fa:fa-database output data])
    d_4 -->|projected and linear| output
    style output_error stroke: red,stroke-width:2px
    style output stroke: green,stroke-width:2px
```

## NSGI transformations

For correct Dutch (NSGI) coordinate transformations, geodense must run on the NSGI build of `pyproj`. This build ships a
modified `proj.db` containing the `NSGI` authority, plus the bundled grids. With stock `pyproj` from PyPI you get
generic PROJ behaviour, which is less accurate for the Netherlands.

The NSGI `pyproj` wheel is pinned in `pyproject.toml` via `[tool.uv.sources]` and is only available from the GitHub
releases page of the
[GeodetischeInfrastructuur/transformations](https://github.com/GeodetischeInfrastructuur/transformations/releases) repo
(`cp312` / `linux_x86_64` only). Use `uv` so this pin is honoured.

## Library usage note

`densify_geojson_object` (and `traverse_geojson_geometries`) mutate the input in place and return it; copy the object
first (e.g. `obj.model_copy(deep=True)`) if you need to retain the original.
