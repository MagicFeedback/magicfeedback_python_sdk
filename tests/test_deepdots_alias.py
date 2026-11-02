"""The company was renamed MagicFeedback -> Deepdots, and both import names are
supported. These tests lock that contract in: they fail if someone adds a module
to ``magicfeedback_sdk`` without adding the matching ``deepdots_sdk`` mirror, or
if a mirror ever starts exporting a *copy* instead of the original object.

Unlike the rest of the suite these are pure unit tests — no network, no
credentials.
"""

import importlib
import pkgutil

import pytest

import magicfeedback_sdk


def _module_names():
    """Every submodule of magicfeedback_sdk, e.g. 'magicfeedback_sdk.api.feedback'."""
    return sorted(
        m.name
        for m in pkgutil.walk_packages(
            magicfeedback_sdk.__path__, prefix="magicfeedback_sdk."
        )
    )


def _mirror_of(name):
    return name.replace("magicfeedback_sdk", "deepdots_sdk", 1)


@pytest.mark.parametrize("name", _module_names())
def test_every_module_has_a_deepdots_mirror(name):
    """Adding magicfeedback_sdk.foo without deepdots_sdk.foo must fail here."""
    importlib.import_module(_mirror_of(name))


@pytest.mark.parametrize("name", _module_names())
def test_mirror_exports_the_same_objects(name):
    """A mirror must re-export the original object, never a copy or subclass."""
    original = importlib.import_module(name)
    mirror = importlib.import_module(_mirror_of(name))
    for attr in getattr(mirror, "__all__", []):
        assert getattr(original, attr) is getattr(mirror, attr), (
            f"{_mirror_of(name)}.{attr} is not the same object as {name}.{attr}"
        )


def test_client_class_alias_is_the_same_class():
    """All four import paths must resolve to one single class object."""
    from deepdots_sdk import Deepdots, MagicFeedback as NewPkgOldName
    from magicfeedback_sdk import Deepdots as OldPkgNewName, MagicFeedback

    assert len({Deepdots, MagicFeedback, NewPkgOldName, OldPkgNewName}) == 1


def test_deep_submodule_import_under_both_names():
    """The case a naive `from x import *` shim silently breaks."""
    from deepdots_sdk.api.feedback import FeedbackAPI as new
    from magicfeedback_sdk.api.feedback import FeedbackAPI as old

    assert old is new
