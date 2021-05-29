#!/usr/bin/env python3
#
#  __init__.py
"""
Sphinx extension that automatically documents click applications.
"""
#
#  Copyright © 2020-2021 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#  Based on https://github.com/click-contrib/sphinx-click
#  Copyright (c) 2017 Stephen Finucane http://that.guru/
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
#

# stdlib
import enum
import traceback
import warnings
from operator import attrgetter
from typing import Iterable, Optional, Tuple

# 3rd party
import click
from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from domdf_python_tools.stringlist import DelimitedList
from domdf_python_tools.words import Plural
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx_toolbox.utils import Purger

__author__: str = "Dominic Davis-Foster"
__copyright__: str = "2020-2021 Dominic Davis-Foster"
__license__: str = "MIT License"
__version__: str = "0.0.0"
__email__: str = "dominic@davis-foster.co.uk"

__all__ = ["ClickDirective", "nested_option", "setup"]


class NestedOption(str, enum.Enum):  # noqa: SLOT000
	NESTED_FULL = "full"
	NESTED_SHORT = "short"
	NESTED_NONE = "none"


NESTED_FULL = NestedOption.NESTED_FULL
NESTED_SHORT = NestedOption.NESTED_SHORT
NESTED_NONE = NestedOption.NESTED_NONE

click_purger = Purger("all_click")
_argument = Plural("argument", "argument(s)")


def _indent(text: str):
	return '\n'.join([f"    {line}" if not line.isspace() else line for line in text.split('\n')])


def _get_usage(ctx: click.Context):
	"""
	Alternative, non-prefixed version of 'get_usage'.
	"""

	formatter = ctx.make_formatter()
	pieces = ctx.command.collect_usage_pieces(ctx)
	formatter.write_usage(ctx.command_path, ' '.join(pieces), prefix='')
	return formatter.getvalue().rstrip('\n')


def _get_help_record(opt: click.Option) -> Tuple[str, str]:
	"""
	Re-implementation of :meth:`click.Option.get_help_record`.

	The variant of 'get_help_record' found in Click makes uses of slashes to
	separate multiple opts, and formats option arguments using upper case. This
	is not compatible with Sphinx's 'option' directive, which expects
	comma-separated opts and option arguments surrounded by angle brackets [1].

	[1] https://www.sphinx-doc.org/en/stable/domains.html#directive-option
	"""

	def _write_opts(opts):
		rv, _ = click.formatting.join_options(opts)

		if not opt.is_flag and not opt.count:
			name = opt.name
			if opt.metavar:
				name = opt.metavar.lstrip("<[{($").rstrip(">]})$")
			rv += f" <{name}>"

		return rv

	rv = [_write_opts(opt.opts)]
	out = []
	extras = []

	if opt.secondary_opts:
		rv.append(_write_opts(opt.secondary_opts))

	if opt.help:
		if opt.required:
			out.append("**Required** %s" % opt.help)
		else:
			out.append(opt.help)
	else:
		if opt.required:
			out.append("**Required**")

	if opt.default is not None and opt.show_default:
		if isinstance(opt.show_default, str):
			# Starting from Click 7.0 this can be a string as well.
			# This is mostly useful when the default is not a constant and
			# documentation thus needs a manually written string.
			extras.append(f":default: {opt.show_default}")
		elif isinstance(opt.default, Iterable) and not isinstance(opt.default, str):
			extras.append(f":default: {DelimitedList(opt.default):, }")
		else:
			extras.append(f":default: {opt.default}")

	if isinstance(opt.type, click.Choice):
		extras.append(f":options: {DelimitedList(opt.type.choices): | }")

	if extras:
		if out:
			out.append('')

		out.extend(extras)

	return ", ".join(rv), '\n'.join(out)


def _format_description(ctx: click.Context):
	"""
	Format the description for a given `click.Command`.

	We parse this as reStructuredText, allowing users to embed rich
	information in their help messages if they so choose.
	"""

	help_string = ctx.command.help or ctx.command.short_help

	if not help_string:
		return

	bar_enabled = False

	for line in statemachine.string2lines(help_string, tab_width=4, convert_whitespace=True):
		if line == '\x08':
			bar_enabled = True
			continue
		if line == '':
			bar_enabled = False

		if bar_enabled:
			yield f"| {line}"
		else:
			yield line

	yield ''


def _format_usage(ctx):
	"""
	Format the usage for a `click.Command`.
	"""

	yield ".. code-block:: shell"
	yield ''

	for line in _get_usage(ctx).splitlines():
		yield _indent(line)

	yield ''


