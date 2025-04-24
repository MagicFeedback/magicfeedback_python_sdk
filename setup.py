from setuptools import find_packages, setup

setup(
    name="magicfeedback_sdk",
    version="1.0.3.2",
    description="A Python SDK for interacting with the MagicFeedback API",
    author="Francisc Arias",
    author_email="farias@magicfeedback.io.io",
    url="https://github.com/MagicFeedback/magicfeedback_python_sdk",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "requests>=2.0.0"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
