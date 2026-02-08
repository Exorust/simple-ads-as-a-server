"""CLI commands for managing the ads collection (Control Plane)."""

import argparse
import json
import sys
from pathlib import Path

from .app.index_service import IndexService
from .models import Ad

# Default path to demo ads JSON (project root / data / test_ads.json)
_DEFAULT_ADS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "test_ads.json"


def load_ads_from_file(path: Path) -> list[Ad]:
    """Load ads from a JSON file. Raises on missing file or invalid JSON/schema."""
    if not path.exists():
        print(f"Error: ads file not found: {path}", file=sys.stderr)
        print("Create data/test_ads.json or pass --file <path>.", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        print("Error: JSON file must contain a list of ad objects.", file=sys.stderr)
        sys.exit(1)
    ads: list[Ad] = []
    for i, item in enumerate(raw):
        try:
            ads.append(Ad.model_validate(item))
        except Exception as e:
            print(f"Error: invalid ad at index {i}: {e}", file=sys.stderr)
            sys.exit(1)
    return ads


def seed_ads(file_path: Path | None = None) -> None:
    """Load demo ads from a JSON file and upsert them via IndexService."""
    path = file_path if file_path is not None else _DEFAULT_ADS_PATH
    ads = load_ads_from_file(path)
    print(f"Adding {len(ads)} ads from {path}...")
    svc = IndexService()
    count = svc.upsert_ads(ads)
    print(f"Successfully added {count} ads.")


def main():
    parser = argparse.ArgumentParser(description="Manage Qdrant ad collection")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create collection command
    create_parser = subparsers.add_parser("create", help="Create the Qdrant collection")
    create_parser.add_argument(
        "--dimension",
        type=int,
        default=384,
        help="Embedding dimension (default: 384 for BAAI/bge-small-en-v1.5)",
    )

    # Delete collection command
    subparsers.add_parser("delete", help="Delete the Qdrant collection")

    # Info command
    subparsers.add_parser("info", help="Show collection information")

    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Load demo ads from a JSON file and add to the collection")
    seed_parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help=f"Path to JSON file with ads (default: {_DEFAULT_ADS_PATH})",
    )

    args = parser.parse_args()
    svc = IndexService()

    if args.command == "create":
        result = svc.ensure_collection(dimension=args.dimension)
        if result["created"]:
            print(f"Created collection: {result['name']}")
        else:
            print(f"Collection already exists: {result['name']}")
    elif args.command == "delete":
        svc.delete_collection()
        print("Deleted collection.")
    elif args.command == "info":
        info = svc.collection_info()
        print(f"Collection: {info['name']}")
        print(f"Status: {info['status']}")
        print(f"Points count: {info['points_count']}")
        print(f"Indexed vectors count: {info['indexed_vectors_count']}")
    elif args.command == "seed":
        seed_ads(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
