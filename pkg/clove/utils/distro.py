# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import platform


def distribution_information():
    class Distro(object):
        pass
    v = Distro()

    (name, release, codename) = _distribution_information()
    name = _normalized_distro_name(name)
    release = _normalized_release(release)

    (v.name, v.major, v.codename) = name, release.major, codename

    return v


def _distribution_information():
    """ detect platform information """
    distro, release, codename = platform.linux_distribution()
    if not codename and 'debian' in distro.lower():  # this could be an empty string in Debian
        debian_codenames = {
            '8': 'jessie',
            '7': 'wheezy',
            '6': 'squeeze',
        }
        major_version = release.split('.')[0]
        codename = debian_codenames.get(major_version, '')

        # In order to support newer jessie/sid or wheezy/sid strings we test this
        # if sid is buried in the minor, we should use sid anyway.
        if not codename and '/' in release:
            major, minor = release.split('/')
            if minor == 'sid':
                codename = minor
            else:
                codename = major

    return (
        str(distro).strip(),
        str(release).strip(),
        str(codename).strip()
    )


def _normalized_distro_name(name):
    name = name.lower()
    if name.startswith(('redhat', 'red hat')):
        return 'redhat'
    elif name.startswith('scientific'):
        return 'scientific'
    elif name.startswith(('suse', 'opensuse')):
        return 'suse'
    elif name.startswith('centos'):
        return 'centos'
    return name


def _normalized_release(release):
    """
    A normalizer function to make sense of distro
    release versions.

    Returns an object with: major, minor, patch, and garbage

    These attributes can be accessed as ints with prefixed "int"
    attribute names, for example:

        normalized_version.int_major
    """
    release = release.strip()

    class NormalizedVersion(object):
        pass
    v = NormalizedVersion()  # fake object to get nice dotted access
    v.major, v.minor, v.patch, v.garbage = (release.split('.') + ["0"]*4)[:4]
    release_map = dict(major=v.major, minor=v.minor, patch=v.patch, garbage=v.garbage)

    # safe int versions that remove non-numerical chars
    # for example 'rc1' in a version like '1-rc1
    for name, value in release_map.items():
        if '-' in value:  # get rid of garbage like -dev1 or -rc1
            value = value.split('-')[0]
        value = float(''.join(c for c in value if c.isdigit()) or 0)
        int_name = "int_%s" % name
        setattr(v, int_name, value)

    return v
