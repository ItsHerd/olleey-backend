"""Subscription renewal utilities for YouTube WebSub."""
import asyncio
import contextlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx

from config import settings
from services.supabase_db import supabase_service


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


async def renew_due_subscriptions(
    user_id: Optional[str] = None,
    renew_before_hours: int = 168,
) -> Dict[str, int]:
    """
    Renew subscriptions that are missing expiry or expiring soon.

    Returns counts: scanned, due, renewed, failed.
    """
    subscriptions = supabase_service.list_subscriptions(user_id=user_id)
    threshold = datetime.now(timezone.utc) + timedelta(hours=renew_before_hours)

    due: List[dict] = []
    for sub in subscriptions:
        expires_at = _parse_dt(sub.get("expires_at"))
        if expires_at is None or expires_at <= threshold:
            due.append(sub)

    renewed = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for sub in due:
            sub_id = sub.get("id")
            lease_seconds = int(sub.get("lease_seconds") or 2592000)
            topic = sub.get("topic")
            callback_url = sub.get("callback_url")
            if not sub_id or not topic or not callback_url:
                failed += 1
                continue

            attempts = int(sub.get("renewal_attempts") or 0) + 1
            supabase_service.update_subscription_status(
                sub_id,
                status="renew_requested",
                renewal_attempts=attempts,
            )

            form = {
                "hub.mode": "subscribe",
                "hub.topic": topic,
                "hub.callback": callback_url,
                "hub.lease_seconds": str(lease_seconds),
            }
            if sub.get("secret"):
                form["hub.secret"] = sub.get("secret")

            try:
                resp = await client.post(
                    settings.pubsubhubbub_hub_url,
                    data=form,
                    timeout=30.0,
                )
                resp.raise_for_status()
                # Hub challenge callback will finalize expires_at + active status.
                supabase_service.update_subscription_status(sub_id, status="renew_requested")
                renewed += 1
            except Exception as e:
                supabase_service.update_subscription_status(
                    sub_id,
                    status="renewal_failed",
                    renewal_attempts=attempts,
                    error=str(e),
                )
                failed += 1

    return {
        "scanned": len(subscriptions),
        "due": len(due),
        "renewed": renewed,
        "failed": failed,
    }


async def renewal_scheduler_loop(
    interval_minutes: int,
    renew_before_hours: int,
) -> None:
    """Background loop to periodically renew due subscriptions."""
    delay = max(60, int(interval_minutes) * 60)
    while True:
        try:
            summary = await renew_due_subscriptions(
                user_id=None,
                renew_before_hours=renew_before_hours,
            )
            print(
                "[SUB_RENEWAL] scanned={scanned} due={due} renewed={renewed} failed={failed}".format(
                    **summary
                )
            )
        except Exception as e:
            print(f"[SUB_RENEWAL] scheduler cycle failed: {str(e)}")
        await asyncio.sleep(delay)


async def stop_scheduler_task(task: Optional[asyncio.Task]) -> None:
    """Gracefully stop a running scheduler task."""
    if not task:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

