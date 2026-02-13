#!/usr/bin/env python3
"""Renew YouTube WebSub subscriptions expiring soon."""
import argparse
import asyncio

from services.subscription_renewal import renew_due_subscriptions


async def main() -> None:
    parser = argparse.ArgumentParser(description="Renew due WebSub subscriptions")
    parser.add_argument(
        "--renew-before-hours",
        type=int,
        default=168,
        help="Renew subscriptions expiring within this many hours (default: 168)",
    )
    args = parser.parse_args()

    summary = await renew_due_subscriptions(
        user_id=None,
        renew_before_hours=args.renew_before_hours,
    )
    print(
        f"scanned={summary['scanned']} due={summary['due']} "
        f"renewed={summary['renewed']} failed={summary['failed']}"
    )


if __name__ == "__main__":
    asyncio.run(main())

