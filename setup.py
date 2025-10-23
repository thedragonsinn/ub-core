import glob
import os

from setuptools import find_packages, setup

__version__: str | None = None


with open("ub_core/version.py", encoding="utf-8") as version_file:
    exec(version_file.read())


def get_platform_requirements() -> list[str]:
    with open("requirements.txt", encoding="utf-8") as req_file:
        packages: list[str] = list(
            filter(lambda l: not l.startswith("#") and l != "\n", req_file.readlines())
        )

    if "termux" not in os.environ.get("HOME", ""):
        return packages

    return list(filter(lambda p: not p.startswith(("uvloop", "psutil", "pillow")), packages))


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
