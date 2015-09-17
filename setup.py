from distutils.core import setup
from setuptools import find_packages

dependencies = [
    'flake8==2.4.1',
    'Jinja2==2.7.3',
    'MarkupSafe==0.23',
    'mock==1.0.1',
    'pydns==2.3.6',
    'redis==2.10.3',
    'validate-email==1.3',
    'Werkzeug==0.10.4',
    'wheel==0.24.0'
]

setup(
    name='formsender',
    version='0.1.1',
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
