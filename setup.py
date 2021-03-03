# encoding=utf-8
from setuptools import setup


package_name = "audiosegmentation"
version_string = "2021.3.3"

dependencies = [
    "extraction-plugin",  # the plugin SDK
    "pydub",
    "logbook",
    "tensorflow",
    "inaSpeechSegmenter",
    "sndfile",
]

setup(
    name=package_name,
    version=version_string,
    author='Netherlands Forensic Institute',
    author_email='fbda@nfi.nl',
    description='Audio Segmentation for Hansken',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    packages=['.'],
    include_package_data=True,
    install_requires=dependencies,
)
