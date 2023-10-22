import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eurotronic-cometblue",
    version="1.1.2dev1",
    author="Johannes Rottler",
    author_email="johannes@rottler.me",
    description="Allows you to access Eurotronic GmbH BLE Comet Blue Radiator Controller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zero-udo/eurotronic-cometblue",
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Development Status :: 5 - Production/Stable",
    ],
    install_requires="bleak",
    python_requires='>=3.7, <4.0',
)
