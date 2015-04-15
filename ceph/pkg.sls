{% from 'ceph/lookup.jinja' import ceph with context %}

include:
  - ceph.repo

ceph.pkg:
  pkg.latest:
    - name: ceph
    - fromrepo: clove
    - refresh: True
    - require:
      - pkgrepo: ceph.repo
