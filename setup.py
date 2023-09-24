from setuptools import setup, find_packages

setup(
    name='arbok_driver',
    version='0.1',
    author='Andreas Nickl',
    packages=find_packages(),
    install_requires=[
        'qcodes',
        'qcodes-contrib-drivers',
        'qm-qua',
        'pyvisa',
        'qualang-tools',
        'quantify-core',
        'jupyterlab',
    ],
)
