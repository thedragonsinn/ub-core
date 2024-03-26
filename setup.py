from setuptools import find_packages, setup

with open("requirements.txt", mode="r", encoding="utf-8") as req_file:
    requires: list[str] = req_file.readlines()

with open("ub_core/version.py", mode="r", encoding="utf-8") as version_file:
    exec(version_file.read())

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
