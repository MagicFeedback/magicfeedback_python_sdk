# Developer guide

Internal guide for Deepdots developers working on this SDK: how the repo is laid
out, how to run the tests, and how to cut and publish a release.

For SDK *usage*, see [README.md](README.md).

## Quick reference

| Task | Command |
|---|---|
| Install for development | `./setup.sh` (`pip install -e .`) |
| Run all tests | `./test.sh` |
| Run only tests needing no credentials | `pytest tests/test_deepdots_alias.py tests/test_request_done_message.py` |
| Build locally | `./build.sh` |
| Publish the SDK to PyPI | `./publish.sh` |
| Publish the `deepdots` bridge | `./publish_deepdots.sh` |

## Repo layout

```
src/magicfeedback_sdk/    the implementation
src/deepdots_sdk/         re-export mirror under the new company name
packages/deepdots/        the `deepdots` bridge distribution (metadata only)
tests/                    pytest suite (see "Tests" below)
examples/                 runnable usage examples
publish.sh                publishes the SDK
publish_deepdots.sh       publishes the bridge
```

## The two names

MagicFeedback was renamed **Deepdots**. Both names work everywhere and refer to
the same objects. There are three independent layers:

| Layer | Current name | Original name |
|---|---|---|
| PyPI distribution | `deepdots` | `magicfeedback` |
| Import package | `deepdots_sdk` | `magicfeedback_sdk` |
| Client class | `Deepdots` | `MagicFeedback` |

`pip install deepdots` and `pip install magicfeedback` both end up installing
the same code — `deepdots` is a metadata-only bridge that depends on
`magicfeedback`, which is the distribution that actually ships both import
packages.

### Rule when adding a module

**The implementation lives in `magicfeedback_sdk`.** `deepdots_sdk` contains
only thin re-export modules. If you add `magicfeedback_sdk/api/foo.py`, you must
also add `deepdots_sdk/api/foo.py`:

```python
"""Re-export of :mod:`magicfeedback_sdk.api.foo` under the Deepdots name."""

from magicfeedback_sdk.api.foo import FooAPI

__all__ = ["FooAPI"]
```

`tests/test_deepdots_alias.py` fails if you forget, and also fails if a mirror
ever exports a *copy* rather than the original object. Explicit re-exports are
used deliberately rather than `sys.modules` aliasing, so that mypy, pyright and
IDE autocompletion resolve both names.

## Tests

`pyproject.toml` sets `pythonpath = ["src"]`, so pytest imports the working tree
directly — no `pip install -e .` needed to run the suite.

Two kinds of tests live here, and the difference matters:

**Unit tests** — no network, no credentials, safe to run anywhere:

- `tests/test_deepdots_alias.py`
- `tests/test_request_done_message.py`

**Integration tests** — these hit the real API and create real data. They need
`MF_EMAIL` / `MF_PASSWORD` in `.env`, and the Datastore ones additionally need
Google Application Default Credentials (`gcloud auth application-default
login`):

- `test_apikey.py`, `test_campaign.py`, `test_contact.py`,
  `test_datastore_token.py`, `test_feedback_answers_array.py`,
  `test_feedback_create.py`, `test_integrations_questions.py`

`./test.sh` runs everything, so it will fail without credentials. In CI, or when
you only want a quick check, run the two unit files.

## Branches and tags

**Tags are the record of what shipped. Branches are where work happens.**

Every release is tagged, and the publish scripts create the tag for you — you
never tag by hand:

| Tag | Marks |
|---|---|
| `v1.0.19` | the commit published as `magicfeedback` 1.0.19 |
| `deepdots-v1.0.19` | the commit published as the `deepdots` bridge 1.0.19 |

The two are namespaced separately because the SDK and the bridge are versioned
independently.

Work happens on a branch named after the version being prepared (`v1.0.20`).
Note that a branch is *not* a reliable record of a release: it keeps moving as
work lands on it. `v1.0.18` is the cautionary example — 1.0.19 was cut from the
same branch, so its tip no longer contains the code that shipped as 1.0.18. A
tag cannot drift like that, which is why the tag is what you trust when you need
to know exactly what a released version contained.

