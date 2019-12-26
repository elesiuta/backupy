import setuptools
import backupy

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="BackuPy",
    version=backupy.getVersion(),
    description="BackuPy: A succinct python program for backing up directories with an emphasis on simple usage and transparent behavior",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elesiuta/backupy",
    py_modules=['backupy'],
    entry_points={
        'console_scripts': [
            'backupy = backupy:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
