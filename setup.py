import glob
import os

from setuptools import setup

__version__: str | None = None
vlocals = {}

with open("ub_core/version.py", encoding="utf-8") as version_file:
    exec(version_file.read(), vlocals)


setup(version=vlocals["__version__"])


def clean_up():
    cache = [item for item in ("./build", "./*egg-info", "./dist") if glob.glob(item)]
    os.system(" ".join(["rm -r", *cache]))


clean_up()
