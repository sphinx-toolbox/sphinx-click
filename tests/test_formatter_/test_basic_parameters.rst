A sample command.

.. program:: foobar
.. code-block:: shell

    foobar [OPTIONS] ARG

.. rubric:: Options

.. cli-option:: --param <param>

    A sample option

.. cli-option:: --another <FOO>

    Another option

.. cli-option:: --choice <choice>

    A sample option with choices

    :options: Option1 | Option2

.. rubric:: Arguments

.. cli-option:: ARG

    Required argument.

.. rubric:: Environment variables

.. _foobar-param-PARAM:

.. envvar:: PARAM
    :noindex:

    Provides a default for :option:`--param <--param>`

.. _foobar-arg-ARG:

.. envvar:: ARG
    :noindex:

    Provides a default for :option:`ARG`
