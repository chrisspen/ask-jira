from __future__ import print_function
import os

from setuptools import setup, find_packages

import ask_jira

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

def get_reqs(*fns):
    lst = []
    for fn in fns:
        for package in open(os.path.join(CURRENT_DIR, fn)).readlines():
            package = package.strip()
            if not package:
                continue
            lst.append(package.strip())
    return lst

setup(
    name="ask_jira",
    version=ask_jira.__version__,
    packages=find_packages(),
    scripts=['bin/ask-jira.py'],
    #package_data={
        #'': ['docs/*.txt', 'docs/*.py'],
    #},
    author="Chris Spencer",
    author_email="chrisspen@gmail.com",
    description="Common JIRA API queries.",
    license="MIT",
    url="https://github.com/chrisspen/ask-jira",
    #https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        #'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        #'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        #'Programming Language :: Python :: 3.4',
        #'Programming Language :: Python :: 3.5',
        #'Programming Language :: Python :: 3.6',
    ],
    zip_safe=False,
    install_requires=get_reqs('requirements.txt'),
)
