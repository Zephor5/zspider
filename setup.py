# coding=utf-8
import os

from setuptools import find_packages
from setuptools import setup

VERSION = "0.1.0"

ROOT = os.path.dirname(os.path.abspath(__file__))


with open("requirements.txt") as fp:
    install_requires = [
        x.strip() for x in fp.read().split("\n") if not x.startswith("#")
    ]


def package_files(directories):
    paths = []
    for directory in directories:
        for path, _, filenames in os.walk(directory):
            for filename in filenames:
                paths.append(os.path.join("..", path, filename))
    return paths


extra_files = package_files(
    ["zspider/data", "zspider/www/static", "zspider/www/templates"]
)

setup(
    name="zspider",
    version=VERSION,
    author="zephorwu",
    author_email="zephor@qq.com",
    url="https://github.com/Zephor5/zspider",
    description="A crawler system.",
    long_description=open(os.path.join(ROOT, "README.md")).read(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("^utests/", "^data/")),
    zip_safe=False,
    install_requires=install_requires,
    license="MIT",
    package_data={"": extra_files},
    entry_points={
        "console_scripts": [
            "zspider-dispatcher = zspider.dispatcher:main",
            "zspider-web = zspider.web:main",
            "zspider-crawler = zspider.crawler:main",
        ]
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
    ],
)
