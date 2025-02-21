from setuptools import setup, find_packages


setup(
    name='jms-pam',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'httpsig'
    ],
    description='JumpServer PAM Client',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/jumpserver',
    author='JumpServer Team',
    author_email='code@jumpserver.org',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.6',
)
