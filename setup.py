from distutils.core import setup
from setuptools import find_packages

dependencies = [
    'flake8==2.4.1',
    'Jinja2>=3.1.6',
    'MarkupSafe==0.23',
    'mock==1.0.1',
    'pydns==2.3.6',
    'redis==2.10.3',
    'validate-email==1.3',
    'werkzeug>=3.0.6',
    'wheel>=0.38.1'
]

setup(
    name='formsender',
    version='0.1.2',
    install_requires=dependencies,
    author=u'OSU Open Source Lab',
    author_email='support@osuosl.org',
    packages=find_packages(),
    url='https://github.com/osuosl/formsender',
    license='Apache Version 2.0',
    zip_safe=False,
    description="Formsender application",
    long_description=open('README.md').read()
)
