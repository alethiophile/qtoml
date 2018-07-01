*****
qTOML
*****

qtoml is another Python TOML encoder/decoder. I wrote it because I found
uiri/toml too unstable, and PyTOML too slow.

For information concerning the TOML language, see toml-lang/toml.

qtoml currently supports TOML v0.4.0. Features above that are not supported.

Usage
=====

qtoml supports the standard ``load``/``loads``/``dump``/``dumps`` API common to
most similar modules. Usage:

.. code: pycon

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

Testing
=======

qtoml is tested against the alethiophile/toml-test test suite, forked from
uiri's fork of the original by BurntSushi. To run the tests, check out the code
including submodules, install pytest, and run ``pytest`` under the ``tests``
subdirectory.

License
=======

This project is available under the terms of the MIT license.
