*****
qTOML
*****

qtoml is another Python TOML encoder/decoder. I wrote it because I found
uiri/toml too unstable, and PyTOML too slow.

For information concerning the TOML language, see `toml-lang/toml <https://github.com/toml-lang/toml>`_.

qtoml currently supports TOML v0.5.0.

Usage
=====

qtoml is available on `PyPI <https://pypi.org/project/qtoml/>`_. You can install
it using pip:

.. code:: bash

  $ pip install qtoml

qtoml supports the standard ``load``/``loads``/``dump``/``dumps`` API common to
most similar modules. Usage:

.. code:: pycon

  >>> import qtoml
  >>> toml_string = """
  ... test_value = 7
  ... """
  >>> qtoml.loads(toml_string)
  {'test_value': 7}
  >>> print(qtoml.dumps({'a': 4, 'b': 5.0}))
  a = 4
  b = 5.0
  
  >>> infile = open('filename.toml', 'r')
  >>> parsed_structure = qtoml.load(infile)
  >>> outfile = open('new_filename.toml', 'w')
  >>> qtoml.dump(parsed_structure, outfile)

TOML supports a fairly complete subset of the Python data model, but notably
does not include a null or ``None`` value. If you have a large dictionary from
somewhere else including ``None`` values, it can occasionally be useful to
substitute them on encode:

.. code:: pycon

  >>> print(qtoml.dumps({ 'none': None }))
  qtoml.encoder.TOMLEncodeError: TOML cannot encode None
  >>> print(qtoml.dumps({ 'none': None }, encode_none='None'))
  none = 'None'

The ``encode_none`` value must be a replacement encodable by TOML, such as zero
or a string.

This breaks reversibility of the encoding, by rendering ``None`` values
indistinguishable from literal occurrences of whatever sentinel you chose. Thus,
it should not be used when exact representations are critical.

Development/testing
===================

qtoml uses the `poetry <https://github.com/sdispater/poetry>`_ tool for project
management. To check out the project for development, run:

.. code:: bash

  $ git clone --recursive-submodules https://github.com/alethiophile/qtoml
  $ cd qtoml
  $ poetry install

This assumes poetry is already installed. The package and dependencies will be
installed in the currently active virtualenv if there is one, or a
project-specific new one created if not.

qtoml is tested against the `alethiophile/toml-test
<https://github.com/alethiophile/toml-test>`_ test suite, forked from uiri's
fork of the original by BurntSushi. To run the tests, after checking out the
project as shown above, enter the ``tests`` directory and run:

.. code:: bash

  $ pytest              # if you already had a virtualenv active
  $ poetry run pytest   # if you didn't

License
=======

This project is available under the terms of the MIT license.
