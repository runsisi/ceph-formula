{% from "ceph/lookup.jinja" import ceph with context %}

{% if ceph.cluster != '' %}
{% set cluster_option = '--cluster ' ~ ceph.cluster %}
{% else %}
{% set cluster_option = '' %}
{% endif %}

{% if ceph.authentication_type == 'cephx' %}
{% if ceph.mon_key != '' %}
{% set keyring_path = '/tmp/' ~ ceph.cluster ~ '-mon-keyring' %}
mon.keyring:
  file.managed:
    - name: {{ keyring_path }}
    - mode: 444
    - contents: "[mon.]\n\tkey = {{ ceph.mon_key }}\n\tcaps mon = \"allow *\"\n"
{% elif ceph.mon_keyring != '' %}
{% set keyring_path = ceph.mon_keyring %}
{% endif %}
{% else %}
{% set keyring_path = '/dev/null' %}
{% endif %}

{% if ceph.public_network != '' %}
{% set public_addr_option = '--public_addr ' ~ ceph.public_network %}
{% else %}
{% set public_addr_option = '' %}
{% endif %}

{% if grains['os'] == 'Ubuntu' or grains['os'] == 'Deepin' %}
{% set init = 'upstart' %}
{% elif grains['os'] == 'Debian' or grains['os_family'] == 'RedHat' %}
{% set init = 'sysvinit' %}
{% endif %}

{% for mon_id in ceph.mon_ids %}
mon.mkfs.{{ mon_id }}:
  cmd.run:
    - name: |
        mon_data=$(ceph-mon {{ cluster_option }} --id {{ mon_id }} --show-config-value mon_data)
        if [ ! -d $mon_data ]; then
          mkdir -p $mon_data
          if ceph-mon {{ cluster_option }} \
            {{ public_addr_option }} \
            --mkfs \
            --id {{ mon_id }} \
            --keyring {{ keyring_path }}; then
            touch $mon_data/done $mon_data/{{ init }} $mon_data/keyring
          else
            rm -rf $mon_data
          fi
        fi

mon.start.{{ mon_id }}:
  cmd.run:
{% if grains['os'] == 'Ubuntu' or grains['os'] == 'Deepin' %}
    - name: start ceph-mon id={{ mon_id }}
{% elif grains['os'] == 'Debian' or grains['os_family'] == 'RedHat' %}
    - name: service ceph start mon.{{ mon_id }}
{% endif %}
    - require:
      - cmd: mon.mkfs.{{ mon_id }}
{% endfor %}