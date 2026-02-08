"""CLI commands for managing Qdrant collection."""

import argparse

from .embedding_service import generate_embedding
from .models import Ad, AdPolicy, AdTargeting
from .qdrant_service import create_collection, delete_collection, get_collection_info, upsert_ad


def create_sample_ads() -> None:
    """Create and insert sample ads into the collection."""
    sample_ads = [
        Ad(
            ad_id="sample-ad-001",
            advertiser_id="sample-advertiser-tech",
            title="Learn Python Today",
            body="Master Python programming with our interactive courses. Build real-world projects and advance your career.",
            cta_text="Start Learning",
            landing_url="https://example.com/python",
            targeting=AdTargeting(
                topics=["programming", "python", "education", "technology"],
                locale=["en-US"],
                verticals=["education", "technology"],
            ),
            policy=AdPolicy(sensitive=False, age_restricted=False),
        ),
        Ad(
            ad_id="sample-ad-002",
            advertiser_id="sample-advertiser-edu",
            title="Online Courses for Everyone",
            body="Discover thousands of online courses in business, design, technology, and more. Learn at your own pace.",
            cta_text="Browse Courses",
            landing_url="https://example.com/courses",
            targeting=AdTargeting(
                topics=["education", "online learning", "courses", "skills"],
                locale=["en-US"],
                verticals=["education"],
            ),
            policy=AdPolicy(sensitive=False, age_restricted=False),
        ),
        Ad(
            ad_id="sample-ad-003",
            advertiser_id="sample-advertiser-shop",
            title="Shop the Latest Trends",
            body="Find amazing deals on fashion, electronics, home goods, and more. Free shipping on orders over $50.",
            cta_text="Shop Now",
            landing_url="https://example.com/shop",
            targeting=AdTargeting(
                topics=["shopping", "fashion", "deals", "e-commerce"],
                locale=["en-US"],
                verticals=["retail", "e-commerce"],
            ),
            policy=AdPolicy(sensitive=False, age_restricted=False),
        ),
        Ad(
            ad_id="sample-ad-004",
            advertiser_id="sample-advertiser-fitness",
            title="Get Fit This Year",
            body="Join thousands of members achieving their fitness goals. Personalized workout plans and nutrition guidance.",
            cta_text="Start Free Trial",
            landing_url="https://example.com/fitness",
            targeting=AdTargeting(
                topics=["fitness", "health", "workout", "wellness"],
                locale=["en-US"],
                verticals=["health", "fitness"],
            ),
            policy=AdPolicy(sensitive=False, age_restricted=False),
        ),
        Ad(
            ad_id="sample-ad-005",
            advertiser_id="sample-advertiser-finance",
            title="Invest in Your Future",
            body="Start investing with as little as $1. Build wealth with low-cost index funds and expert guidance.",
            cta_text="Get Started",
            landing_url="https://example.com/invest",
            targeting=AdTargeting(
                topics=["investing", "finance", "wealth", "savings"],
                locale=["en-US"],
                verticals=["finance"],
            ),
            policy=AdPolicy(sensitive=False, age_restricted=False),
        ),
    ]

    print("Adding sample ads to collection...")
    for ad in sample_ads:
        embedding = generate_embedding(ad.embedding_text)
        upsert_ad(ad, embedding)
        print(f"  Added: {ad.ad_id} - {ad.title}")
    print(f"Successfully added {len(sample_ads)} sample ads.")


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
    subparsers.add_parser("seed", help="Add sample ads to the collection for testing")

    args = parser.parse_args()

    if args.command == "create":
        create_collection(dimension=args.dimension)
    elif args.command == "delete":
        delete_collection()
    elif args.command == "info":
        info = get_collection_info()
        print(f"Collection: {info['name']}")
        print(f"Status: {info['status']}")
        print(f"Points count: {info['points_count']}")
        print(f"Indexed vectors count: {info['indexed_vectors_count']}")
    elif args.command == "seed":
        create_sample_ads()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
