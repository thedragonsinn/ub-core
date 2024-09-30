import glob
import os

from setuptools import find_packages, setup

__version__: str | None = None

with open("requirements.txt", mode="r", encoding="utf-8") as req_file:
    requires: list[str] = req_file.readlines()

with open("ub_core/version.py", mode="r", encoding="utf-8") as version_file:
    exec(version_file.read())


def clean_up():
    cache = [item for item in ("./build", "./*egg-info", "./dist") if glob.glob(item)]
    os.system(" ".join(["rm -r", *cache]))


setup(
    name="ub_core",
    version=__version__,
    author="Meliodas",
    description="BoilerPlate Code for Bot projects.",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires="~=3.11",
    install_requires=requires,
    scripts=["bin/run-ub-core"],
)

clean_up()
