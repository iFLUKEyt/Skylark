from setuptools import setup, find_packages

setup(
    name='imghdr-fallback',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    description='Fallback imghdr module for environments missing stdlib imghdr',
)
