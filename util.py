import argparse
import json
import sys


def gen_code_cov_badge_cmd(args):
    input_filepath = args.input_file
    output_filepath = args.output_file

    def get_coverage_color(percentage) -> str:
        color_map = {0: "red", 50: "orange", 80: "yellow", 90: "green"}
        coverage_level = sum(level <= percentage for level in color_map) - 1
        color_map_key = list(color_map.keys())[coverage_level]
        return color_map[color_map_key]

    with open(input_filepath) as in_f:
        data = json.load(in_f)
        percentage = data["totals"]["percent_covered"]
        percent_display = data["totals"]["percent_covered_display"]
        color = get_coverage_color(percentage)
        coverage_badge_config = f"""{{
    "schemaVersion": 1,
    "label": "code coverage",
    "message": "{percent_display}%",
    "color": "{color}"
}}"""
        with open(output_filepath, "w") as out_f:
            out_f.write(coverage_badge_config)


def main():
    parser = argparse.ArgumentParser(
        description="CLI tool to perform utility tasks in repository",
    )

    subparsers = parser.add_subparsers()
    cov_badge_parser = subparsers.add_parser(
        "gen-cov-badge",
        description="Generate code coverage badge config",
    )
    cov_badge_parser.add_argument("input_file", type=str)
    cov_badge_parser.add_argument("output_file", type=str)
    cov_badge_parser.set_defaults(func=gen_code_cov_badge_cmd)
    args = parser.parse_args()

    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
