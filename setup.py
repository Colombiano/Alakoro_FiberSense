"""
Alakoro FiberSense — Setup
Compatibilidade legacy para ferramentas que ainda nao suportam pyproject.toml.
O build principal e feito via scikit-build-core definido em pyproject.toml.
"""

from setuptools import setup, find_packages

setup(
    name="alakoro-fibersense",
    packages=find_packages(include=["alakoro", "alakoro.*", "alakoro_core", "alakoro_core.*"]),
    package_data={
        "alakoro.events": ["*.json"],
        "alakoro.io.schemas": ["*.avsc"],
    },
    include_package_data=True,
    zip_safe=False,
)