def _format_option(opt: click.Option):
	"""
	Format the output for a `click.Option`.
	"""

	opt_help = _get_help_record(opt)

	yield f".. option:: {opt_help[0]}"

	if opt_help[1]:
		yield ''
		for line in statemachine.string2lines(opt_help[1], tab_width=4, convert_whitespace=True):
			yield _indent(line)


def _format_options(ctx):
	"""
	Format all :class:`click.Option` for a :class:`click.Command`.
	"""

	params = [param for param in ctx.command.params if isinstance(param, click.Option) and not param.hidden]

	for param in params:
		yield from _format_option(param)
		yield ''


def _format_argument(arg: click.Argument):
	"""
	Format the output of a :class:`click.Argument`.
	"""

	yield f".. option:: {arg.human_readable_name}"
	yield ''

	if getattr(arg, "description", None) is not None:
		yield _indent(arg.description)  # type: ignore
		yield ''

	if arg.required:
		yield f"    Required {_argument(arg.nargs)}."
	else:
		yield f"    Optional {_argument(arg.nargs)}."
		yield f"    Default ``{arg.default!r}``"


def _format_arguments(ctx: click.Context):
	"""
	Format all `click.Argument` for a `click.Command`.
	"""

	params = [x for x in ctx.command.params if isinstance(x, click.Argument)]

	for param in params:
		yield from _format_argument(param)
		yield ''


def _format_envvar(param):
	"""
	Format the envvars of a `click.Option` or `click.Argument`.
	"""

	yield f'.. envvar:: {param.envvar}'
	yield "    :noindex:"
	yield ''

	# TODO: Provide a role to link to the option that accepts slashes
	#  Or replace the option directive entirely?
	#  That would allow linking to the option of a specific command.

	if isinstance(param, click.Argument):
		yield f"    Provides a default for :option:`{param.human_readable_name}`"
	else:
		param_ref = DelimitedList(param.opts)
		yield f"    Provides a default for :option:`{param_ref: / } <{param_ref[0]}>`"


def _format_envvars(ctx: click.Context):
	"""
	Format all envvars for a :class:`click.Command`.
	"""

	params = [x for x in ctx.command.params if getattr(x, "envvar")]

	for param in params:
		yield f".. _{ctx.command_path.replace(' ', '-')}-{param.name}-{param.envvar}:"
		yield ''
		yield from _format_envvar(param)
		yield ''


def _format_subcommand(command):
	"""
	Format a sub-command of a :class:`click.Command` or :class:`click.Group`.
	"""

	yield f'.. object:: {command.name}'

	if not command.help:
		return

	yield ''

	for line in statemachine.string2lines(command.help, tab_width=4, convert_whitespace=True):
		yield _indent(line)


def _format_epilog(ctx: click.Context):
	"""
	Format the epilog for a given :class:`click.Command`.

	We parse this as reStructuredText, allowing users to embed rich
	information in their help messages if they so choose.
	"""

	epilog_string = ctx.command.epilog

	if not epilog_string:
		return

	yield from statemachine.string2lines(epilog_string, tab_width=4, convert_whitespace=True)
	yield ''


def _get_lazyload_commands(multicommand: click.MultiCommand):
	commands = {}

	for command in multicommand.list_commands(multicommand):  # type: ignore
		commands[command] = multicommand.get_command(multicommand, command)  # type: ignore

	return commands


def _filter_commands(ctx: click.Context, commands=None):
	"""
	Return list of used commands.
	"""

	lookup = getattr(ctx.command, "commands", {})

	if not lookup and isinstance(ctx.command, click.MultiCommand):
		lookup = _get_lazyload_commands(ctx.command)

	if commands is None:
		return sorted(lookup.values(), key=attrgetter("name"))

	names = [name.strip() for name in commands.split(',')]

	return [lookup[name] for name in names if name in lookup]


def _format_command(ctx: click.Context, nested: NestedOption, commands=None):
	"""
	Format the output of :class:`click.Command`.
	"""

	if ctx.command.hidden:
		return

	# description
	yield from _format_description(ctx)

	yield f".. program:: {ctx.command_path}"

	# usage
	yield from _format_usage(ctx)

	# options
	lines = list(_format_options(ctx))
	if lines:
		# we use rubric to provide some separation without exploding the table
		# of contents
		yield ".. rubric:: Options"
		yield ''

	yield from lines

	# arguments
	lines = list(_format_arguments(ctx))

	if lines:
		yield ".. rubric:: Arguments"
		yield ''
		yield from lines

	# environment variables
	lines = list(_format_envvars(ctx))

	if lines:
		yield ".. rubric:: Environment variables"
		yield ''
		yield from lines

	# description
	yield from _format_epilog(ctx)

	# if we're nesting commands, we need to do this slightly differently
	if nested in (NestedOption.NESTED_FULL, NestedOption.NESTED_NONE):
		return

	commands = _filter_commands(ctx, commands)

	if commands:
		yield ".. rubric:: Commands"
		yield ''

	for command in commands:
		# Don't show hidden subcommands
		if not command.hidden:
			yield from _format_subcommand(command)
			yield ''


