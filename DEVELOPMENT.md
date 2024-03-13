# Logging and output

We use the logging facility for both debugging and output to the user. If you
want to output a normal message (replacement of `print()`) use `lg.warn()`. The
name might feel counter-intuitive, but I don't want to hack the logging-system
and add new levels. `INFO` is basically reseved for successful commands.
Unsuccessful commands are logged on `ERROR`. You can also hide unsuccessful command
using `hide_error=True` in `run_command`.
