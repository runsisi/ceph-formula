ceph.crontab.logrotate:
  file.managed:
    - name: /var/spool/cron/root
    - makedirs: True
    - contents: '*/5 * * * * /usr/sbin/logrotate /etc/logrotate.d/ceph >/dev/null 2>&1'
