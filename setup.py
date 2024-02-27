from setuptools import setup, find_packages
from version import __version__

with open("requirements.txt", mode="r", encoding="utf-8") as req_file:
    requires: list[str] = req_file.readlines()

setup(
    name="ub_core",
    version=__version__,
    author="Meliodas",
    author_email="",
    description="BoilerPlate Code for Bot projects.",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires="~=3.11",
    install_requires=requires,
)
