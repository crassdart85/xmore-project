"""
Setup configuration for xmore_data package.

Install in development mode: pip install -e .
Install normally: pip install .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements = [
    "pandas>=1.5.0",
    "numpy>=1.23.0",
    "python-dotenv>=0.20.0",
    "yfinance>=0.2.0",
    "joblib>=1.2.0",
    "openpyxl>=3.9.0",
]

optional_requirements = {
    "egxpy": ["egxpy>=0.1.0"],
    "alpha-vantage": ["alpha-vantage>=2.3.0"],
    "dev": [
        "pytest>=7.0.0",
        "pytest-cov>=3.0.0",
        "mypy>=0.990",
        "black>=22.0.0",
        "isort>=5.10.0",
        "flake8>=4.0.0",
    ]
}

setup(
    name="xmore-data",
    version="1.0.0",
    author="Xmore AI Team",
    author_email="dev@xmore.ai",
    description="Production-ready data ingestion layer for Egyptian Exchange (EGX) market data",
    long_description=Path("XMORE_DATA_GUIDE.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/xmore-ai/xmore-data",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require=optional_requirements,
    entry_points={
        "console_scripts": [
            "xmore-data=xmore_data.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
