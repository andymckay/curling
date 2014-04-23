from setuptools import setup


setup(
    name='curling',
    version='0.3.9.3',
    description='Slumber wrapper for Django that works well with Tastypie',
    long_description=open('README.rst').read(),
    author='Andy McKay',
    author_email='andym@mozilla.com',
    license='BSD',
    install_requires=['argparse', 'requests>=2.0.0', 'PyJWT-mozilla',
                      'mock', 'slumber>=0.5.3', 'Django', 'pygments',
                      'oauth2>=1.5.211', 'httplib2',
                      'django-statsd-mozilla>=0.3.8.6', 'statsd>=1.0.0'],
    packages=['curling'],
    url='https://github.com/andymckay/curling',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Framework :: Django'
    ],
    entry_points={
        'console_scripts': [
            'curling = curling.command:main'
        ]
    }
)
