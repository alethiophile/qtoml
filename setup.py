#!python

from setuptools import setup

with open('README.rst') as rm:
    long_description = rm.read()

setup(
    name='qtoml',
    version='0.2.0',
    author="alethiophile",
    author_email="tomdicksonhunt@gmail.com",
    description="New TOML encoder/decoder",
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='MIT',
    packages=['qtoml'],
    url="https://github.com/alethiophile/qtoml",
    install_requires=['click'],
    python_requires='~=3.6',
    entry_points={
        'console_scripts': [
            'qtoml_testencode = qtoml.__main__:encode',
            'qtoml_testdecode = qtoml.__main__:decode',
        ],
    },
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules"
    )
)
