#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Away-mode notification stubs.

Send alerts when the user is away and motion is detected. Channel integrations
are placeholders until SMTP, push, and Telegram providers are configured.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger("the_eyes.away_notifier")


def send_email_alert(
    subject: str,
    body: str,
    *,
    to_address: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Send an email alert.

    Args:
        subject: Email subject line.
        body: Plain-text message body.
        to_address: Recipient override (defaults from config when implemented).
        metadata: Optional extra context (camera_id, snapshot path, etc.).
    """
    # TODO: Load SMTP/SendGrid settings from config; render HTML template; retry on failure.
    raise NotImplementedError("Email away alerts are not implemented yet")


def send_push_alert(
    title: str,
    message: str,
    *,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Send a mobile/web push notification.

    Args:
        title: Notification title.
        message: Short notification body.
        metadata: Optional payload for deep links (session_id, camera_id).
    """
    # TODO: Integrate FCM/APNs or web push subscription store; respect quiet hours.
    raise NotImplementedError("Push away alerts are not implemented yet")


def send_telegram_alert(
    message: str,
    *,
    chat_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Send a Telegram bot message.

    Args:
        message: Message text (Markdown when supported).
        chat_id: Target chat override (defaults from config when implemented).
        metadata: Optional inline keyboard / snapshot URL data.
    """
    # TODO: Call Telegram Bot API with bot token from secrets; attach snapshot if configured.
    raise NotImplementedError("Telegram away alerts are not implemented yet")


def _dispatch_channels(event: str, camera_id: str, session_id: Optional[str], snapshot_path: Optional[str]) -> None:
    """Try each notification channel; log TODO for unimplemented channels."""
    meta = {
        "event": event,
        "camera_id": camera_id,
        "session_id": session_id,
        "snapshot": snapshot_path,
    }
    subject = f"The Eyes: {event.replace('_', ' ')} on {camera_id}"
    body = f"Event: {event}\nCamera: {camera_id}\nSession: {session_id or 'n/a'}\nSnapshot: {snapshot_path or 'n/a'}"

    for name, fn, args, kwargs in (
        ("email", send_email_alert, (subject, body), {"metadata": meta}),
        ("push", send_push_alert, (subject, body), {"metadata": meta}),
        ("telegram", send_telegram_alert, (body,), {"metadata": meta}),
    ):
        try:
            fn(*args, **kwargs)
        except NotImplementedError:
            logger.warning("TODO: away %s via %s (camera=%s)", event, name, camera_id)


def notify_motion_started(
    camera_id: str,
    *,
    session_id: Optional[str] = None,
    snapshot_path: Optional[str] = None,
) -> None:
    """
    Notify away channels that motion has started on a camera.

    Args:
        camera_id: Canonical camera identifier.
        session_id: Motion session id for paired snapshots.
        snapshot_path: Project-relative path to the first snapshot.
    """
    # TODO: Skip if user is marked "home" (presence / schedule integration).
    _dispatch_channels("motion_started", camera_id, session_id, snapshot_path)


def notify_motion_ended(
    camera_id: str,
    *,
    session_id: Optional[str] = None,
    snapshot_path: Optional[str] = None,
) -> None:
    """
    Notify away channels that motion has ended on a camera.

    Args:
        camera_id: Canonical camera identifier.
        session_id: Motion session id for paired snapshots.
        snapshot_path: Project-relative path to the last snapshot.
    """
    # TODO: Optionally send summary only for sessions longer than a threshold.
    _dispatch_channels("motion_ended", camera_id, session_id, snapshot_path)
