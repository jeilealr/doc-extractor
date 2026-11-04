"""Minimal stdlib argparse CLI. Same API as ``from doc_extractor import extract``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .api import extract, inspect_file
from .errors import DocExtractError
from .exporters import export_result
from .profiles import builtin_profile_ids, load_file
from .profiles.loader import installed_profile_ids
from .utils import Limits

MAIN_DESCRIPTION = """\
Extract text, tables and structured records from PDF and CSV files, locally.
Every value keeps a reference to where it came from (page, bbox, row, column)
and the source file's SHA-256. Nothing is sent over the network.

Run 'doc-extractor <command> --help' for the options of each command."""

MAIN_EPILOG = """\
examples:
  doc-extractor inspect statement.pdf
  doc-extractor extract paper.pdf --mode content --to markdown
  doc-extractor extract report.pdf --mode tables --preset preset.pdf.tables.borderless.v1
  doc-extractor extract export.csv --mode records --profile-file my_bank.yaml --to json
  doc-extractor profiles list

exit codes: 0 ok, 2 error (bad input/profile/write), 3 needs review (see 'extract --help')"""

INSPECT_DESCRIPTION = """\
Print a short JSON summary of a PDF or CSV without extracting or printing its content:
file name, format, size, SHA-256 and, for PDFs, the page count; for CSVs, the
delimiter guessed from the first 32 KiB. Use it to check that a file is readable
and to record its hash before extracting. 'inspect' has no further options."""

EXTRACT_DESCRIPTION = """\
Read a PDF or CSV and export what was found.

--mode picks WHAT to extract:
  all       everything available: PDF text and tables, or CSV cells (default)
  content   PDF text only, line by line, per page (not valid for CSV)
  tables    tables only: PDF tables detected on each page, or the CSV as one table
  records   named fields (date, amount, ...) mapped from tables by a source profile;
            requires --profile-file or --profile, otherwise exits 3

--preset / --profile-file / --profile pick HOW to extract (choose at most one):
  preset         built-in, generic settings, e.g. ruled vs borderless table detection
                 (list them with 'doc-extractor profiles list')
  profile-file   your own YAML describing one specific layout: how to recognise it,
                 which table settings to use and which columns to map to which fields
  profile        a source profile shipped by a trusted, installed Python package

--to picks the output FORMAT: json (full detail and provenance), markdown (readable
view), text (PDF text only), parquet or arrow (one file per table plus manifest.json,
needs --output and the optional 'tabular'/'arrow' extras)."""

EXTRACT_EPILOG = """\
examples:
  # readable text of a PDF
  doc-extractor extract paper.pdf --mode content --to markdown
  # tables from a PDF with visible cell borders (the default strategy)
  doc-extractor extract statement.pdf --mode tables --to markdown
  # tables from a PDF whose columns are only aligned text
  doc-extractor extract report.pdf --mode tables --preset preset.pdf.tables.borderless.v1
  # a Windows-exported CSV with ';' separators
  doc-extractor extract export.csv --encoding cp1252 --delimiter ';' --to markdown
  # typed records via a profile, saved to a file
  doc-extractor extract statement.pdf --mode records --profile-file bank.yaml \\
      --to json --output out/statement.json
  # Parquet files for Polars/DuckDB
  doc-extractor extract export.csv --mode tables --to parquet --output out/export_tables

notes:
  Without --output, json/markdown/text are printed to stdout. Existing output
  files or directories are never overwritten.
  Values are kept as the exact strings found in the source. Profiles can add a
  'normalized' value (ISO date, plain decimal string) next to each raw value.

