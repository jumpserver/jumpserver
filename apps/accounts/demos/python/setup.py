from pathlib import Path

from setuptools import find_packages, setup


setup(
    name='jms-pam',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['requests>=2.31.0'],
    description='JumpServer PAM SDK and Agent',
    long_description=Path('README.en.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://github.com/jumpserver/jumpserver',
    author='JumpServer Team',
    author_email='code@jumpserver.org',
    entry_points={'console_scripts': ['jms-pam-agent=jms_pam.agent:main']},
    classifiers=['Programming Language :: Python :: 3'],
    python_requires='>=3.9',
)
