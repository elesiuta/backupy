import setuptools
import backupy

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="BackuPy",
    version=backupy.getVersion(),
    description="A simple backup program in python with an emphasis on data integrity and transparent behaviour",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elesiuta/backupy",
    packages=['backupy'],
    entry_points={
        'console_scripts': [
            'backupy = backupy:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Archiving :: Mirroring",
        "Topic :: Utilities",
        "Intended Audience :: End Users/Desktop",
        "Environment :: Console",
        "Development Status :: 5 - Production/Stable",
    ],
    test_suite = 'tests.tests',
)
