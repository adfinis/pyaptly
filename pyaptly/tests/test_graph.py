"""Testing dependency graphs."""
import random
from functools import partial
from typing import Union

from hypothesis import given, settings
from hypothesis import strategies as st

from .. import command

# Disable the deadline globally for all tests
settings.register_profile("my_profile", deadline=None)
settings.load_profile("my_profile")

RES_COUNT = 20

range_intagers_st = st.integers(min_value=0, max_value=RES_COUNT)


@st.composite
def provide_require_st(draw, filter_=True):
    """Build a random command tree, to test."""
    commands = draw(range_intagers_st)
    provides = draw(
        st.lists(
            st.lists(range_intagers_st, max_size=10),
            min_size=commands,
            max_size=commands,
        ),
    )
    is_func = draw(st.lists(st.booleans(), min_size=commands, max_size=commands))
    provides_set = set()
    for cmd in provides:
        provides_set.update(cmd)
    requires = []
    if provides_set:
        for cmd in provides:
            if cmd:
                max_prov = max(cmd)
            else:
                max_prov = 0
            if filter_:
                provides_filter = set([x for x in provides_set if x > max_prov])
            else:
                provides_filter = provides_set
            if provides_filter:
                sample = st.sampled_from(list(provides_filter))
                requires.append(draw(st.lists(sample, max_size=10)))
            else:
                requires.append([])
    else:
        requires = [[]] * commands
    return (provides, requires, is_func)


def print_example():  # pragma: no cover
    """Print an example for debugging."""
    example = provide_require_st().example()
    print(
        """
    digraph g {
         label="Command graph";
         graph [splines=line];
    """
    )
    for i in range(len(example[0])):
        print("    c%03d [shape=triangle];" % i)
        for provides in example[0][i]:
            print("    c%03d -> r%03d;" % (i, provides))
        for requires in example[1][i]:
            print("    r%03d -> c%03d;" % (requires, i))

    print("}")


@given(provide_require_st(), st.random_module())
def test_graph_basic(tree, rnd):
    """Test our test method, create a basic graph using hypthesis.

    And run some basic tests against it.
    """
    run_graph(tree)


@given(provide_require_st(False), st.random_module())
def test_graph_cycles(tree, rnd):
    """Test reacts correctly on trees with cycles."""
    try:
        run_graph(tree)
    except ValueError as e:  # pragma: no cover
        if "Commands with unresolved deps" not in e.args[0]:
            raise e


@given(provide_require_st(), provide_require_st(), st.random_module())
def test_graph_island(tree0, tree1, rnd):  # pragma: no cover
    """Test with two independant graphs which can form a island."""
    tree = (tree0[0] + tree1[0], tree0[1] + tree1[1], tree0[2] + tree1[2])
    run_graph(tree)


def run_graph(tree):
    """Run the test."""
    commands = []
    index = list(range(len(tree[0])))
    random.shuffle(index)
    cmd: Union[command.Command, command.FunctionCommand]
    for i in index:

        def dummy(i):  # pragma: no cover
            return i

        if tree[2][i]:
            func = partial(dummy, i)
            func.__name__ = dummy.__name__  # type: ignore
            cmd = command.FunctionCommand(func)
        else:
            cmd = command.Command([str(i)])
        for provides in tree[0][i]:
            cmd.provide("virtual", provides)
        for requires in tree[1][i]:
            cmd.require("virtual", requires)
        commands.append(cmd)
    ordered = command.Command.order_commands(commands)
    assert len(commands) == len(ordered)
    provided: set[tuple[str, str]] = set()
    for cmd in ordered:
        assert cmd._requires.issubset(provided)
        provided.update(cmd._provides)
