# Deepdots Python SDK

`deepdots` is the Deepdots name for the Python SDK formerly published as
**magicfeedback**. Installing it pulls in the `magicfeedback` distribution,
which ships the actual code.

```bash
pip install deepdots
```

```python
from deepdots_sdk import Deepdots

client = Deepdots("email", "password")
```

The original names remain fully supported — `magicfeedback_sdk` and the
`MagicFeedback` class refer to the very same objects, so existing code needs no
changes.

Source, documentation and issues:
https://github.com/MagicFeedback/magicfeedback_python_sdk
