import json

import tomli
from hypothesis import given
from hypothesis import strategies as st

from .. import tomli_w

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore

toml_strategy = st.recursive(
    st.booleans()
    | st.floats(allow_infinity=False, allow_nan=False)
    | st.text()
    | st.integers(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=20,
)
table_strategy = st.dictionaries(st.text(), toml_strategy)


@given(data=table_strategy)
def test_convert(data):
    # make sure we have valid json (if this fails the test is broken, not our code)
    json.dumps(data, indent=2)
    # make sure we can generate the data-structure
    toml = tomli_w.dumps(data)
    # make sure it is valid toml
    tomli.loads(toml)
    # if tomllib is avaible compare to it
    if tomllib:  # pragma: no cover
        tomllib.loads(toml)