Tags start at 1.0.19; earlier releases predate this convention and are not
tagged.

To check out exactly what a version shipped:

```bash
git checkout v1.0.19
```

## Releasing a new SDK version

1. **Bump the version in both files.** `pyproject.toml` and `setup.py` each
   carry it and must agree:

   ```bash
   # pyproject.toml -> version = "1.0.19"
   # setup.py       -> version="1.0.19",
   ```

   Only `pyproject.toml` actually affects the build (see "Gotchas"), but leaving
   `setup.py` behind makes the repo lie about its own version.

2. **Work on a version branch.** The convention here is one branch per release,
   named after it: `v1.0.19`.

3. **Run the tests.**

4. **Commit everything.** `publish.sh` refuses to run against a dirty working
   tree, because the tag it creates has to match the code that goes to PyPI.

5. **Publish:**

   ```bash
   ./publish.sh
   ```

   The script builds sdist + wheel, uploads only that version's two files, then
   tags the commit `vX.Y.Z` and pushes the tag. It refuses to run if the version
   is already on PyPI, or if the tag already exists locally or on origin.

   The tag is created *after* the upload succeeds, so a tag always means "this
   really shipped". If the upload works but the tag push fails, the script says
   so and tells you the command to retry — the release itself is fine.

6. **Open a PR into `main`.** `main` is a protected branch — direct pushes are
   rejected, so the merge must go through a pull request.

### Do you also need to republish the bridge?

Usually **no**. `packages/deepdots/pyproject.toml` declares
`magicfeedback>=1.0.18`, a lower bound rather than a pin, so `pip install
deepdots` always resolves to the newest SDK without the bridge being touched.

Republish it (with `./publish_deepdots.sh`, after bumping its own version) only
when the bridge's own metadata changes — its description, its URLs, or the
minimum SDK version it requires.

## PyPI credentials

Uploads authenticate with an API token from
https://pypi.org/manage/account/token/, stored in your system keyring:

```bash
python3 -m keyring set https://upload.pypi.org/legacy/ __token__
```

Paste the token (it starts with `pypi-`) when prompted. `twine` picks it up
automatically; no `~/.pypirc` needed.

## Gotchas

**Publishing is irreversible.** Once a version is uploaded, that number is burnt
forever — PyPI never allows the same filename to be re-uploaded, even if you
delete the release. A mistake always costs a new version number. Both publish
scripts check PyPI up front and abort rather than let you find out afterwards.

**`setup.py` is redundant.** When a `[project]` table is present in
`pyproject.toml`, setuptools takes all metadata from it and *ignores* the
`name`, `version` and `install_requires` in `setup.py`. This bit us before: up
to 1.0.16 the dependencies were declared only in `setup.py`, so the published
wheels had no `Requires-Dist` at all and pip installed nothing alongside the
SDK. Keep the two in sync, or delete `setup.py`.

**`publish_test.sh` is stale.** It still calls `python setup.py sdist
bdist_wheel` and uploads `dist/*` to TestPyPI, which is exactly the pattern
`publish.sh` was fixed to avoid. Don't copy from it.

**Write distribution names lowercase.** `magicfeedback` and `deepdots`, never
`MagicFeedback`. This is the packaging convention, and mixing the two styles was
a recurring source of confusion. It is purely cosmetic: PyPI normalises case
(PEP 503), so `pip install magicfeedback`, `MagicFeedback` and `MAGICFEEDBACK`
all resolve to the same project, and the built wheel filename has always been
lowercase regardless. Note the normalisation covers case but *not* separators —
`pip install Magic-Feedback` fails, because the added hyphen makes it a
different name entirely.

Python class names are unaffected: `MagicFeedback` and `Deepdots` stay
CamelCase, because they are Python identifiers, not distribution names.

**`dist/` is no longer wiped.** `publish.sh` uploads only the current version's
files, so old local builds accumulate there harmlessly. The directory is
gitignored.
