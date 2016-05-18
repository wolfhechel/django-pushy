from setuptools import setup, find_packages

import os

requirements_txt = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'requirements.txt'
)

with open(requirements_txt) as requirements:
    install_requires = [r.strip() for r in requirements.readlines()]

setup(
    name='Django-Pushy',
    version='0.1.11',
    author='Rakan Alhneiti',
    author_email='rakan.alhneiti@gmail.com',

    # Packages
    packages=[
        'pushy',
        'pushy/contrib',
        'pushy/contrib/rest_api',
        'pushy/tasks',
        'pushy/migrations',
        'pushy/south_migrations'
    ],
    include_package_data=True,

    # Details
    url='https://github.com/rakanalh/django-pushy',

    license='LICENSE.txt',
    description='Handle push notifications at scale.',
    long_description=open('README.rst').read(),

    # Dependent packages (distributions)
    install_requires = install_requires,
    extras_require={
        'rest_api': ['djangorestframework>=3.0,<3.3']
    }
)