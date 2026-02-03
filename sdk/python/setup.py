"""
Setup script for BAEL Python SDK.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="bael-sdk",
    version="1.0.0",
    description="Official Python SDK for BAEL - The Lord of All AI Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BAEL Team",
    author_email="team@bael.ai",
    url="https://github.com/yourusername/bael",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "mypy>=0.990",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai agents orchestration bael llm",
    project_urls={
        "Documentation": "https://docs.bael.ai",
        "Source": "https://github.com/yourusername/bael",
        "Tracker": "https://github.com/yourusername/bael/issues",
    },
)
