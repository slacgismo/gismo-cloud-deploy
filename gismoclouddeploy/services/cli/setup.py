from setuptools import setup

setup(
    name="gcd",
    version='0.1',
    py_modules=['main'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        gcd=main:main
    ''',
)