exit codes:
  0  extraction finished
  2  error: unreadable or unsupported input, invalid profile, limit exceeded,
     missing optional dependency, or output already exists
  3  needs review: --mode records produced no records (no profile, or the profile
     did not match), or --strict was given and warnings were found"""

PROFILES_DESCRIPTION = """\
Work with extraction profiles.

  preset   generic, built-in settings shipped with doc-extractor (e.g. preset.pdf.text.v1)
  profile  YAML written for ONE specific source layout (e.g. one bank's statement);
           it declares how to recognise that layout and how to map its columns

See docs/source/reference/profile-spec.md for the YAML format and examples/ for samples."""


def make_parser() -> argparse.ArgumentParser:
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        prog="doc-extractor",
        description=MAIN_DESCRIPTION,
        epilog=MAIN_EPILOG,
        formatter_class=formatter,
    )
    parser.add_argument("--version", action="version", version=f"doc-extractor {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    inspect_cmd = sub.add_parser(
        "inspect",
        help="Show format, size, SHA-256 and page count without printing content",
        description=INSPECT_DESCRIPTION,
        formatter_class=formatter,
        epilog="example:\n  doc-extractor inspect ~/Documents/statement.pdf",
    )
    inspect_cmd.add_argument("path", type=Path, help="PDF or CSV file to inspect")

    cmd = sub.add_parser(
        "extract",
        help="Extract text, tables or records from a PDF or CSV",
        description=EXTRACT_DESCRIPTION,
        epilog=EXTRACT_EPILOG,
        formatter_class=formatter,
    )
    cmd.add_argument("path", type=Path, help="PDF or CSV file to read")
    what = cmd.add_argument_group("what and where")
    what.add_argument(
        "--mode",
        choices=("all", "content", "tables", "records"),
        default="all",
        help="What to extract (see above). Default: all",
    )
    what.add_argument(
        "--to",
        choices=("json", "markdown", "text", "parquet", "arrow"),
        default="json",
        help="Output format. Default: json",
    )
    what.add_argument(
        "--output",
        type=Path,
        metavar="PATH",
        help="New output file (json/markdown/text) or new directory "
        "(parquet/arrow). Default: print to stdout",
    )
    how = cmd.add_argument_group("how (choose at most one)")
    group = how.add_mutually_exclusive_group()
    group.add_argument(
        "--preset",
        metavar="ID",
        help="Built-in generic preset, e.g. preset.pdf.tables.borderless.v1",
    )
    group.add_argument(
        "--profile-file",
        type=Path,
        metavar="YAML",
        help="Your own YAML source profile (needed for --mode records)",
    )
    group.add_argument(
        "--profile", metavar="ID", help="Source profile from a trusted installed package"
    )
    csv_opts = cmd.add_argument_group("CSV options (override auto-detection and profiles)")
    csv_opts.add_argument(
        "--delimiter", choices=(",", ";", "tab", "|"), help="Column separator. Default: detected"
    )
    csv_opts.add_argument(
        "--encoding",
        choices=("utf-8", "utf-8-sig", "cp1252", "latin-1"),
        help="Text encoding. Default: UTF-8 (with or without BOM)",
    )
    csv_opts.add_argument(
        "--csv-header",
        choices=("first", "none"),
        help="'first': first row holds column names (default); 'none': all rows are data",
    )
    safety = cmd.add_argument_group("limits and review")
    safety.add_argument(
        "--max-bytes",
        type=int,
        default=Limits.max_bytes,
        metavar="N",
        help=f"Refuse inputs larger than N bytes. Default: {Limits.max_bytes}",
    )
    safety.add_argument(
        "--max-pages",
        type=int,
        default=Limits.max_pages,
        metavar="N",
        help=f"Refuse PDFs with more than N pages. Default: {Limits.max_pages}",
    )
    safety.add_argument(
        "--max-rows",
        type=int,
        default=Limits.max_rows,
        metavar="N",
        help=f"Refuse CSVs with more than N rows. Default: {Limits.max_rows}",
    )
    safety.add_argument(
        "--strict", action="store_true", help="Exit 3 if the result has warnings that need review"
    )

    profiles = sub.add_parser(
        "profiles",
        help="List presets, validate a YAML profile, or test it against a file",
        description=PROFILES_DESCRIPTION,
        formatter_class=formatter,
    )
    profile_cmd = profiles.add_subparsers(
        dest="profiles_command", required=True, metavar="<action>"
    )
    profile_cmd.add_parser(
        "list",
        help="List built-in presets and installed source profiles",
        description="Print the IDs usable with 'extract --preset' and 'extract --profile'.",
    )
    validate = profile_cmd.add_parser(
        "validate",
        help="Check a YAML profile against the V1 schema",
        description="Load a YAML profile, reject unknown or unsafe settings, and print its "
        "ID, version, format and SHA-256. Does not read any document.",
    )
    validate.add_argument("path", type=Path, help="YAML profile file")
    explain = profile_cmd.add_parser(
        "explain",
        help="Show whether a profile matches a file, without printing its values",
        description="Run the profile's match checks (required text, required table headers) "
        "against a document and print which ones pass. Exits 3 if it does not match. "
        "Use it to debug a profile before running 'extract --mode records'.",
        epilog="example:\n  doc-extractor profiles explain statement.pdf --profile-file bank.yaml",
        formatter_class=formatter,
    )
    explain.add_argument("path", type=Path, help="Input PDF or CSV")
    explain.add_argument(
        "--profile-file", type=Path, required=True, metavar="YAML", help="YAML profile to test"
    )
    # Built from the real subparsers so the overview can never drift from the actual flags.
    usages = [inspect_cmd.format_usage(), cmd.format_usage()] + [
        action.format_usage() for action in profile_cmd.choices.values()
    ]
    overview = "\n".join(
        "  " + u.strip().removeprefix("usage: ").replace("\n       ", "\n  ") for u in usages
    )
    parser.epilog = (
        f"command options (details: doc-extractor <command> --help):\n{overview}\n\n{MAIN_EPILOG}"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_file(args.path), ensure_ascii=False, indent=2))
            return 0
        if args.command == "profiles":
            if args.profiles_command == "list":
                print(
                    json.dumps(
                        {
                            "built_in_presets": builtin_profile_ids(),
                            "installed_source_profiles": installed_profile_ids(),
                        },
                        indent=2,
                    )
                )
                return 0
            if args.profiles_command == "validate":
                p = load_file(args.path)
                print(
                    json.dumps(
                        {
                            "valid": True,
                            "id": p.id,
                            "version": p.version,
                            "format": p.file_format,
                            "sha256": p.sha256,
                        },
                        indent=2,
                    )
                )
                return 0
            if args.profiles_command == "explain":
                p = load_file(args.profile_file)
                result = extract(args.path, mode="all", profile_file=args.profile_file)
                print(
                    json.dumps(
                        {
                            "profile": p.id,
                            "matched": not any(i.code == "LAYOUT_MISMATCH" for i in result.issues),
                            "checks": result.settings.get("profile_match_checks", []),
                            "operation_names": [s["op"] for s in p.pipeline],
                            "issues": [i.code for i in result.issues],
                        },
                        indent=2,
                    )
                )
                return 0 if not any(i.code == "LAYOUT_MISMATCH" for i in result.issues) else 3
        if args.command == "extract":
            limits = Limits(
                max_bytes=args.max_bytes, max_pages=args.max_pages, max_rows=args.max_rows
            )
            result = extract(
                args.path,
                mode=args.mode,
                preset=args.preset,
                profile=args.profile,
                profile_file=args.profile_file,
                delimiter="\t" if args.delimiter == "tab" else args.delimiter,
                encoding=args.encoding,
                csv_header=(None if args.csv_header is None else args.csv_header == "first"),
                limits=limits,
            )
            if (
                args.mode == "records"
                and not result.record_sets
                and args.to in {"parquet", "arrow"}
            ):
                print("No records mapped; use --to json for diagnostic details.", file=sys.stderr)
                return 3
            outcome = export_result(result, fmt=args.to, destination=args.output)
            if isinstance(outcome, str):
                sys.stdout.write(outcome)
            else:
                print(f"Output created: {outcome}", file=sys.stderr)
            if args.mode == "records" and not result.record_sets:
                print(
                    "No validated records; inspect warnings in JSON or manifest.", file=sys.stderr
                )
                return 3
            if args.strict and result.needs_review:
                print(
                    "Extraction needs review; inspect warnings in JSON or manifest.",
                    file=sys.stderr,
                )
                return 3
            return 0
        return 2
    except (DocExtractError, ValueError) as exc:
        print(f"doc-extractor: {exc}", file=sys.stderr)
        return 2
    except (BrokenPipeError, KeyboardInterrupt):
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
