# 3rd party
import click
from coincidence.regressions import AdvancedFileRegressionFixture

# this package
import sphinx_click


class TestCommand:
	"""
	Validate basic ``click.Command`` instances.
	"""

	def test_no_parameters(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a `click.Command` with no parameters.

		This exercises the code paths for a command with *no* arguments, *no*
		options and *no* environment variables.
		"""

		@click.command()
		def foobar():
			"""
			A sample command.
			"""

		ctx = click.Context(foobar, info_name="foobar")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_basic_parameters(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a combination of parameters.

		This exercises the code paths for a command with arguments, options and
		environment variables.
		"""

		@click.command()
		@click.option("--param", envvar="PARAM", help="A sample option")
		@click.option("--another", metavar="[FOO]", help="Another option")
		@click.option(
				"--choice",
				help="A sample option with choices",
				type=click.Choice(["Option1", "Option2"]),
				)
		@click.argument("ARG", envvar="ARG")
		def foobar(bar):
			"""
			A sample command.
			"""

		ctx = click.Context(foobar, info_name="foobar")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_help_epilog(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate formatting of explicit help and epilog strings.
		"""

		@click.command(help="A sample command.", epilog="A sample epilog.")
		@click.option("--param", help="A sample option")
		def foobar(bar):
			pass

		ctx = click.Context(foobar, info_name="foobar")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_defaults(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate formatting of user documented defaults.
		"""

		@click.command()
		@click.option("--num-param", type=int, default=42, show_default=True)
		@click.option(
				"--param",
				default=lambda: None,
				show_default="Something computed at runtime",
				)
		def foobar(bar):
			"""
			A sample command.
			"""

		ctx = click.Context(foobar, info_name="foobar")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_hidden(self):
		"""
		Validate a `click.Command` with the `hidden` flag.
		"""

		@click.command(hidden=True)
		def foobar():
			"""
			A sample command.
			"""

		ctx = click.Context(foobar, info_name="foobar")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		assert '' == '\n'.join(output)

	def test_titles(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a `click.Command` with nested titles.
		"""

		@click.command()
		@click.option("--name", help="Name to say hello to.", required=True, type=str)
		def hello(name):
			"""
			Prints hello to name given.

			Examples
			--------

			.. code:: bash

				my_cli hello --name "Jack"
			"""

		ctx = click.Context(hello, info_name="hello")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")


class TestGroup:
	"""
	Validate basic ``click.Group`` instances.
	"""

	def test_no_parameters_group(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a `click.Group` with no parameters.

		This exercises the code paths for a group with *no* arguments, *no*
		options and *no* environment variables.
		"""

		@click.group()
		def cli():
			"""
			A sample command group.
			"""

		ctx = click.Context(cli, info_name="cli")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_basic_parameters_group(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a combination of parameters.

		This exercises the code paths for a group with arguments, options and
		environment variables.
		"""

		@click.group()
		@click.option("--param", envvar="PARAM", help="A sample option")
		@click.argument("ARG", envvar="ARG")
		def cli():
			"""
			A sample command group.
			"""

		ctx = click.Context(cli, info_name="cli")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_no_line_wrapping(self, advanced_file_regression: AdvancedFileRegressionFixture):
		r"""
		Validate behavior when a \b character is present.

		https://click.palletsprojects.com/en/7.x/documentation/#preventing-rewrapping
		"""

		@click.group()
		def cli():
			"""
			A sample command group.

			\b
			This is
			a paragraph
			without rewrapping.

			And this is a paragraph
			that will be rewrapped again.
			"""

		ctx = click.Context(cli, info_name="cli")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")


class TestNestedCommands:
	"""
	Validate ``click.Command`` instances inside ``click.Group`` instances.
	"""

	@staticmethod
	def _get_ctx():

		@click.group()
		def cli():
			"""
			A sample command group.
			"""

		@cli.command()
		def hello():
			"""
			A sample command.
			"""

		return click.Context(cli, info_name="cli")

	def test_nested_short(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a nested command with 'nested' of 'short' (default).

		We should list minimal help texts for sub-commands since they're not
		being handled separately.
		"""

		ctx = self._get_ctx()
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_nested_full(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a nested command with 'nested' of 'full'.

		We should not list sub-commands since they're being handled separately.
		"""

		ctx = self._get_ctx()
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_FULL))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_nested_none(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a nested command with 'nested' of 'none'.

		We should not list sub-commands.
		"""

		ctx = self._get_ctx()
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_NONE))
		advanced_file_regression.check('\n'.join(output), extension=".rst")


class TestCommandFilter:
	"""
	Validate filtering of commands.
	"""

	@staticmethod
	def _get_ctx():

		@click.group()
		def cli():
			"""
			A sample command group.
			"""

		@cli.command()
		def hello():
			"""
			A sample command.
			"""

		@cli.command()
		def world():
			"""
			A world command.
			"""

		return click.Context(cli, info_name="cli")

	def test_no_commands(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate an empty command group.
		"""

		ctx = self._get_ctx()
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT, commands=''))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_order_of_commands(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate the order of commands.
		"""

		ctx = self._get_ctx()
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT, commands="world, hello"))
		advanced_file_regression.check('\n'.join(output), extension=".rst")


class TestCustomMultiCommand:
	"""
	Validate ``click.MultiCommand`` instances.
	"""

	def test_basics(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Validate a custom ``click.MultiCommand`` with no parameters.

		This exercises the code paths to extract commands correctly from these commands.
		"""

		@click.command()
		def hello():
			"""
			A sample command.
			"""

		@click.command()
		def world():
			"""
			A world command.
			"""

		class MyCLI(click.MultiCommand):
			_command_mapping = {
					"hello": hello,
					"world": world,
					}

			def list_commands(self, ctx):
				return ["hello", "world"]

			def get_command(self, ctx, name):
				return self._command_mapping[name]

		cli = MyCLI(help="A sample custom multicommand.")
		ctx = click.Context(cli, info_name="cli")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))
		advanced_file_regression.check('\n'.join(output), extension=".rst")

	def test_hidden(self, advanced_file_regression: AdvancedFileRegressionFixture):
		"""
		Ensure 'hidden' subcommands are not shown.
		"""

		@click.command()
		def hello():
			"""
			A sample command.
			"""

		@click.command()
		def world():
			"""
			A world command.
			"""

		@click.command(hidden=True)
		def hidden():
			"""
			A hidden command.
			"""

		class MyCLI(click.MultiCommand):
			_command_mapping = {
					"hello": hello,
					"world": world,
					"hidden": hidden,
					}

			def list_commands(self, ctx):
				return ["hello", "world", "hidden"]

			def get_command(self, ctx, name):
				return self._command_mapping[name]

		cli = MyCLI(help="A sample custom multicommand.")
		ctx = click.Context(cli, info_name="cli")
		output = list(sphinx_click._format_command(ctx, nested=sphinx_click.NESTED_SHORT))

		# Note that we do NOT expect this to show the 'hidden' command
		advanced_file_regression.check('\n'.join(output), extension=".rst")
