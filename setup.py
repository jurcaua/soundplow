import os
import pathlib
from distutils.core import setup


def get_scripts(parent_folders, file_types):
    scripts = []

    for folder in parent_folders:
        for root, dirs, files in os.walk(folder):
            for file in files:
                print(file)
                if pathlib.Path(file).suffix in file_types:
                    scripts.append(os.path.join(root, file))


    print(scripts)
    return scripts


REQUIRED_PACKAGES = [
    'requests',
    'soundcloud',
    'PySide2',
    "six",
    "mutagen"
]


setup(
    name='soundplow',
    version='0.0.1dev',
    author='Alexander Jurcau',
    author_email='jurcaua@gmail.com',
    packages=REQUIRED_PACKAGES,
    scripts=get_scripts([r'..\soundplow'], ['py']),
    url='http://pypi.python.org/pypi/soundplow/',
    license='LICENSE.txt',
    description='Downloads songs from Soundcloud locally - in a flash.',
    long_description=open('README.txt').read(),
    install_requires=[],
)