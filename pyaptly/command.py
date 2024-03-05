"""Commands with dependencies."""
import collections
import logging

from frozendict import frozendict

from . import state_reader, util

lg = logging.getLogger(__name__)


class Command(object):
    """Repesents a system command and is used to resolve dependencies.

    :param cmd: The command as list, one item per argument
    :type  cmd: list
    """

    pretend_mode = False

    def __init__(self, cmd: list[str]):
        assert isinstance(cmd, list)
        self.cmd: list[str] = cmd
        self._requires: set[tuple[str, str]] = set()
        self._provides: set[tuple[str, str]] = set()
        self._finished: bool = False
        self._known_dependency_types = (
            "snapshot",
            "mirror",
            "repo",
            "publish",
            "virtual",
        )
        self.frozen = False

    def get_provides(self):  # pragma: no cover
        """Return all provides of this command.

        :rtype: set()
        """
        return self._provides

    def append(self, argument):
        """Append additional arguments to the command.

        :param argument: String argument to append
        :type  argument: str
        """
        assert str(argument) == argument
        if self.frozen:  # pragma: no cover
            raise RuntimeError("Do not modify frozen Command")
        self.cmd.append(argument)

    def require(self, type_, identifier):
        """Require a dependency for this command.

        :param      type_: Type or category of the dependency ie. snapshot
        :type       type_: str
        :param identifier: Identifier of the dependency for example name of a
                           snapshot
        :type  identifier: usually str
        """
        if self.frozen:  # pragma: no cover
            raise RuntimeError("Do not modify frozen Command")
        assert type_ in (
            self._known_dependency_types
            + ("any",)
            + state_reader.SystemStateReader.known_dependency_types
        )
        self._requires.add((type_, str(identifier)))

    def provide(self, type_, identifier):
        """Provide a dependency for this command.

        :param      type_: Type or category of the dependency ie. snapshot
        :type       type_: str
        :param identifier: Identifier of the dependency for example name of a
                           snapshot
        :type  identifier: usually str
        """
        if self.frozen:  # pragma: no cover
            raise RuntimeError("Do not modify frozen Command")
        assert type_ in self._known_dependency_types
        self._provides.add((type_, str(identifier)))

    def execute(self):
        """Execute the command. Return the return value of the command.

        :rtype: integer
        """
        if self._finished:  # pragma: no cover
            return self._finished

        if not Command.pretend_mode:
            lg.debug("Running command: %s", " ".join(self.cmd))
            # It seems the intention of the original code is to a redo a command if it
            # scheduled multiple times and fails the first time. But there is also:

            # `commands = set([c for c in commands if c is not None])`

            # which prevents that. I guess the feature is currently not needed.
            # So I decided to change that. For now we fail hard if a `Command` fails.
            # I guess we will see in production what happens.
            util.run_command(self.cmd, check=True)
        else:
            lg.info("Pretending to run command: %s", " ".join(self.cmd))
        self._finished = True

        return self._finished

    def repr_cmd(self):
        """Return repr of the command.

        :rtype: str
        """
        return repr(self.cmd)

    def _freeze_common(self):
        if not self.frozen:
            self.frozen = True
            # manually checking using self.frozen
            self._requires = frozenset(self._requires)  # type: ignore
            self._provides = frozenset(self._provides)  # type: ignore

    def freeze(self):
        """Freeze the class to make it hashable."""
        self._freeze_common()
        # manually checking using self.frozen
        self.cmd = tuple(self.cmd)  # type: ignore

    def _hash_base(self):
        self.freeze()
        return hash((type(self), self._requires, self._provides))

    def _eq_base(self, other):
        self.freeze()
        other.freeze()
        return (
            type(self) is type(other)
            and self._requires == other._requires
            and self._provides == other._provides
        )

    def __hash__(self):
        """Hash of the command.

        :rtype: integer
        """
        dependencies_hash = self._hash_base()
        return hash((self.cmd, dependencies_hash))

    def __eq__(self, other):
        """Compare commands."""
        return self._eq_base(other) and self.cmd == other.cmd

    def __repr__(self):
        """Show repr of Command."""
        return "Command<%s requires %s, provides %s>\n" % (
            self.repr_cmd(),
            ", ".join([repr(x) for x in self._requires]),
            ", ".join([repr(x) for x in self._provides]),
        )

    @staticmethod
    def command_list_to_digraph(commands):  # pragma: no cover
        """Generate dot source for a digraph.

        Suitable for generating diagrams.

        The requires and provides from the commands build nodes, the commands
        themselves act as connectors.

        :param  commands: The commands to draw a diagram with
        :type   commands: list
        """
        nodes = set()
        edges = set()

        def result_node(type_, name):
            """Get the dot representation of a result node."""
            return (
                '"%s %s" [shape=ellipse]' % (type_, name),
                '"%s %s"' % (type_, name),
            )

        def cmd_node(command):
            """Get the dot representation of a command node."""
            return (
                '"%s" [shape=box]' % command.repr_cmd(),
                '"%s"' % command.repr_cmd(),
            )

        for cmd in commands:
            if cmd is None:
                continue

            cmd_spec, cmd_identifier = cmd_node(cmd)
            nodes.add(cmd_spec)

            for type_, name in cmd._requires:
                spec, identifier = result_node(type_, name)
                nodes.add(spec)
                edges.add((identifier, cmd_identifier))

            for type_, name in cmd._provides:
                spec, identifier = result_node(type_, name)
                nodes.add(spec)
                edges.add((cmd_identifier, identifier))

        template = """
            digraph {
                %s;
                %s;
            }
        """
        return template % (
            ";\n".join(nodes),
            ";\n".join(["%s -> %s" % edge for edge in edges]),
        )

    @staticmethod
    def order_commands(commands, has_dependency_cb=lambda x: False):
        """Order the commands.

        According to the dependencies they provide/require.

        :param          commands: The commands to order
        :type           commands: list
        :param has_dependency_cb: Optional callback the resolve external
                                  dependencies
        :type  has_dependency_cb: function
        """
        commands = set([c for c in commands if c is not None])

        lg.debug("Ordering commands: %s", [str(cmd) for cmd in commands])

        have_requirements: dict["Command", int] = collections.defaultdict(lambda: 0)
        required_number: dict["Command", int] = collections.defaultdict(lambda: 0)
        scheduled = []

        for cmd in commands:
            for provide in cmd._provides:
                required_number[provide] += 1

        something_changed = True
        while something_changed:
            something_changed = False

            for cmd in commands:
                if cmd in scheduled:
                    continue

                can_schedule = True
                for req in cmd._requires:
                    if have_requirements[req] < required_number[req]:
                        lg.debug(
                            "%s: dependency %s not fulfilled, "
                            "checking aptly state" % (cmd, req)
                        )
                        # No command providing our dependency.. Let's see if
                        # it's already otherwise fulfilled
                        if not has_dependency_cb(req):
                            lg.debug(
                                "%s: dependency %s not "
                                "in aptly state either" % (cmd, req)
                            )
                            can_schedule = False
                            # Break out of the requirements loop, as the
                            # command cannot be scheduled anyway.
                            break
                            # command cannot be scheduled anyway.
                            break

                if can_schedule:
                    lg.debug("%s: all dependencies fulfilled" % cmd)
                    scheduled.append(cmd)
                    for provide in cmd._provides:
                        have_requirements[provide] += 1

                    something_changed = True

        unresolved = [cmd for cmd in commands if cmd not in scheduled]

        if len(unresolved) > 0:  # pragma: no cover
            raise ValueError(
                "Commands with unresolved deps: %s" % [str(cmd) for cmd in unresolved]
            )

        # Just one last verification before we commence
        scheduled_set = set([cmd for cmd in scheduled])
        incoming_set = set([cmd for cmd in commands])
        assert incoming_set == scheduled_set

        lg.info("Reordered commands: %s", [str(cmd) for cmd in scheduled])

        return scheduled


