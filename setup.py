"""
Setup configuration for Master Data Scraper
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='master-data-scraper',
    version='1.0.0',
    author='Luke Fournier',
    author_email='luke@example.com',
    description='A powerful command-line application for web scraping with an intuitive interface',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/lukefournier/master-data-scraper',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'dev': [
            'black>=24.1.0',
            'pylint>=3.0.0',
            'mypy>=1.8.0',
        ]
    },
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'scraper=main:main',
            'master-scraper=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML',
    ],
    keywords='web scraping, data extraction, cli, terminal, html parser',
)