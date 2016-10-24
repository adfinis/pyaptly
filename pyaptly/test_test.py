"""Testing the testing tools"""

import os
import random
import sys
import unittest

from . import test

if not sys.version_info < (2, 7):  # pragma: no cover
    import hypothesis.strategies as st
    from hypothesis import example, given  # noqa


if sys.version_info < (2, 7):  # pragma: no cover
    import mock
    given = mock.MagicMock()  # noqa
    example = mock.MagicMock()  # noqa
    st = mock.MagicMock()  # noqa

_test_base = os.path.dirname(
    os.path.abspath(__file__)
).encode("UTF-8")

yml_st = st.recursive(
    st.floats(-1, 1) | st.booleans() |
    st.text() | st.none() | st.binary(),
    lambda children: st.lists(
        children, average_size=5, max_size=10
    ) | st.dictionaries(
        st.text(),
        children,
        average_size=5,
        max_size=10
    ),
    max_leaves=30
)


class TestTest(unittest.TestCase):
    def test_read_yml(self):
        """Test if reading yml files works without errors."""
        path = os.path.join(
            _test_base,
            b"merge.yml"
        )
        yml = test.read_yml(path)
        assert yml['mirror']['fakerepo01'] is not None

    def test_delete(self):
        """Test if merges can delete fields"""
        path = os.path.join(
            _test_base,
            b"delete_merge.yml"
        )
        yml = test.read_yml(path)
        assert 'fakerepo01' not in yml['mirror']

    @test.hypothesis_min_ver
    @given(yml_st, yml_st, st.random_module())
    @example({'1': 'Huhu'}, {'1': 'None'}, st.random_module())
    def test_merge(self, a, b, rand):  # pragma: no cover
        """Test if merge has the expected result."""
        res  = test.merge(a, b)
        for _ in range(10):
            path, data_b = self.rand_path(b)
            if data_b == 'None':
                error = False
                try:
                    data_res = self.get_path(path, res)
                except KeyError:
                    error = True
                assert error
            else:
                data_res = self.get_path(path, res)
                assert data_res == data_b
            if isinstance(a, dict) and isinstance(b, dict):
                path, data_a = self.rand_path(a)
                try:
                    data_res     = self.get_path(path, res)
                    if data_a != data_res:  # pragma: no cover
                        data_b = self.get_path(path, b)
                        assert data_res == data_b
                except (TypeError, KeyError):
                    pass

    def get_path(self, path, data):  # pragma: no cover
        for i in path:
            data = data[i]
        if isinstance(data, dict):
            return None
        return data

    def rand_path(self, data):  # pragma: no cover
        path = []
        while True:
            if isinstance(data, dict):
                keys = list(data.keys())
                if keys:
                    k = random.choice(list(data.keys()))
                    path.append(k)
                    data = data[k]
                else:
                    return path, None
            else:
                break
        return path, data
