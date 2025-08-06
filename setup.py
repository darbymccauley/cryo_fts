from setuptools import setup

setup(
    name='cryo_fts',
    version='0.0.1',
    description='Cryogenic Fourier Transform Spectrometer utilities',
    author='Darby McCauley',
    author_email='darbynm2@illinois.edu',
    packages = ['cryo_fts'],
    package_dir = {'cryo_fts': 'src'},
    install_requires=[
        'numpy',
        'astropy',
        'pyserial',
        'zaber-motion'
    ],
    python_requires='>=3.7',
)
