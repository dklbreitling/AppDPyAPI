from setuptools import setup

import src.AppDPyAPI as api

setup(name="AppDPyAPI",
      version=api.__version__,
      url=api.__url__,
      author=api.__author__,
      package_dir={"": "src"},
      python_requires=">=3.10, <4",
      install_requires=["requests", "sphinx", "sphinxcontrib-napoleon", "sphinx-rtd-theme", "uritemplate"],
      license='Apache')
