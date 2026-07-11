import os
import sys
import pybind11
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup, find_packages

# Get pybind11 include path
pybind11_include = pybind11.get_include()

ext_modules = [
    Pybind11Extension(
        "alakoro",
        sources=[
            "src/cpp/bindings/bindings.cpp",
            "src/cpp/bindings/signal_processor_binding.cpp",
            "src/cpp/bindings/das_decoder_binding.cpp",
            "src/cpp/bindings/event_detector_binding.cpp",
            "src/cpp/core/signal_processor.cpp",
            "src/cpp/core/das_decoder.cpp",
            "src/cpp/core/filter_bank.cpp",
            "src/cpp/core/event_detector.cpp",
        ],
        include_dirs=[
            "src/cpp/include",
            pybind11_include,
        ],
        cxx_std=17,
    ),
]

setup(
    name="Alakoro_FiberSense",
    version="1.0.0",
    author="Luiz Paulo Colombiano",
    author_email="",
    description="Sistema de Processamento de Dados de Fibra Optica (DAS) - Arquitetura Event-Driven + MVC",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Colombiano/Alakoro_FiberSense",
    packages=find_packages(where="src/python"),
    package_dir={"": "src/python"},
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "matplotlib>=3.4.0",
        "pybind11>=2.10.0",
        "h5py>=3.6.0",
        "pyyaml>=6.0",
        "pika>=1.3.0",
        "redis>=4.3.0",
        "pydantic>=1.10.0",
        "fastapi>=0.95.0",
        "uvicorn>=0.20.0",
        "websockets>=11.0",
        "asyncio-mqtt>=0.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: C++",
    ],
    python_requires=">=3.9",
    zip_safe=False,
)
