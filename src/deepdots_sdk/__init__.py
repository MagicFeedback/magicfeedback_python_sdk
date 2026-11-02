"""Deepdots Python SDK.

``Deepdots`` is the current name of the company formerly called MagicFeedback.
This package is the forward-looking import name; the implementation still lives
in :mod:`magicfeedback_sdk` and is re-exported here module by module, so both
import paths expose the very same objects. Existing code importing
``magicfeedback_sdk`` keeps working unchanged.
"""

from magicfeedback_sdk.client import Deepdots, MagicFeedback

__all__ = ["Deepdots", "MagicFeedback"]
