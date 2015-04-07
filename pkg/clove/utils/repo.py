# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn


def yum_repo(**kwargs):
    # taken from ceph-deploy, https://github.com/ceph/ceph-deploy.git

    lines = []

    # by using tuples (vs a dict) we preserve the order of what we want to
    # return, like starting with a [repo name]
    tmpl = (
        ('reponame', '[%s]'),
        ('name', 'name=%s'),
        ('baseurl', 'baseurl=%s'),
        ('enabled', 'enabled=%s'),
        ('gpgcheck', 'gpgcheck=%s'),
        ('_type', 'type=%s'),
        ('gpgkey', 'gpgkey=%s'),
        ('proxy', 'proxy=%s'),
        ('priority', 'priority=%s'),
    )

    for line in tmpl:
        tmpl_key, tmpl_value = line  # key values from tmpl

        # ensure that there is an actual value (not None nor empty string)
        if tmpl_key in kwargs and kwargs.get(tmpl_key) not in (None, ''):
            lines.append(tmpl_value % kwargs.get(tmpl_key))

    return '\n'.join(lines)
