from setuptools import setup, find_packages

setup(
    name="wikibrain",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1",
        "pyyaml>=6.0",
        "tqdm>=4.66",
        "python-dotenv>=1.0",
    ],
    entry_points={
        "console_scripts": [
            "wikibrain=wikibrain.cli:main",
        ],
    },
    python_requires=">=3.10",
)
