#!/usr/bin/env python
import setuptools
import sys
import os
# - For the example on which this was based, see
#   https://github.com/poikilos/linux-preinstall/blob/main/setup.py
#   which is based on
#   https://github.com/poikilos/world_clock/blob/main/setup.py
#   which is based on
#   https://github.com/poikilos/nopackage/blob/main/setup.py
#   which is based on
#   https://github.com/poikilos/pypicolcd/blob/master/setup.py
# - For nose, see https://github.com/poikilos/mgep/blob/master/setup.py

# versionedModule = {}
# versionedModule['urllib'] = 'urllib'
# if sys.version_info.major < 3:
#     versionedModule['urllib'] = 'urllib2'
install_requires = []

if os.path.isfile("requirements.txt"):
    with open("requirements.txt", "r") as ins:
        for rawL in ins:
            line = rawL.strip()
            if len(line) < 1:
                continue
            install_requires.append(line)

description = (
    "Compare, reorder, and commit a series of source"
    " snapshots (where each may also contain snapshots of subprojects)."
)
long_description = description
if os.path.isfile("readme.md"):
    long_description = ""
    with open("readme.md", "r") as fh:
        for rawL in fh:
            if rawL.startswith("## "):
                # Stop at the first subheading if using Markdown.
                long_description = long_description.rstrip()
                # ^ Remove the trailing newline.
                break
            long_description += rawL
            # Use rawL to keep the newline (read as \n in Python, so GUI-safe)


setuptools.setup(
    name='anewcommit',
    version='0.3.0',
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        ('License :: OSI Approved ::'
         ' MIT License'),
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Version Control',
    ],
    keywords=('python repo management commit data analyzer'
              ' meld merge compare files diff'),
    url="https://github.com/poikilos/anewcommit",
    author="Jake Gustafson",
    author_email='7557867+poikilos@users.noreply.github.com',
    license='MIT',
    # packages=setuptools.find_packages(),
    packages=['anewcommit'],
    # include_package_data=True,  # look for MANIFEST.in
    # scripts=['example'] ,
    # See <https://stackoverflow.com/questions/27784271/
    # how-can-i-use-setuptools-to-generate-a-console-scripts-entry-
    # point-which-calls>
    entry_points={
        'console_scripts': [
            'duminus=anewcommit.duminus:main',
            'anewcommit=anewcommit.gui_tkinter:main',
        ],
    },
    install_requires=install_requires,
    #     versionedModule['urllib'],
    # ^ "ERROR: Could not find a version that satisfies the requirement
    #   urllib (from nopackage) (from versions: none)
    #   ERROR: No matching distribution found for urllib"
    test_suite='nose.collector',
    tests_require=['nose', 'nose-cover3'],
    zip_safe=False,  # It can't run zipped due to needing data files.
 )
