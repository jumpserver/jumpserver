from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent


setup(
    name="jms-pam",
    version="1.0.0",
    packages=find_packages(),
    package_data={"jms_pam": ["py.typed"]},
    install_requires=["requests>=2.31.0", "websocket-client>=1.6.1"],
    description="JumpServer PAM Python SDK",
    long_description=(BASE_DIR / "README.en.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/jumpserver/jumpserver",
    author="JumpServer Team",
    author_email="code@jumpserver.org",
    classifiers=["Programming Language :: Python :: 3"],
    python_requires=">=3.9",
)
