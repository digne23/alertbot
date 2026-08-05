"""Kept for backwards compatibility with the Sprint-5 layout.

The Firebase implementation now lives in `app/services/notifiers/firebase.py`
so every channel sits behind the same interface. Import from there.
"""

from app.services.notifiers.firebase import FirebaseNotifier, active_tokens

__all__ = ["FirebaseNotifier", "active_tokens"]
