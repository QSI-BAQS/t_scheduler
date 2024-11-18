import distutils.command.build
from setuptools import setup


setup(
    name='t_scheduler',
    packages=['t_scheduler'],
    package_dir={
        '':'src'},
    include_package_data=True,
)
