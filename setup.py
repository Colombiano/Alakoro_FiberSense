"""
Alakoro FiberSense — Setup
Compatibilidade legacy para ferramentas que ainda não suportam pyproject.toml
Legacy compatibility for tools that don't yet support pyproject.toml
"""

from setuptools import setup, find_packages

setup(
    name="alakoro-fibersense",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    packages=find_packages(include=["src", "src.*"]),
    package_data={
        "src.events": ["*.json"],
    },
    include_package_data=True,
)
