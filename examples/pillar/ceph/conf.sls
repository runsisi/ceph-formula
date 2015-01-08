ceph:
  conf:
    cluster: ceph

    fsid: cbc99ef9-fbc3-41ad-a726-47359f8d84b3
    authentication_type: cephx
    mon_initial_members: hust,
    mon_host: 10.118.4.36:6789,
    public_network: 10.118.4.0/24
    cluster_network: 10.118.4.0/24

    osd_pool_default_pg_num: 200
    osd_pool_default_pgp_num: 200
    osd_pool_default_size: 2
    osd_pool_default_min_size: 1
    osd_crush_chooseleaf_type: 0

    mon_key: AQATGHJTUCBqIBAA7M2yafV1xctn1pgr3GcKPg==
    admin_key: AQBMGHJTkC8HKhAAJ7NH255wYypgm1oVuV41MA==
    bootstrap_osd_key: AQARG3JTsDDEHhAAVinHPiqvJkUi5Mww/URupw==
    bootstrap_mds_key: AQCztJdSyNb0NBAASA2yPZPuwXeIQnDJ9O8gVw==