def nested_option(argument: str) -> Optional[str]:  # noqa: D103
	if not argument:
		return None

	values = (NESTED_FULL, NESTED_SHORT, NESTED_NONE)

	if argument not in values:
		value = directives.format_values(values)
		raise ValueError(f"{value} is not a valid value for ':nested:'; allowed values: {value}")

	return argument


class ClickDirective(SphinxDirective):
	"""
	Sphinx directive for documenting Click commands.
	"""

	has_content = False
	required_arguments = 1
	option_spec = {
			"prog": directives.unchanged_required,
			"nested": nested_option,
			"commands": directives.unchanged,
			"show-nested": directives.flag,
			}

	def _generate_nodes(
			self,
			name: str,
			command: click.Command,
			parent: Optional[click.Context],
			nested: NestedOption,
			commands=None,
			):
		"""
		Generate the relevant Sphinx nodes.

		Format a :class:`click.Group` or :class:`click.Command`.

		:param name: Name of command, as used on the command line
		:param command: Instance of `click.Group` or `click.Command`
		:param parent: Instance of `click.Context`, or None
		:param nested: The granularity of subcommand details.
		:param commands: Display only listed commands or skip the section if empty

		:returns: A list of nested docutils nodes
		"""

		if command.hidden:
			return []

		targetid = f"click-{self.env.new_serialno('click'):d}"
		targetnode = nodes.target('', '', ids=[targetid])

		# Summary
		ctx = click.Context(command, info_name=name, parent=parent)
		content = list(_format_command(ctx, nested, commands))

		view = ViewList(content)
		click_node = nodes.paragraph(rawsource='\n'.join(content))
		self.state.nested_parse(view, self.content_offset, click_node)

		click_purger.add_node(self.env, click_node, targetnode, self.lineno)

		return [targetnode, click_node]

	def _load_module(self, module_path: str):
		"""
		Load the module.

		:param module_path:
		"""

		try:
			module_name, attr_name = module_path.split(':', 1)
		except ValueError:
			raise self.error(f'"{module_path}" is not of format "module:parser"')

		try:
			mod = __import__(module_name, globals(), locals(), [attr_name])
		except (Exception, SystemExit) as exc:  # noqa
			err_msg = f'Failed to import "{attr_name}" from "{module_name}". '

			if isinstance(exc, SystemExit):
				err_msg += "The module appeared to call sys.exit()"
			else:
				err_msg += f'The following exception was raised:\n{traceback.format_exc()}'

			raise self.error(err_msg)

		if not hasattr(mod, attr_name):
			raise self.error(f'Module "{module_name}" has no attribute "{attr_name}"')

		parser = getattr(mod, attr_name)

		if not isinstance(parser, click.BaseCommand):
			raise self.error(f'"{type(parser)}" of type "{module_path}" is not derived from "click.BaseCommand"')
		return parser

	def run(self):  # noqa: D102
		command = self._load_module(self.arguments[0])

		if "prog" not in self.options:
			raise self.error(":prog: must be specified")

		prog_name = self.options.get("prog")
		show_nested = "show-nested" in self.options
		nested = self.options.get("nested")

		if show_nested:
			if nested:
				raise self.error("':nested:' and ':show-nested:' are mutually exclusive")
			else:
				warnings.warn(
						"':show-nested:' is deprecated; use ':nested: full'",
						DeprecationWarning,
						)
				nested = NestedOption.NESTED_FULL if show_nested else NESTED_SHORT

		commands = self.options.get("commands")

		return self._generate_nodes(prog_name, command, None, nested, commands)


def env_get_outdated(app, env, added, changed, removed):
	return [node["docname"] for node in getattr(env, click_purger.attr_name, ())]


def setup(app: Sphinx) -> None:
	"""
	Setup Sphinx extension.
	"""

	app.add_directive("click", ClickDirective)
	app.connect("env-purge-doc", click_purger.purge_nodes)
	app.connect("env-get-outdated", env_get_outdated)
