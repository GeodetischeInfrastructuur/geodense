import argparse
from nsgi_dense.lib import check_density, densify_geospatial_file, get_hr_report


def densify_cmd(args):
    input_file = args.input_file
    output_file = args.output_file
    max_segment_length = args.max_segment_length
    layer = args.layer
    densify_in_projection = args.densify_in_projection
    densify_geospatial_file(input_file, output_file, max_segment_length, layer, densify_in_projection)


def check_density_cmd(args):
    result = check_density(args.input_file, args.max_segment_length, args.layer)
    hr_report = get_hr_report(result, args.max_segment_length)
    if len(result) == 0:
        exit(0)
    else:
        print(hr_report)
        exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="dense",
        description="Check density of, and densify geometries using the geodetic great circle calculation for accurate CRS transformations",
        epilog="Created by https://www.nsgi.nl/",
    )

    subparsers = parser.add_subparsers()
    densify_parser = subparsers.add_parser("densify")
    densify_parser.add_argument("input_file", type=str)
    densify_parser.add_argument("output_file", type=str)
    densify_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=int,
        default=200,
        help="max allowed segment length in meters",
    )
    densify_parser.add_argument(
        "--layer",
        "-l",
        type=str,
        help="layer to use in multi-layer geospatial input files",
    )
    densify_parser.add_argument(
        "--densify-in-projection",
        "-p",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="densify using source projection,  not applicable when source crs is geographic",
    )

    densify_parser.set_defaults(func=densify_cmd)

    check_density_parser = subparsers.add_parser("check-density")
    check_density_parser.add_argument("input_file", type=str)
    check_density_parser.add_argument(
        "--max-segment-length",
        "-m",
        type=int,
        default=200,
        help="max allowed segment length in meters",
    )
    check_density_parser.add_argument(
        "--layer",
        "-l",
        type=str,
        help="layer to use in multi-layer geospatial input files",
    )
    check_density_parser.set_defaults(func=check_density_cmd)
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