from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in nanak_customization/__init__.py
from nanak_customization import __version__ as version

setup(
	name='nanak_customization',
	version=version,
	description='Nanak Customization',
	author='Raaj Tailor',
	author_email='tailorraj111@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
