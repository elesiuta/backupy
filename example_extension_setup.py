# install with `python example_extension_setup.py install --user`
# run with `backupy.rsync [options]`
import setuptools
setuptools.setup(
    name="backupy.rsync",
    version="1.0.0",
    description="Example backupy extension using rsync",
    long_description="Example backupy extension using rsync",
    long_description_content_type="text/markdown",
    py_modules=["example_extension"],
    entry_points={"console_scripts": ["backupy.rsync = example_extension:main"]},
    install_requires=["backupy"],
)
