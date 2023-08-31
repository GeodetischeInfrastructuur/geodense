import argparse
import io
import json
import re
from typing import Tuple
import fiona
from pyproj import CRS, Geod, Transformer

TRANFORM_CRS = "EPSG:4326"
ELLIPS = "WGS84"

def transform_point(source_crs:str, target_crs:str, val: Tuple[float,float]):
    source_crs_crs = CRS.from_authority(*source_crs.split(":"))
    target_crs_crs = CRS.from_authority(*target_crs.split(":"))
    transformer = Transformer.from_crs(source_crs_crs, target_crs_crs, always_xy=True)
    return transformer.transform(*val)

def get_distance_metric_lookup(src: fiona.Collection, crs: str):
    metric_lookup_table: dict[int, dict[int,float]] = {}
    for i, ft in enumerate(src):
        geom = ft.geometry

        distance_geom: dict[int,float] = {}
        for j in range(0,len(geom.coordinates)-1):
            a = geom.coordinates[j]
            b = geom.coordinates[j+1]
            a_t = transform_point(crs, TRANFORM_CRS, a)
            b_t = transform_point(crs, TRANFORM_CRS, b)
            g = Geod(ellps=ELLIPS)
            _,_,geod_dist = g.inv(*a_t,*b_t)
            distance_geom[j] = geod_dist
        metric_lookup_table[i] = distance_geom
    return metric_lookup_table

def interpolate_geodetic(a, b, max_segment_length, input_crs: str):
    a_t = transform_point(input_crs, TRANFORM_CRS, a)
    b_t = transform_point(input_crs, TRANFORM_CRS, b)
    g = Geod(ellps=ELLIPS)
    az12,_,dist = g.inv(*a_t,*b_t)
    npts = (dist//max_segment_length)
    r = g.fwd_intermediate(*a_t,az12,npts=npts,del_s=max_segment_length)
    return [transform_point(TRANFORM_CRS, input_crs, (lon,lat)) for lon,lat in zip(r.lons, r.lats)]


def add_point_recursively(geom: fiona.Geometry, coord_index:int, treshold:float, input_crs: str):
    coordinates = geom.coordinates
    a = coordinates[coord_index]
    b = coordinates[coord_index+1]
    p = interpolate_geodetic(a, b, treshold, input_crs)
    coordinates[coord_index+1:coord_index+1] = p
    geom = fiona.Geometry(coordinates=coordinates, type="LineString")
    return len(p)


def add_nodes_exceeding_treshold(metric_lookup_table: dict[int, dict[int,float]], treshold:float, src: fiona.Collection, dst: fiona.Collection, input_crs:str):
    for i, ft in enumerate(src):
        if i in metric_lookup_table:
            geom: fiona.Geometry = ft.geometry
            added_nodes = 0
            for j in metric_lookup_table[i]:
                metric = metric_lookup_table[i][j]
                if metric > treshold:
                    added_nodes+=add_point_recursively(geom, j+added_nodes, treshold, input_crs) # j+added_nodes, since we are inserting new nodes in the geometry, so shift the index by the nr of inserted nodes
            dst.write(
                fiona.Feature(geometry=geom, properties=ft.properties)
            )
        else:
            dst.write(
                ft
            )

def get_crs_from_json(json):
    if "crs" in json:
        pattern=r"^urn:ogc:def:crs:(.+)::(.+)$"
        crs_urn = json["crs"]["properties"]["name"]
        result = re.search(pattern, crs_urn)
        crs_auth = result.group(1)
        crs_identifier = result.group(2)
        return f"{crs_auth}:{crs_identifier}"
    return None


def add_nodes_geojson_dict(in_geojson:dict) -> dict:
    json_str = json.dumps(in_geojson)
    with io.BytesIO(b"") as out_f, io.BytesIO(json_str.encode("utf-8")) as in_f:
        add_nodes(in_f, out_f)
        return json.load(out_f)


def add_nodes(in_f, out_f, max_segment_length):
    with open(in_f, 'r') as in_file:
        data = json.load(in_file)
    crs = get_crs_from_json(data)
    if crs==None:
        raise ValueError("Unable to read CRS from input GeoJSON")

    with fiona.open(in_f, crs=crs) as src:
        profile = src.profile


        assert profile['schema']['geometry'] == "LineString", f"only LineString geometryTypes supported, received geometryType {profile['schema']['geometry']}" # TODO: add support for polygon geometry types
        with fiona.open(out_f, "w", **profile) as dst:
            metric_lookup = get_distance_metric_lookup(src, crs)
            add_nodes_exceeding_treshold(metric_lookup, max_segment_length, src, dst, crs)
        if not isinstance(out_f, str): # when string filepath:str is passed in, otherwise it is filelike object, then seek to start to enable reading again
            out_f.seek(0)


# TODO: improve handling stdout from function
def validate_nodes(in_f, max_segment_length):
    with fiona.open(in_f) as src:
        profile = src.profile
        assert profile['schema']['geometry'] == "LineString", f"only LineString geometryTypes supported, received geometryType {profile['schema']['geometry']}" # TODO: add support for polygon geometry types
        metric_lookup = get_distance_metric_lookup(src)

        result = {
            k_o: {
                k_i: v_i
                for k_i, v_i in v_o.items()
                if v_i > max_segment_length
            }
            for k_o, v_o in metric_lookup.items()
        }
        result = {k: v for k, v in result.items() if v } # remove empty dict items
        if len(result.keys()) == 0:
            return True
        else:
            report = ""
            for key in result:
                ft_report = f"line segment(s) exceeding max_segment_length: features[{key}].geometry.segments[{', '.join([str(x) for x  in result[key].keys()])}]\n"
                report+= ft_report
            print(report)
            return False

def fix_cmd(args):
    add_nodes(args.input_file,  args.output_file, args.max_segment_length)
    with open( args.output_file, 'r') as f:
        print(json.dumps(json.load(f), indent=4))


def validate_cmd(args):
    result =validate_nodes(args.input_file, args.max_segment_length)
    if result:
        exit(0)
    else:
        exit(1)


def main():
    parser = argparse.ArgumentParser(
                    prog='lange-lijnstukken-advies (lla)',
                    description='Geometry validation and fixing for CRS transformation between ETRS89 and RD',
                    epilog='')


    subparsers = parser.add_subparsers()
    fix_parser = subparsers.add_parser('fix')
    fix_parser.add_argument("input_file", type=str)
    fix_parser.add_argument("output_file" , type=str)
    fix_parser.add_argument("--max-segment-length","-m", type=int, default=200, help='max allowed segment length in meters')
    fix_parser.set_defaults(func=fix_cmd)

    validate_parser = subparsers.add_parser('validate')
    validate_parser.add_argument("input_file", type=str)
    validate_parser.add_argument("--max-segment-length","-m", type=int, default=200, help='max allowed segment length in meters')
    validate_parser.set_defaults(func=validate_cmd)
    parser._subparsers.title = "commands"
    args = parser.parse_args()
    args.func(args)

    ## cli args
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

if __name__ == "__main__":
    main()
