#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

def readme():
    with open('README.rst', 'r') as f:
        return f.read()

setup(
    name='archiveify',
    version='0.0.1',
    description='The funniest joke in the world',
    long_description=readme(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Topic :: Text Processing :: Linguistic',
    ],
    keywords='funniest joke comedy flying circus',
    url='http://github.com/storborg/funniest',
    author='Jay Taylor',
    author_email='outtatime@gmail.com',
    license='MIT',
    packages=['archiveify'],
    install_requires=[
#        'markdown',
    ],
    include_package_data=True,
    zip_safe=False,
    test_suite='nose.collector',
    tests_require=['nose'],
)

