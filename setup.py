import glob
import os

from setuptools import find_packages, setup

__version__: str | None = None


with open("ub_core/version.py", mode="r", encoding="utf-8") as version_file:
    exec(version_file.read())


def get_platform_requirements() -> list[str]:
    with open("requirements.txt", mode="r", encoding="utf-8") as req_file:
        packages: list[str] = filter(
            lambda l: not l.startswith("#"), req_file.readlines()
        )

    if "termux" not in os.environ.get("HOME", ""):
        return packages

    return [
        package
        for package in packages
        if package.split(">")[0] not in ("uvloop", "psutil", "pillow")
    ]


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
    install_requires=get_platform_requirements(),
    scripts=["bin/run-ub-core"],
)

clean_up()
