import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eurotronic-cometblue",
    version="1.0.3",
    author="Johanens Rottler",
    author_email="johannes@rottler.me",
    description="Allows you to access Eurotronic GmbH BLE Comet Blue Radiator Controller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zero-udo/eurotronic-cometblue",
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 5 - Production/Stable",
    ],
    install_requires="pygatt[GATTTOOL]==4.0.5",
    python_requires='>=3.6',
)
