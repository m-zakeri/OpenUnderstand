"""
OpenUnderstand setup script.

Commands:

`python setup.py install`
`python setup.py clean --all`


"""

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openunderstand",
    version="0.1.0",
    author="Morteza Zakeri, Amin HassanZarei, Ali Ayati",
    author_email="m-zakeri@live.com",
    license="MIT",
    description="A free implementation of Sci-tools Understand API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/m-zakeri/OpenUnderstand",
    project_urls={
        "Bug Tracker": "https://github.com/m-zakeri/OpenUnderstand/issues",
        "Source": "https://github.com/m-zakeri/OpenUnderstand",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "openunderstand = ounderstand.openunderstand:parse_arguments",
        ],
    },
    package_dir={"": "openunderstand"},
    packages=setuptools.find_packages(
        where="openunderstand",
    ),
    include_package_data=True,
    package_data={
        "": ["*.csv", "*.xlsx", "*.txt"],
    },
    exclude_package_data={"": ["README.md"]},
    python_requires=">=3.8",
    install_requires=[
        "antlr4-python3-runtime==4.9.1",
        "peewee>=3.14.4",
        "decorator>=4.4.2",
        "networkx>=2.5.1",
        "pandas>=1.1.5",
        "pyparsing>=2.4.7",
        "python-dateutil>=2.8.2",
        "regex>=2021.7.6",
        "GitPython>=3.1.32",
        "pybind11>=2.11.1",
        "speedy-antlr-tool>=1.1.0",
    ],
)
