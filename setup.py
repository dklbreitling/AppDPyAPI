from setuptools import setup
import os


about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "src", "requests", "__version__.py")) as f:
    exec(f.read(), about)

setup(
    name="AppDPyAPI",
    version=about["__version__"],
    url=about["__url__"],
    author=about["__author__"],
    package_dir={"": "src"},
    python_requires=">=3.10, <4",
    install_requires=["requests"],
    license='Apache'
)
