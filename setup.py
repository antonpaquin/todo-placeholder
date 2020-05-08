from setuptools import setup, find_packages
from os import path

root_dir = path.abspath(path.dirname(__file__))

with open(path.join(root_dir, 'README.md'), 'r') as in_f:
    long_description = in_f.read()

setup(
    name='todo-placeholder',
    version='1.0.1',
    description='Use a terminal session to lazily write python source code',
    packages=find_packages(),

    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Anton Paquin',
    author_email='python@antonpaqu.in',
)


    
