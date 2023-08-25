import argparse
import io
import json
import math
import fiona
from math import radians, cos, sin, asin, sqrt
from shapely import LineString, Point

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000 # Radius of earth in meters. Use 3956 for miles. Determines return value units.
    return c * r


def get_distance_metric_lookup(src: fiona.Collection):
    metric_lookup_table: dict[int, dict[int,float]] = {}
    for i, ft in enumerate(src):
        geom = ft.geometry

        distance_geom: dict[int,float] = {}
        for j in range(0,len(geom.coordinates)-1):
            a = geom.coordinates[j]
            b = geom.coordinates[j+1]
            dist = math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)
            distance_geom[j] = dist
        metric_lookup_table[i] = distance_geom
    return metric_lookup_table

def add_point_recursively(geom: fiona.Geometry, coord_index:int, treshold:float):
    coordinates = geom.coordinates
    a = coordinates[coord_index]
    b = coordinates[coord_index+1]

    p_point: Point= LineString([a, b]).interpolate(treshold)
    p = tuple(p_point.coords[0])
    if p == b:
        return
    else:
        coordinates.insert(coord_index+1,p)
        geom = fiona.Geometry(coordinates=coordinates, type="LineString")
        add_point_recursively(geom, coord_index+1, treshold)

def add_nodes_exceeding_treshold(metric_lookup_table: dict[int, dict[int,float]], treshold:float, src: fiona.Collection, dst: fiona.Collection):
    for i, ft in enumerate(src):
        if i in metric_lookup_table:
            geom: fiona.Geometry = ft.geometry
            for j in metric_lookup_table[i]:
                metric = metric_lookup_table[i][j]
                if metric > treshold:
                    add_point_recursively(geom, j, treshold) # TODO: check for evenly spacing of points
            dst.write(
                fiona.Feature(geometry=geom, properties=ft.properties)
            )
        else:
            dst.write(
                ft
            )


def main():
    parser = argparse.ArgumentParser(
                    prog='lange-lijnstukken-advies (lla)',
                    description='Geometrie controle en reparatie tbv CRS transformatie van ETRS89 en RD',
                    epilog='')

    parser.add_argument("input_file")
    parser.add_argument("output_file")
    args = parser.parse_args()

    ## cli args
    add_nodes(args.input_file,  args.output_file)
    with open( args.output_file, 'r') as f:
        print(json.dumps(json.load(f), indent=4))

    ## json args example

#     json_dict = json.loads('''
# {
# "type": "FeatureCollection",
# "name": "lijnen",
# "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::28992" } },
# "features": [
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 156264.906359842570964, 601302.588919493253343 ], [ 165681.964475793502061, 605544.313164469087496 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 197469.61676805181196, 578867.209674741141498 ], [ 208765.828605588612845, 585118.04955188173335 ], [ 214978.579108641220955, 579998.342453736579046 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 233912.686535700748209, 551369.281992391683161 ], [ 245564.067328312172322, 539677.288861267617904 ], [ 257328.60820127511397, 548003.141586222918704 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 210918.597344624489779, 478768.259641678829212 ], [ 232798.115296837408096, 470859.279475290386472 ], [ 236902.296422307554167, 456897.405543544969987 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 272182.597337315732148, 464381.992139570764266 ], [ 272438.267499944369774, 474055.442993962555192 ], [ 288261.877387178654317, 479765.751194861950353 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 93411.298435807053465, 474976.165362189291045 ], [ 98650.058117257722188, 467669.814339613658376 ], [ 113264.902673724602209, 477181.217063896707259 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 38816.458703284064541, 394689.020564639766235 ], [ 63378.898438817224815, 393203.124137901235372 ], [ 65707.721984194562538, 385797.269111435685772 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ -17084.258525104261935, 371192.313211922126357 ], [ -8383.290356248937314, 364984.209468487999402 ], [ -817.400946293841116, 353379.834339173045009 ], [ -14379.179841294622747, 348365.349435280484613 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 193638.184259118163027, 334806.62195219960995 ], [ 203576.012500613258453, 335883.131387825240381 ], [ 216054.644449666957371, 332046.926132246037014 ], [ 217133.905943340039812, 325105.827307404426392 ] ] } },
# { "type": "Feature", "properties": { }, "geometry": { "type": "LineString", "coordinates": [ [ 266300.890377873321995, 625765.27717069722712 ], [ 272285.73768137593288, 625675.086520252167247 ], [ 278210.402989279828034, 627931.178850010619499 ], [ 275738.835845820023678, 632895.496214323444292 ] ] } }
# ]
# }''')
#     new_json_dict = add_nodes_geojson_dict(json_dict)
#     print(json.dumps(new_json_dict, indent=4))


def add_nodes_geojson_dict(in_geojson:dict) -> dict:
    json_str = json.dumps(in_geojson)
    with io.BytesIO(b"") as out_f, io.BytesIO(json_str.encode("utf-8")) as in_f:
        add_nodes(in_f, out_f)
        return json.load(out_f)


def add_nodes(in_f, out_f):
    with fiona.open(in_f) as src:
        profile = src.profile
        assert profile['schema']['geometry'] == "LineString", f"only LineString geometryTypes supported, received geometryType {profile['schema']['geometry']}" # TODO: add support for polygon geometry types
        with fiona.open(out_f, "w", **profile) as dst:
            metric_lookup = get_distance_metric_lookup(src)
            add_nodes_exceeding_treshold(metric_lookup, 5000, src, dst)
        if not isinstance(out_f, str): # when string filepath:str is passed in, otherwise it is filelike object, then seek to start to enable reading again
            out_f.seek(0)

if __name__ == "__main__":
    main()