class FunctionCommand(Command):
    """Repesents a function command.

    Is used to resolve dependencies between such commands. This command executes
    the given function. *args and **kwargs are passed through.

    :param func: The function to execute
    :type  func: callable
    """

    def __init__(self, func, *args, **kwargs):
        super().__init__([])

        assert callable(func)
        self.cmd = [str(id(func))]
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def freeze(self):
        """Freeze the class to make it hashable."""
        self._freeze_common()
        # manually checking using self.frozen
        self.kwargs = frozendict(self.kwargs)  # type: ignore

    def __hash__(self):
        """Hash the class."""
        dependencies_hash = self._hash_base()
        return hash((id(self.func), self.args, self.kwargs, dependencies_hash))

    def __eq__(self, other):
        """Compare the class."""
        return (
            self._eq_base(other)
            and id(self.func) == id(other.func)
            and self.args == other.args
            and self.kwargs == other.kwargs
        )

    def execute(self):
        """Execute the command.

        Call the function.
        """
        if self._finished:  # pragma: no cover
            return self._finished
        if not Command.pretend_mode:
            lg.debug(
                "Running code: %s(args=%s, kwargs=%s)",
                self.func.__name__,
                repr(self.args),
                repr(self.kwargs),
            )

            self.func(*self.args, **self.kwargs)

            self._finished = True
        else:  # pragma: no cover
            lg.info(
                "Pretending to run code: %s(args=%s, kwargs=%s)",
                self.repr_cmd(),
                repr(self.args),
                repr(self.kwargs),
            )

        return self._finished

    def repr_cmd(self):
        """Return repr of the command.

        :rtype: str
        """
        # We need to "id" ourselves here so that multiple commands that call a
        # function with the same name won't be shown as being equal.
        return "%s|%s" % (self.func.__name__, id(self))

    def __repr__(self):
        """Show repr for FunctionCommand."""
        return "FunctionCommand<%s requires %s, provides %s>\n" % (
            self.repr_cmd(),
            ", ".join([repr(x) for x in self._requires]),
            ", ".join([repr(x) for x in self._provides]),
        )
