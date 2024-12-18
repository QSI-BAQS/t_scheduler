import distutils.command.build
from setuptools import find_packages, setup


setup(
    name='t_scheduler',
    packages=find_packages(where='src'),
    package_dir={
        '':'src'},
    include_package_data=True,
)
