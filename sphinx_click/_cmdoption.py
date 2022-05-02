#!/usr/bin/env python3
#
#  _cmdoption.py
"""
Sphinx extension that automatically documents click applications.
"""
#
#  Copyright © 2021 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#
#  Based on Sphinx
#  Copyright (c) 2007-2020 by the Sphinx team.
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

# stdlib
from typing import Any, List

# 3rd party
from docutils import nodes
from sphinx import addnodes
from sphinx.domains import std
from sphinx.util.docfields import DocFieldTransformer

__all__ = ["Cmdoption", "OptionDesc"]


class OptionDesc(addnodes.desc):  # noqa: D101
	pass


class Cmdoption(std.Cmdoption):
	"""
	Description of a command-line option (.. option).
	"""

	def run(self) -> List[nodes.Node]:  # noqa: D102
		if ':' in self.name:
			self.domain, self.objtype = self.name.split(':', 1)
		else:
			self.domain, self.objtype = '', self.name
		self.indexnode = addnodes.index(entries=[])

		node = OptionDesc()
		node.document = self.state.document
		node["domain"] = self.domain
		# 'desctype' is a backwards compatible attribute
		node["objtype"] = node["desctype"] = self.objtype
		node["noindex"] = noindex = ("noindex" in self.options)
		if self.domain:
			node["classes"].append(self.domain)

		self.names: List[Any] = []
		signatures = self.get_signatures()
		for i, sig in enumerate(signatures):
			# add a signature node for each signature in the current unit
			# and add a reference target for it
			signode = addnodes.desc_signature(sig, '')
			self.set_source_info(signode)
			node.append(signode)
			try:
				# name can also be a tuple, e.g. (classname, objname);
				# this is strictly domain-specific (i.e. no assumptions may
				# be made in this base class)
				name = self.handle_signature(sig, signode)
			except ValueError:
				# signature parsing failed
				signode.clear()
				signode += addnodes.desc_name(sig, sig)
				continue  # we don't want an index entry here
			if name not in self.names:
				self.names.append(name)
				if not noindex:
					# only add target and index entry if this is the first
					# description of the object with this name in this desc block
					self.add_target_and_index(name, sig, signode)

		contentnode = addnodes.desc_content()
		node.append(contentnode)
		if self.names:
			# needed for association of version{added,changed} directives
			self.env.temp_data["object"] = self.names[0]
		self.before_content()
		self.state.nested_parse(self.content, self.content_offset, contentnode)
		self.transform_content(contentnode)
		self.env.app.emit("object-description-transform", self.domain, self.objtype, contentnode)
		DocFieldTransformer(self).transform_all(contentnode)
		self.env.temp_data["object"] = None
		self.after_content()

		return [self.indexnode, node]
