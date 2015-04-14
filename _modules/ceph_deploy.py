# -*- coding: utf-8 -*-
'''
Module for managing ceph (MON, OSD) deployment.

Note: Main ideas of the OSD code are borrowed from ceph-disk utility.

author: runsisi@hust.edu.cn
'''

from __future__ import absolute_import

# Import python libs
import os
import stat
import tempfile
import time
import errno
import re
import shutil
import ConfigParser
import struct
import base64
import uuid

# Import salt libs
from salt import utils

__virtualname__ = 'ceph_deploy'

COMMAND_TIMEOUT = 180                   # 180 seconds

CEPH_CLUSTER = 'ceph'                   # Default cluster name
CEPH_CONNECT_TIMEOUT = 30               # 60 seconds

JOURNAL_UUID = '45b0969e-9b03-4f30-b4c6-b4b80ceff106'
OSD_UUID = '4fbd7e29-9d25-41b8-afd0-062c0ceff05d'

DEFAULT_FS_TYPE = 'xfs'

MOUNT_OPTIONS = dict(
    btrfs='noatime,user_subvol_rm_allowed',
    # user_xattr is default ever since linux 2.6.39 / 3.0, but we'll
    # delay a moment before removing it fully because we did have some
    # issues with ext4 before the xatts-in-leveldb work, and it seemed
    # that user_xattr helped
    ext4='noatime,user_xattr',
    xfs='noatime,inode64',
    )

MKFS_OPTIONS = dict(
    btrfs='-m single -l 32768 -n 32768',
    # xfs insists on not overwriting previous fs; even if we wipe
    # partition table, we often recreate it exactly the same way,
    # so we'll see ghosts of filesystems past
    xfs='-f -i size=2048',
    )


class _CephDevType(object):
    DIR = 'directory'           # directory
    FILE = 'regular file'       # regular file
    DISK = 'disk'               # whole disk
    PART = 'partition'          # partition
    LV = 'LVM2 logical volume'  # LVM2 logical volume
    OTHER = '-OTHER-'           #


class _CephPartType(object):
    NONE = '-NONE-'         #
    GPT = 'gpt'             # gpt
    DOS = 'msdos'           # msdos
    OTHER = '-OTHER-'       #


# in strings, used by mount operation
class _CephFsType(object):
    NONE = '-NONE-'         #
    XFS = 'xfs'             # xfs
    EXT4 = 'ext4'           # ext4
    BTRFS = 'btrfs'         # btrfs
    OTHER = '-OTHER-'       #


def __virtual__():
    '''
    Only load if ceph package is installed.

    ceph and other utils are packed in ceph-common package
    ceph-mon, ceph-osd etc. are packed in ceph package

    :return: Module name if ceph package is installed else False.
    '''
    if utils.which('ceph') and utils.which('ceph-mon') and utils.which('ceph-osd'):
        return __virtualname__

    return False


def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret


def _run(cmd, **kwargs):
    '''
    Run cmd and return (code, stdout, stderr) 3-tuples.

    :param cmd: Command line to run.
    :param kwargs: Options etc.
    :return: (code, stdout, stderr) 3-tuples.
    '''
    if not isinstance(cmd, list):
        raise ValueError('cmd: {0} must be a list'.format(cmd))

    if 'timeout' not in kwargs:
        kwargs['timeout'] = COMMAND_TIMEOUT

    cmd = ' '.join(cmd)

    data = __salt__['cmd.run_all'](cmd, **kwargs)

    return data['retcode'], data['stdout'], data['stderr']


def _check_run(cmd, **kwargs):
    '''
    Run cmd and return (code, stdout, stderr) 3-tuples, throws an exception
    if the 'cmd' return code is not zero.

    :param cmd: Command line to run.
    :param kwargs: Options etc.
    :return: (code, stdout, stderr) 3-tuples.
    '''
    (code, stdout, stderr) = _run(cmd, **kwargs)

    if code:
        raise RuntimeError(cmd, stdout, stderr, code)

    return code, stdout, stderr


def _rmdir(path):
    for name in os.listdir(path):
        full_path = os.path.join(path, name)
        if os.path.isfile(full_path) or os.path.islink(full_path):
            os.remove(full_path)
        else:
            shutil.rmtree(full_path)


class _CephTag(object):
    def __init__(self, path):
        super(_CephTag, self).__init__()

        if not os.path.isabs(path):
            raise ValueError('tag path: {0} is not an abs path'.format(path))

        self.path = path

    def remove(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class _CephOneLineTag(_CephTag):
    def __init__(self, path):
        super(_CephOneLineTag, self).__init__(path)

    def read(self):
        '''
        Get content of the tag file.

        :return: None if tag does not exist, or content of the tag.
        '''
        try:
            with open(self.path, 'rb') as fobj:
                line = fobj.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                return None
            raise

        # safe for empty line
        if line[-1:] != '\n':
            raise AssertionError(
                'content of tag: {0} does not end with \'\\n\''.format(self.path)
            )

        line = line[:-1]

        if '\n' in line:
            raise AssertionError(
                'content of tag: {0} has multiple lines'.format(self.path)
            )

        return line

    def write(self, line):
        '''
        Write text to tag file.
        :param line: Text to write.
        :return: None.
        '''
        if '\n' in line:
            raise ValueError(
                'content: {0} write to tag must not contain \'\\n\''
                .format(line)
            )

        (fd, path) = tempfile.mkstemp(prefix='tag.', dir=os.path.dirname(self.path))
        os.close(fd)

        with open(path, 'wb') as fobj:
            fobj.write(line + '\n')
            os.fsync(fobj.fileno())

        try:
            os.rename(path, self.path)
        except OSError as e:
            os.remove(path)
            raise

    def compare(self, line):
        if self.read() == line:
            return True
        return False


class _CephMultiLineTag(_CephTag):
    def __init__(self, path):
        super(_CephMultiLineTag, self).__init__(path)

    def read(self):
        '''
        Get content of the tag file.

        :return: None if tag does not exist, or content of the tag.
        '''
        try:
            with open(self.path, 'rb') as fobj:
                line = fobj.read()
                if line[-1:] != '\n':
                    raise AssertionError(
                        'content of tag: {0} does not end with \'\\n\''
                        .format(self.path)
                    )
                line = line[:-1]
                lines = line.split('\n')
                return lines
        except IOError as e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def write(self, lines):
        '''
        Write mutiple lines to tag file.

        :param lines: Content to write.
        :return: None.
        '''
        if not isinstance(lines, list):
            raise ValueError('Content must be a list')

        for line in lines:
            if '\n' in line:
                raise ValueError(
                    'content: {0} write to tag must not contain \'\\n\''
                    .format(line)
                )

        (fd, path) = tempfile.mkstemp(prefix='tag.', dir=os.path.dirname(self.path))
        os.close(fd)

        with open(path, 'wb') as fobj:
            for line in lines:
                fobj.write(line + '\n')
            os.fsync(fobj.fileno())

        try:
            os.rename(path, self.path)
        except OSError as e:
            os.remove(path)
            raise

    def compare(self, lines):
        if self.read() == lines:
            return True
        return False


class _CephConf(object):
    def __init__(self, cluster=CEPH_CLUSTER, conf=''):
        super(_CephConf, self).__init__()

        if cluster is None:
            cluster = CEPH_CLUSTER
        if conf is None:
            conf = ''

        self.cluster, self.conf = self.normalize(cluster, conf)
        self.parser = ConfigParser.SafeConfigParser()

    @classmethod
    def normalize(cls, cluster=CEPH_CLUSTER, conf=''):
        if cluster is None:
            cluster = CEPH_CLUSTER
        if conf is None:
            conf = ''

        if cluster:
            if '.' in cluster:
                raise ValueError('cluster name: {0} contains dot'.format(cluster))

        if conf:
            if not os.path.isabs(conf):
                raise ValueError(
                    'ceph conf: {0} is not an abs path'.format(conf)
                )
            if not conf.endswith('.conf'):
                raise ValueError(
                    'ceph conf: {0} does not end with .conf'.format(conf)
                )

        if not cluster and not conf:
            cluster = CEPH_CLUSTER
            conf = ''
        elif not cluster:
            cluster = conf.split('/')[-1].split('.')[0]
        elif not conf:
            conf = '/etc/ceph/{0}.conf'.format(cluster)

        return cluster, conf

    def open(self):
        with _CephIniFile(self.conf) as fobj:
            self.parser.readfp(fobj)
        return self.parser

    def write(self):
        with open(self.conf, 'wb') as fobj:
            self.parser.write(fobj)

    def get_conf(self, key, name=''):
        '''
        Get config value of a key.

        Note:

        :param key: The key whose value is to get.
        :param name: ceph entity name.
        :return: Value of the key, None if not set.
        '''
        # To get the value from the config file
        cmd = ['ceph-conf']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        if name:
            cmd.append('--name {0}'.format(name))
        cmd.append('--lookup {0}'.format(key))

        (code, stdout, stderr) = _run(cmd)

        if not code:
            value = stdout.strip().split('\n', 1)
            if len(value) != 1:
                raise AssertionError('Weird ceph-conf output: {0}'.format(value))
            value = value[0]
            if not value:
                return None
            return value

        if code != 1:   # ceph-conf return 1 if entry not found
            raise RuntimeError(cmd, stderr, code)

        # Fallback to get the value if the daemon knows
        cmd = ['ceph-conf']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        if name:
            cmd.append('--name {0}'.format(name))
        cmd.append('--show-config-value {0}'.format(key))

        # Unfortunately as shown in ceph/src/common/config.cc --show-config-value
        # only has two exit codes: 0 or 1, and 1 are used for both option does not
        # exist or error occurred
        (code, stdout, _) = _run(cmd)

        if not code:
            value = stdout.strip().split('\n', 1)
            if len(value) != 1:
                raise AssertionError('Weird ceph-conf output: {0}'.format(value))
            value = value[0]
            if not value:
                return None
            return value

        return None


class _CephDev(object):
    def __init__(self, dev, dtype):
        '''
        Init _CephDev object.

        :param dev: Device full path name.
        :param dtype: Device type.
        :return: None.
        '''
        super(_CephDev, self).__init__()

        if dev is None:
            raise ValueError('Device path must not be None')
        if not os.path.isabs(dev):
            raise ValueError('Device: {0} is not an abs path'.format(dev))
        if not os.path.exists(dev):
            raise ValueError('Device: {0} does not exist'.format(dev))

        if dtype not in (_CephDevType.DISK, _CephDevType.PART, _CephDevType.LV,
                         _CephDevType.DIR, _CephDevType.FILE):
            raise ValueError('Not supported type: {0}'.format(dtype))

        self.odev = dev
        self.dev = os.path.realpath(dev)
        self.type = dtype

    @classmethod
    def get_dev_type(cls, dev):
        '''
        Detect the type of a given device.

        :param dev: The device path to be detected.
        :return: The type of the device.
        '''
        if dev is None:
            raise ValueError('Device path must not be None')
        if not os.path.isabs(dev):
            raise ValueError('Device: {0} is not an abs path'.format(dev))
        if not os.path.exists(dev):
            raise ValueError('Device: {0} does not exist'.format(dev))

        dev = os.path.realpath(dev)

        dev_type = _CephDevType.OTHER

        mode = os.stat(dev).st_mode
        if stat.S_ISDIR(mode):
            dev_type = _CephDevType.DIR
        elif stat.S_ISREG(mode):
            dev_type = _CephDevType.FILE
        elif stat.S_ISBLK(mode):
            dev_type = cls.__get_blk_dev_type(dev)

        return dev_type

    @classmethod
    def __get_blk_dev_type(cls, dev):
        '''
        Detect the type of a given block device.

        :param dev: The block device path to be detected.
        :return: The type of the block device.
        '''
        dev_name = cls.__get_blk_dev_name(dev)

        # Check LVM2 LV
        if dev_name.startswith('dm-'):
            lvs = cls.__get_lv_list()
            if dev in lvs:
                return _CephDevType.LV
            else:
                return _CephDevType.OTHER

        # Check whole disk
        if os.path.exists(os.path.join('/sys/block', dev_name)):
            return _CephDevType.DISK

        # Check partition
        pardev_name = dev_name
        while len(pardev_name):
            fpath = '/sys/block/{pardev}/{dev}'\
                .format(pardev=pardev_name, dev=dev_name)
            if os.path.exists(fpath):
                return _CephDevType.PART
            pardev_name = pardev_name[:-1]

        return _CephDevType.OTHER

    @classmethod
    def __get_lv_list(cls):
        '''
        Get all LVM2 LV device(s).

        Note: Any symbolic links are eliminated!

        :return: A list of logical volumes on this host.
        '''
        if not utils.which('lvs'):
            return set()

        cmd = ['lvs']
        cmd.append('--noheadings')
        cmd.append('-o lv_path')

        (_, stdout, _) = _check_run(cmd)

        lines = stdout.splitlines()

        lvs = set()
        for line in lines:
            line = line.strip()
            if line:
                lv = os.path.realpath(line)
                lvs.add(lv)

        return lvs

    @classmethod
    def __get_blk_dev_name(cls, path):
        '''
        Get the name of a block device by given a full path name.

        For example:
            /dev/sda -> sda
            /dev/sda1 -> sda1
            /dev/cciss/c0d1 -> cciss!c0d1
            /dev/cciss/c0d1p1 -> cciss!c0d1p1

        :param dev: The full path name of the block device.
        :return: Device name of the given device path.
        '''
        name = path[5:]
        return name.replace('/', '!')

    @classmethod
    def __get_blk_dev_path(cls, name):
        '''
        Get full path with a given device name.

        For example:
            sda -> /dev/sda
            sda1 -> /dev/sda1
            cciss!c0d1 -> /dev/cciss/c0d1
            cciss!c0d1p1 -> /dev/cciss/c0d1p1

        :param name: The device name.
        :return: Full path of the device.
        '''
        return '/dev/' + name.replace('!', '/')

    @classmethod
    def __get_blk_dev_relpath(cls, name):
        '''
        Get relative path with a given device name.

        For example:
            sda -> sda
            sda1 -> sda1
            cciss!c0d1 -> cciss/c0d1
            cciss!c0d1p1 -> cciss/c0d1p1

        :param name: The device name.
        :return: Relative path of the device.
        '''
        return name.replace('!', '/')

    @classmethod
    def __get_part_num(cls, part):
        '''
        Get disk and partition number of a given partition name.
        :param part: Partition name.

        For example:
            /dev/sda1 -> (/dev/sda, 1)
            /dev/cciss/c0d1p1 -> (/dev/cciss/c0d1, 1)

        :return: (disk, num) 2-tuples of this partition.
        '''
        if 'loop' in part or 'cciss' in part:
            (disk, num) = re.match('(.*\d+)p(\d+)', part).group(1, 2)
        else:
            (disk, num) = re.match('(\D+)(\d+)', part).group(1, 2)

        return disk, num

    @classmethod
    def __get_part_path(cls, disk, num):
        '''
        Get partition name with given (base, num) 2-tuples.

        For example:
            (/dev/sda, 1) -> /dev/sda1
            (/dev/cciss/c0d1, 1) -> /dev/cciss/c0d1p1

        :param disk: Disk the partition is on.
        :param num: Partition number of the disk.
        :return: Partition name.
        '''
        if 'loop' in disk or 'cciss' in disk:
            part = disk + 'p' + str(num)
        else:
            part = disk + str(num)

        return part

    def is_disk(self):
        return self.type == _CephDevType.DISK

    def is_part(self):
        return self.type == _CephDevType.PART

    def is_lv(self):
        return self.type == _CephDevType.LV

    def is_file(self):
        return self.type == _CephDevType.FILE

    def is_dir(self):
        return self.type == _CephDevType.DIR

    def is_blk(self):
        return self.is_disk() or self.is_part() or self.is_lv()

    def get_disk_label(self):
        '''
        Detect disk label (partition table) type.

        Note: 'blkid' is much simper than parted, it's not as robust
        as 'parted' though.

        :return: Partition table type of the given disk.
        '''
        # '--machine' option of 'parted' has very very weird behavior on disk that
        # 'sgdisk' has created partitions on!!!
        if not self.is_disk():
            raise AssertionError('Not a disk dev')

        cmd = ['parted']
        cmd.append('--script')
        cmd.append('--')
        cmd.append(self.dev)
        cmd.append('print')

        (code, stdout, stderr) = _run(cmd)

        # TODO: read 'parted' source to get rid of this magic errno.
        if code:
            if code != 1:
                raise RuntimeError(cmd, stderr, code)

        lines = stdout.splitlines()
        pts = None

        for line in lines:
            m = re.match('Partition Table: (\S+)', line)
            if m:
                pts = m.group(1)
                break

        if pts is not None:
            if pts == 'unknown':
                part_type = _CephPartType.NONE
            elif pts == 'gpt':
                part_type = _CephPartType.GPT
            elif pts == 'msdos':
                part_type = _CephPartType.DOS
            else:
                part_type = _CephPartType.OTHER

            return part_type

        raise AssertionError('No disk label found on disk: {0}'.format(self.dev))

    def get_part_fs(self):
        '''
        Detect filesystem type of given partition or LV.

        :return: Filesystem type of the given partition or LV.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        fs_type = _CephFsType.NONE

        cmd = ['blkid']
        cmd.append('-p')
        cmd.append('-o value')
        cmd.append('-s TYPE')
        cmd.append('--')
        cmd.append(self.dev)

        (code, stdout, stderr) = _run(cmd)

        if code:
            if code == errno.ENOENT:
                return fs_type
            raise RuntimeError(cmd, stderr, code)

        data = stdout

        if data == 'xfs':
            fs_type = _CephFsType.XFS
        elif data == 'ext4':
            fs_type = _CephFsType.EXT4
        elif data == 'btrfs':
            fs_type = _CephFsType.BTRFS
        else:
            fs_type = _CephFsType.OTHER

        return fs_type

    def get_part_info(self):
        '''
        Get partition info.

        :return: (guid, typecode, name) 3-tuples.
        '''
        if not self.is_part():
            raise AssertionError('Not a partition')

        (disk, num) = self.__get_part_num(self.dev)

        (guid, typecode, name) = (None, None, None)

        cmd = ['sgdisk']
        cmd.append('--info={0}'.format(num))
        cmd.append(disk)

        # sgdisk will not fail even if part does not exist
        (_, stdout, _) = _check_run(cmd)

        data = stdout.splitlines()

        for line in data:
            m = re.match('Partition GUID code: (\S+)', line)
            if m:
                typecode = m.group(1).lower()
                continue
            m = re.match('Partition unique GUID: (\S+)', line)
            if m:
                guid = m.group(1).lower()
                continue
            m = re.match('Partition name (\S+)', line)
            if m:
                name = m.group(1).strip('\'')

        return guid, typecode, name

    def get_disk_part_list(self):
        '''
        Get partition number list of the given disk.

        :return: A list of partition number of the disk.
        '''
        # '--machine' option of 'parted' has very very weird behavior on disk that
        # 'sgdisk' has created partitions on!!!
        if not self.is_disk():
            raise AssertionError('Not a disk')

        cmd = ['sgdisk']
        cmd.append('--print')
        cmd.append('--')
        cmd.append(self.dev)

        (_, stdout, _) = _check_run(cmd)

        lines = stdout.splitlines()

        parts = set()
        for line in lines:
            m = re.match('\s+(\d+)\s+\d+\s+\d+\s+\S+ \S+B\s+\S+\s*', line)
            if m:
                num = int(m.group(1))
                parts.add(num)

        # TODO: remove?
        for num in parts:
            part = self.__get_part_path(self.dev, num)
            disk_name = self.__get_blk_dev_name(self.dev)
            part_name = self.__get_blk_dev_name(part)

            fpath = '/sys/block/{disk}/{part}'.format(disk=disk_name, part=part_name)
            if not os.path.exists(fpath):
                raise AssertionError('Kernel not sync with disk?')

        return parts

    def get_disk_part(self, num):
        '''
        Get partition path for a given paritition number.

        :param num: Partition number.
        :return: None if not exist or Partition full path.
        '''
        if not self.is_disk():
            raise AssertionError('Not a disk')

        return self.__get_part_path(self.dev, num)

    def get_free_part_num(self):
        '''
        Get the next free partition number on a given device.

        :return: The available free partition number.
        '''
        if not self.is_disk():
            raise AssertionError('Not a disk')

        parts = self.get_disk_part_list()

        num = 1
        while num in parts:
            num += 1

        return num

    def get_part_disk(self):
        '''
        Get disk path from partition path.
        :return: Disk path.
        '''
        if not self.is_part():
            raise AssertionError('Not a partition')

        (disk, _) = self.__get_part_num(self.dev)

        return disk

    def get_part_num(self):
        '''
        Get partition number from partition path.
        :return: Partition number.
        '''
        if not self.is_part():
            raise AssertionError('Not a partition')

        (_, num) = self.__get_part_num(self.dev)

        return num

    def make_disk_label(self):
        '''
        Make gpt label on disk, old partition table will be destroyed.

        :return: None.
        '''
        if not self.is_disk():
            raise AssertionError('Not a disk')

        cmd = ['parted']
        cmd.append('--machine')
        cmd.append('--script')
        cmd.append('--')
        cmd.append(self.dev)
        cmd.append('mklabel')
        cmd.append('gpt')

        _check_run(cmd)

    def make_disk_part(self, num, size, guid, typecode, name):
        '''
        Create a new partition on given disk.

        :param num: Partition number.
        :param size: Size of the partition, unit in MB, 0 if the partition will
        fill the largest available block of space on the disk.
        :param guid: Partition unique GUID.
        :param typecode: Partition's type code.
        :param name: Partition's name.
        :return: Partition number of the newly created partition.
        '''
        # From 'sgdisk' version greater than 0.8.10 on 'sgdisk --new' support
        # set 'num' to 0 and let 'sgdisk' to choose the next free partition
        # number, but still lacks an convenient way to get the new created
        # partition number. B.T.W. 'sgdisk --largest-new=0' is broken on many
        # versions (e.g. 0.8.6, 0.8.8, 0.8.10 etc.).
        if not self.is_disk():
            raise AssertionError('Not a disk')

        if size:
            part = '--new={num}:0:+{size}M'.format(num=num, size=size)
        else:
            part = '--largest-new={0}'.format(num)

        cmd = ['sgdisk']
        cmd.append(part)
        cmd.append('--partition-guid={num}:{guid}'.format(num=num, guid=guid))
        cmd.append('--typecode={num}:{typecode}'.format(num=num, typecode=typecode))
        cmd.append('--change-name={num}:{name}'.format(num=num, name=name))
        cmd.append('--')
        cmd.append(self.dev)

        _check_run(cmd)

    def remove_disk_part(self, num):
        '''
        Delete partition on given disk.

        :param num: Partition number.
        :return: None.
        '''
        if not self.is_disk():
            raise AssertionError('Not a disk')

        cmd = ['sgdisk']
        cmd.append('--delete={0}'.format(num))
        cmd.append('--')
        cmd.append(self.dev)

        _check_run(cmd)

    def make_part_fs(self, fstype, options=''):
        '''
        Make filesystem on partition or LV.

        :param fstype: Filesystem type, type is in string.
        :param options: Options used to make filesystem.
        :return: None.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        options = options.split()

        if fstype == 'xfs':
            options.append('-f')

        cmd = ['mkfs']
        cmd.append('-t {0}'.format(fstype))
        cmd.extend(options)
        cmd.append('--')
        cmd.append(self.dev)

        _check_run(cmd)

    def set_part_info(self, guid=None, typecode=None, name=None):
        '''
        Set parition info.

        :param guid: Partition unique GUID.
        :param typecode: Partition's type code.
        :param name: Partition's name.
        :return: Partition number of the newly created partition.
        '''
        if not self.is_part():
            raise AssertionError('Not a disk')

        (disk, num) = self.__get_part_num(self.dev)

        cmd = ['sgdisk']
        if guid is not None:
            cmd.append('--partition-guid={num}:{guid}'.format(num=num, guid=guid))
        if typecode is not None:
            cmd.append(
                '--typecode={num}:{typecode}'.format(num=num, typecode=typecode)
            )
        if name is not None:
            cmd.append('--change-name={num}:{name}'.format(num=num, name=name))
        cmd.append('--mbrtogpt')    # Aha, no necessary but no harm :)
        cmd.append('--')
        cmd.append(disk)

        _check_run(cmd)

    def get_mount_info(self):
        '''
        Get mount info of the partition or LV.

        :return: (path, fstype, options) 3-tuples if the device is mounted or None.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        with open('/proc/mounts', 'rb') as mounts:
            for line in mounts:
                fields = line.split()
                if len(fields) < 3:
                    continue
                dev = fields[0]
                if dev.startswith('/dev/') and os.path.exists(dev):
                    dev = os.path.realpath(dev)
                    if dev == self.dev:
                        return fields[1], fields[2], fields[3]

        return None, None, None

    def mount(self, path, fstype, options=''):
        '''
        Mount the partition or LV to a given location.

        :param path: Mount point.
        :param fstype: Filesystem type of the partition or LV.
        :param options: Mount options.
        :return: None.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        cmd = ['mount']
        cmd.append('-t {0}'.format(fstype))
        if options.strip():
            cmd.append('-o {0}'.format(options))
        cmd.append('--')
        cmd.append(self.dev)
        cmd.append(path)

        _check_run(cmd)

        return path

    def mount_tmp(self, fstype, options=''):
        '''
        Mount the partition or LV to a temp location.

        :param fstype: Filesystem type of the partition or LV.
        :param options: Mount options.
        :return: The location the device mounted on.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        path = tempfile.mkdtemp(prefix='ceph.mnt.')

        self.mount(path, fstype, options)

        return path

    def umount(self, path=None, umount_all=False):
        '''
        Unmount the mounted device or path.

        :return: None.
        '''
        if path:
            if not os.path.isabs(path):
                raise AssertionError('Path to umount is not abs')
            if not os.path.exists(path):
                raise AssertionError('Path to umount does not exist')
        else:
            if not self.is_part() and not self.is_lv():
                raise AssertionError('Not a partition or LVM2 logical volume')

        cmd = ['umount']
        cmd.append('--force')
        if umount_all:
            cmd.append('--all-targets')
        cmd.append('--')
        if path:
            cmd.append(path)
        else:
            cmd.append(self.dev)

        retries = 0
        while True:
            (code, _, stderr) = _run(cmd)

            if code:
                if retries == 3:
                    raise RuntimeError(cmd, stderr, code)
                time.sleep(0.5 + retries * 1.0)
                retries += 1
            else:
                break

    def move_mount(self, opath, npath, fstype, options):
        '''
        Move an mount from an old mount point to a new mount point.

        :param opath: Old mount point.
        :param npath: New mount point.
        :param fstype: Filesystem type of the partition or LV
        :param options: Mount options.
        :return: None.
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        # we really want to mount --move, but that is not supported when
        # the parent mount is shared, as it is by default on RH, Fedora,
        # and probably others.  Also, --bind doesn't properly manipulate
        # /etc/mtab, which *still* isn't a symlink to /proc/mounts despite
        # this being 2013.  Instead, mount the original device at the final
        # location.
        self.mount(npath, fstype, options)
        self.umount(opath)

    def clear_disk(self):
        '''
        Destroy the partition table.

        :return: None.
        '''
        if not self.is_disk():
            raise AssertionError('Not a disk')

        cmd = ['sgdisk']
        cmd.append('--clear')
        cmd.append('--')
        cmd.append(self.dev)

        _check_run(cmd)

    def clear_part(self):
        '''
        Destroy partition or LVM logical volume.

        :return: None
        '''
        if not self.is_part() and not self.is_lv():
            raise AssertionError('Not a partition or LVM2 logical volume')

        bs = 2048
        size = 128 * bs
        with open(self.dev, 'wb') as fobj:
            fobj.write(size*'\0')

    def clear_dir(self):
        '''
        Clear directory content.

        :return: None.
        '''
        if not self.is_dir():
            raise AssertionError('Not a directory')
        _rmdir(self.dev)

    def zap_disk(self):
        '''
        Destroy the partition table and make a new gpt label.

        :return: None.
        '''
        # try to wipe out any GPT partition table backups.  sgdisk
        # isn't too thorough.
        if not self.is_disk():
            raise AssertionError('Not a disk')

        lba_size = 4096
        size = 33 * lba_size
        with open(self.dev, 'wb') as fobj:
            fobj.seek(-size, os.SEEK_END)
            fobj.write(size*'\0')

        cmd = ['sgdisk']
        cmd.append('--zap-all')
        cmd.append('--clear')
        cmd.append('--mbrtogpt')
        cmd.append('--')
        cmd.append(self.dev)

        _check_run(cmd)


class _CephDaemon(object):
    def __init__(self, etype, eid, cluster=CEPH_CLUSTER):
        super(_CephDaemon, self).__init__()

        if etype not in ['mon', 'osd', 'mds', 'client']:
            raise ValueError('Invalid daemon type: {0}'.format(etype))

        cfg = _CephConf(cluster)

        self.cluster = cfg.cluster
        self.conf = cfg.conf
        self.cfg = cfg
        self.type = etype
        self.id = eid
        self.name = '{type}.{id}'.format(type=etype, id=eid)

    @classmethod
    def start_mon(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('start')
        cmd.append('mon')

        _check_run(cmd)

    @classmethod
    def start_osd(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('start')
        cmd.append('osd')

        _check_run(cmd)

    @classmethod
    def start_mds(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('start')
        cmd.append('mds')

        _check_run(cmd)

    @classmethod
    def start_all(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('start')

        _check_run(cmd)

    @classmethod
    def stop_mon(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('stop')
        cmd.append('mon')

        _check_run(cmd)

    @classmethod
    def stop_osd(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('stop')
        cmd.append('osd')

        _check_run(cmd)

    @classmethod
    def stop_mds(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('stop')
        cmd.append('mds')

        _check_run(cmd)

    @classmethod
    def stop_all(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('stop')

        _check_run(cmd)

    @classmethod
    def restart_mon(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('restart')
        cmd.append('mon')

        _check_run(cmd)

    @classmethod
    def restart_osd(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('restart')
        cmd.append('osd')

        _check_run(cmd)

    @classmethod
    def restart_mds(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('restart')
        cmd.append('mds')

        _check_run(cmd)

    @classmethod
    def restart_all(cls, cluster=CEPH_CLUSTER):
        cfg = _CephConf(cluster)

        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('restart')

        _check_run(cmd)

    def start(self):
        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('start')
        cmd.append(self.name)

        _check_run(cmd)

    def stop(self):
        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('stop')
        cmd.append(self.name)

        _check_run(cmd)

    def restart(self):
        cmd = ['/etc/init.d/ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('restart')
        cmd.append(self.name)

        _check_run(cmd)

    def status(self):
        pass

    def is_running(self):
        pass


class _CephOsdDaemonState(object):
    DEAD = 0
    RUNNING = 1


class _CephOsdDaemon(_CephDaemon):
    def __init__(self, osdid, cluster=CEPH_CLUSTER):
        super(_CephOsdDaemon, self).__init__('osd', osdid, cluster)

    def status(self):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('daemon')
        cmd.append(self.name)
        cmd.append('status')

        (code, _, stderr) = _run(cmd)

        # TODO: Read ceph source to verify this errno.
        if code:
            if code == errno.EINVAL:
                return _CephOsdDaemonState.DEAD
            raise RuntimeError(cmd, stderr, code)

        return _CephOsdDaemonState.RUNNING

    def is_running(self):
        return self.status() != _CephOsdDaemonState.DEAD


class _CephMonDaemonState(object):
    DEAD = 0
    RUNNING = 1


class _CephMonDaemon(_CephDaemon):
    def __init__(self, monid, cluster=CEPH_CLUSTER):
        super(_CephMonDaemon, self).__init__('mon', monid, cluster)

    def status(self):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('daemon')
        cmd.append(self.name)
        cmd.append('mon_status')

        (code, _, stderr) = _run(cmd)

        # TODO: Read ceph source to verify this errno.
        if code:
            if code == errno.EINVAL:
                return _CephMonDaemonState.DEAD
            raise RuntimeError(cmd, stderr, code)

        return _CephMonDaemonState.RUNNING

    def is_running(self):
        return self.status() != _CephMonDaemonState.DEAD


class _CephOsdState(object):
    FREE = 0,
    PREPARED = 1,       # data and journal device prepared, tag: 'magic'
    CREATED = 2,        # osd id generated, tag: 'whoami'
    READY = 3,          # ceph-osd --mkfs finished, tag: 'ready'
    ACTIVE = 4,         # entity authenticated, tag: 'active'


class _CephOsd(object):
    def __init__(self, data, journal='', cluster=CEPH_CLUSTER):
        super(_CephOsd, self).__init__()

        if journal is None:
            journal = ''
        if cluster is None:
            cluster = CEPH_CLUSTER

        cfg = _CephConf(cluster)

        if not os.path.exists(cfg.conf):
            raise AssertionError('ceph conf file does not exist')

        fsid_str = cfg.get_conf('fsid')
        fsid = None
        try:
            fsid = uuid.UUID(fsid_str)
        except:
            raise AssertionError('fsid is not valid')

        if fsid.int == 0:
            raise AssertionError('fsid not configured')

        fstype = self.__get_fs_type(cfg)
        if not self.__check_fs(fstype):
            raise AssertionError('Not supported OSD filesystem type configured')

        (ddev, jdev) = self.__check_dev(data, journal)

        self.cluster = cfg.cluster
        self.conf = cfg.conf
        self.cfg = cfg
        self.fsid = fsid

        self.data = data
        self.journal = journal
        self.dtype = ddev.type
        self.jtype = jdev.type if jdev else (ddev.type if journal else '')
        self.ddev = ddev
        self.jdev = jdev

        self._state = None

        self.__old_id = None
        self.__old_duuid = None
        self.__old_juuid = None
        self.__old_fstype = None
        self.__old_signature = None

    @property
    def state(self):
        return self._state

    @classmethod
    def __check_data_type(cls, dtype):
        if dtype not in (_CephDevType.DISK, _CephDevType.PART, _CephDevType.DIR):
            return False

        return True

    @classmethod
    def __check_journal_type(cls, jtype):
        if jtype not in (_CephDevType.DISK, _CephDevType.PART, _CephDevType.FILE):
            return False

        return True

    @classmethod
    def __check_dev(cls, data, journal):
        if not data:
            raise ValueError('OSD data must not be None')
        if not os.path.isabs(data):
            raise ValueError('OSD data: {0} is not an abs path'.format(data))
        if not os.path.exists(data):
            raise ValueError('OSD data: {0} does not exist'.format(data))

        if journal:
            if not os.path.isabs(data):
                raise ValueError(
                    'OSD journal: {0} is not an abs path'.format(journal)
                )
            if not os.path.exists(journal):
                raise ValueError(
                    'OSD journal: {0} does not exist'.format(journal)
                )

        # d: data
        # j: journal

        (ddev, jdev) = (None, None)

        dtype = _CephDev.get_dev_type(data)
        ddev = _CephDev(data, dtype)

        if not cls.__check_data_type(dtype):
            raise ValueError(
                'Type: {t} of data device: {d} is not supported'
                .format(d=data, t=dtype)
            )

        if journal:
            jtype = _CephDev.get_dev_type(journal)
            jdev = _CephDev(journal, jtype)

            if not cls.__check_journal_type(jtype):
                raise ValueError(
                    'Type: {t} of journal device: {j} is not supported'
                    .format(j=journal, t=jtype)
                )

            if jdev.is_part():
                disk = jdev.get_part_disk()
                if disk == ddev.dev:
                    raise ValueError(
                        'Data device: {d} and journal device: {j} conflict'
                        .format(d=data, j=journal))

            if ddev.dev == jdev.dev:
                jdev = None

        return ddev, jdev

    @classmethod
    def __detect_osd(cls, dev):
        (state, osdid, duuid, juuid, fstype, signature) = \
            (None, None, None, None, None, None)
        dummy = (None, None, None, None, None, None)

        rddev = None
        fstype = None

        if dev.is_disk():
            label = dev.get_disk_label()
            if label == _CephPartType.NONE:
                return dummy

            if label != _CephPartType.GPT:
                return dummy

            parts = dev.get_disk_part_list()

            if parts == set():
                return dummy

            if parts not in (set([1]), set([1, 2])):
                return dummy

            # may have been prepared by ceph-disk
            rdata = dev.get_disk_part(1)

            if not os.path.exists(rdata):
                raise AssertionError('Kernel not sync with disk?')

            rddev = _CephDev(rdata, _CephDevType.PART)

            (_, typecode, _) = rddev.get_part_info()

            if typecode != OSD_UUID:
                return dummy

            fstype = rddev.get_part_fs()

            if not cls.__check_fs(fstype):
                return dummy

            if parts == set([1, 2]):
                rjournal = dev.get_disk_part(2)

                if not os.path.exists(rjournal):
                    raise AssertionError('Kernel not sync with disk?')

                rjdev = _CephDev(rjournal, _CephDevType.PART)

                (_, typecode, _) = rjdev.get_part_info()

                if typecode != JOURNAL_UUID:
                    return dummy
        elif dev.is_part():
            rddev = dev

            fstype = rddev.get_part_fs()

            if not cls.__check_fs(fstype):
                return dummy

        mount = False   # data device mounted by us manually
        path = ''       # location of OSD fs

        try:
            if dev.is_disk() or dev.is_part():
                (path, _, _) = rddev.get_mount_info()

                if path is None:
                    # not mounted, mount to a tmp location manually
                    path = rddev.mount_tmp(fstype)
                    mount = True
            else:
                # data device is a directory
                path = dev.dev

            # check
            state = cls.__get_state(path)
            osdid = cls.__get_id(path)
            duuid = cls.__get_data_uuid(path)
            juuid = cls.__get_journal_uuid(path)
            signature = cls.__read_signature(path)

            return state, osdid, duuid, juuid, fstype, signature
        finally:
            if mount:
                rddev.umount(path)
                os.rmdir(path)

    @classmethod
    def __clear_dev(cls, dev):
        if dev.is_disk():
            if dev.get_disk_label() != _CephPartType.GPT:
                dev.make_disk_label()
            else:
                dev.clear_disk()

            cmd = ['partprobe']
            cmd.append(dev.dev)
            _run(cmd)
        elif dev.is_part():
            dev.clear_part()
        elif dev.is_dir():
            dev.clear_dir()

    @classmethod
    def __check_fs(cls, fstype):
        if fstype not in (_CephFsType.EXT4, _CephFsType.XFS, _CephFsType.BTRFS):
            return False

        return True

    @classmethod
    def __get_state(cls, path):
        state = None

        tag = _CephOneLineTag(os.path.join(path, 'magic'))
        magic = tag.read()
        tag = _CephOneLineTag(os.path.join(path, 'whoami'))
        whoami = tag.read()
        tag = _CephOneLineTag(os.path.join(path, 'ready'))
        ready = tag.read()
        tag = _CephOneLineTag(os.path.join(path, 'active'))
        active = tag.read()

        if magic is not None:
            state = _CephOsdState.PREPARED
        elif whoami is not None:
            raise AssertionError('corrupted osd filesystem')
        if whoami is not None:
            state = _CephOsdState.CREATED
        elif ready is not None:
            raise AssertionError('corrupted osd filesystem')
        if ready is not None:
            state = _CephOsdState.READY
        elif active is not None:
            raise AssertionError('corrupted osd filesystem')
        if active is not None:
            state = _CephOsdState.ACTIVE

        return state

    @classmethod
    def __get_id(cls, path):
        tag = _CephOneLineTag(os.path.join(path, 'whoami'))
        whoami = tag.read()

        if whoami is None:
            return None

        try:
            osdid = int(whoami)
        except ValueError:
            raise AssertionError('corrupted whoami: {0}'.format(whoami))

        return osdid

    @classmethod
    def __get_fsid(cls, path):
        tag = _CephOneLineTag(os.path.join(path, 'ceph_fsid'))

        return tag.read()

    @classmethod
    def __get_data_uuid(cls, path):
        tag = _CephOneLineTag(os.path.join(path, 'fsid'))

        return tag.read()

    @classmethod
    def __get_journal_uuid(cls, path):
        tag = _CephOneLineTag(os.path.join(path, 'journal_uuid'))

        return tag.read()

    @classmethod
    def __read_signature(cls, path):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        return tag.read()

    @classmethod
    def __write_signature(cls, path, sig):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        tag.write(sig)

    @classmethod
    def __remove_signature(cls, path):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        tag.remove()

    @classmethod
    def __parse_signature(cls, sig):
        sig = [x.split('=', 1) for x in sig]

        return dict(sig)

    @classmethod
    def __get_osd_data(cls, osdid, cfg):
        # ignore ceph.conf and return osd_data always point to
        # /var/lib/ceph/osd/$cluster.$id !!!
        # it's not my fault, blame to ceph-disk :)
        return '/var/lib/ceph/osd/{cluster}-{id}'\
            .format(cluster=cfg.cluster, id=osdid)

    @classmethod
    def __get_fs_type(cls, cfg):
        fstype = cfg.get_conf('osd_mkfs_type')

        if fstype is None:
            fstype = cfg.get_conf('osd_fs_type')

        if fstype is None:
            fstype = DEFAULT_FS_TYPE

        return fstype

    @classmethod
    def __get_mkfs_options(cls, cfg):
        fstype = cls.__get_fs_type(cfg)

        options = cfg.get_conf('osd_mkfs_options_{0}'.format(fstype))

        if options is None:
            options = cfg.get_conf('osd_fs_mkfs_options_{0}'.format(fstype))

        if options is None:
            options = MKFS_OPTIONS.get(fstype, '')

        return options

    @classmethod
    def __get_mount_options(cls, cfg):
        fstype = cls.__get_fs_type(cfg)

        options = cfg.get_conf('osd_mount_options_{0}'.format(fstype))

        if options is None:
            options = cfg.get_conf('osd_fs_mount_options_{0}'.format(fstype))

        if options is None:
            options = MOUNT_OPTIONS.get(fstype, '')

        return options

    @classmethod
    def __unregister(cls, osdid, cfg):
        name = 'osd.{0}'.format(osdid)

        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('osd')
        cmd.append('crush')
        cmd.append('rm')
        cmd.append(name)

        _check_run(cmd)

    @classmethod
    def __remove_crush(cls, osdid, cfg):
        name = 'osd.{0}'.format(osdid)

        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('osd')
        cmd.append('rm')
        cmd.append(name)

        _check_run(cmd)

    @classmethod
    def __remove_auth(cls, osdid, cfg):
        name = 'osd.{0}'.format(osdid)

        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(cfg.cluster))
        cmd.append('--conf {0}'.format(cfg.conf))
        cmd.append('auth')
        cmd.append('del')
        cmd.append(name)

        _check_run(cmd)

    def __signature(self):
        return ['magic={0}'.format('\xe8\x8e\x8e\xe5\xad\x90'),
                'version={0}'.format('v1'),
                'cluster={0}'.format(self.cluster),
                'fsid={0}'.format(self.fsid),
                'data={0}'.format(self.data),
                'journal={0}'.format(self.journal),
                'dtype={0}'.format(self.dtype),
                'jtype={0}'.format(self.jtype)]

    def __compare_signature(self, sig):
        if self.__signature() == sig:
            return True

        return False

    def __prepare(self):
        assert self._state == _CephOsdState.FREE

        parts_before = None
        parts_after = None

        diff = None
        if self.jdev is not None and self.jdev.is_disk():
            parts_before = self.jdev.get_disk_part_list()

        # prepare

        # ceph-disk does not support --conf
        cmd = ['ceph-disk']
        cmd.append('prepare')
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append(self.ddev.odev)
        if self.jdev is not None:
            cmd.append(self.jdev.odev)

        _check_run(cmd)

        # prepared, some checks

        rddev = self.ddev

        if self.ddev.is_disk():
            rdata = self.ddev.get_disk_part(1)
            rddev = _CephDev(rdata, _CephDevType.PART)

        if self.jdev is not None and self.jdev.is_disk():
            parts_after = self.jdev.get_disk_part_list()
            diff = parts_after - parts_before
            if len(diff) != 1:
                raise AssertionError('Disk operation racing with others?')

        path = ''

        try:
            if rddev.is_part():
                fstype = rddev.get_part_fs()

                path = rddev.mount_tmp(fstype)
            else:
                path = self.ddev.dev

            # write signature
            self.__write_signature(path, self.__signature())
            self._state = _CephOsdState.PREPARED
        finally:
            if rddev.is_part():
                rddev.umount(path)
                os.rmdir(path)

    def __activate(self):
        assert self._state >= _CephOsdState.PREPARED

        rdata = self.ddev.dev

        if self.ddev.is_disk():
            rdata = self.ddev.get_disk_part(1)

        # ceph-disk activate does not support both --cluster and --conf
        cmd = ['ceph-disk']
        cmd.append('activate')
        cmd.append(rdata)

        _check_run(cmd)

    # ### interface ### #

    def init(self):
        assert self._state is None

        (state, osdid, duuid, juuid, fstype, signature) = \
            self.__detect_osd(self.ddev)

        self.__old_id = osdid
        self.__old_duuid = duuid
        self.__old_juuid = juuid
        self.__old_fstype = fstype
        self.__old_signature = signature

        self._state = state or _CephOsdState.FREE

    def prepare(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) prepared'.format(
                d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        journalchanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            # TODO: Umount or warn user if device is mounted
            self.__clear_dev(self.ddev)
            datachanges.append('Clear data device')

            if self.jdev is not None and self.jdev.is_disk():
                if self.jdev.get_disk_label() != _CephPartType.GPT:
                    self.jdev.make_disk_label()
                    journalchanges.append('Make gpt label')

            self.__prepare()
            datachanges.append('Prepare device')

            changes[self.data] = datachanges
            if journalchanges:
                changes[self.journal] = journalchanges

            return ret

        if self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

        # signature match

        # TODO: Check if this is a disk from another machine

        ret['comment'] = 'OSD: ({d}, {j}) is prepared, skip'\
            .format(d=self.data, j=self.journal)

        return ret

    def activate(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) activated'.format(
                d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            return _error(ret, 'OSD: ({d}, {j}) is not prepared, skip'
                          .format(d=self.data, j=self.journal))

        if self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

        # signature match

        # TODO: Check if this is a disk from another machine

        # check if ever been activated

        state = self._state

        if state == _CephOsdState.PREPARED:
            self.__activate()

            datachanges.append('Create OSD entity')
            datachanges.append('Make OSD filesystem')
            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.CREATED:
            self.__activate()

            datachanges.append('Make OSD filesystem')
            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.READY:
            self.__activate()

            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.ACTIVE:
            daemon = _CephOsdDaemon(self.__old_id, self.cluster)
            if daemon.is_running():
                ret['comment'] = 'OSD: ({d}, {j}) is already activated, skip'\
                                 .format(d=self.data, j=self.journal)

                return ret

            self.__activate()

            datachanges.append('Start OSD daemon')

        changes[self.data] = datachanges

        return ret

    def manage(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) managed'.format(d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        journalchanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            # TODO: Umount or warn user if device is mounted
            self.__clear_dev(self.ddev)
            datachanges.append('Clear data device')

            if self.jdev is not None and self.jdev.is_disk():
                if self.jdev.get_disk_label() != _CephPartType.GPT:
                    self.jdev.make_disk_label()
                    journalchanges.append('Make gpt label')

            self.__prepare()
            datachanges.append('Prepare device')
        elif self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))
        elif not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

            # TODO: Check if this is a disk from another machine

        # new prepared device or signature match

        # check if ever been activated

        state = self._state

        if state == _CephOsdState.PREPARED:
            self.__activate()

            datachanges.append('Create OSD entity')
            datachanges.append('Make OSD filesystem')
            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.CREATED:
            self.__activate()

            datachanges.append('Make OSD filesystem')
            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.READY:
            self.__activate()

            datachanges.append('Authenticate OSD entity')
            datachanges.append('Start OSD daemon')
        elif state == _CephOsdState.ACTIVE:
            daemon = _CephOsdDaemon(self.__old_id, self.cluster)
            if daemon.is_running():
                ret['comment'] = 'OSD: ({d}, {j}) already managed, skip'\
                                 .format(d=self.data, j=self.journal)

                return ret

            self.__activate()

            datachanges.append('Start OSD daemon')

        changes[self.data] = datachanges

        return ret

    def unprepare(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) unprepared'.format(
                d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        journalchanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            ret['comment'] = 'OSD: ({d}, {j}) is not prepared, skip'\
                .format(d=self.data, j=self.journal)

            return ret

        if self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

        # signature match

        # TODO: Check if this is a disk from another machine

        if self._state > _CephOsdState.PREPARED:
            return _error(ret, 'OSD: ({d}, {j}) is activated, skip'
                          .format(d=self.data, j=self.journal))

        if self.jdev is not None and self.jdev.is_disk():
            if self.__old_juuid is None:
                raise AssertionError('corrupted osd filesystem')

            # journal device is created from another disk
            rjournal = '/dev/disk/by-partuuid/{0}'.format(self.__old_juuid)
            rjdev = _CephDev(rjournal, _CephDevType.PART)

            journal = rjdev.get_part_disk()
            num = rjdev.get_part_num()

            jdev = _CephDev(journal, _CephDevType.DISK)
            jdev.remove_disk_part(num)

            cmd = ['partprobe']
            cmd.append(self.jdev.dev)
            _run(cmd)

            journalchanges.append('Remove partition')

        self.__clear_dev(self.ddev)

        datachanges.append('Destroy device')

        if journalchanges:
            changes[self.journal] = journalchanges
        changes[self.data] = datachanges

        return ret

    def deactivate(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) deactivated'.format(
                d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        daemonchanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            ret['comment'] = 'OSD: ({d}, {j}) is not prepared, skip'\
                .format(d=self.data, j=self.journal)

            return ret

        if self._state == _CephOsdState.PREPARED:
            # not activated
            ret['comment'] = 'OSD: ({d}, {j}) is not activated, skip'\
                .format(d=self.data, j=self.journal)

            return ret

        if self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

        # signature match

        # TODO: Check if this is a disk from another machine

        osdid = self.__old_id
        fstype = self.__old_fstype

        rddev = None

        if self.ddev.is_disk():
            rdata = self.ddev.get_disk_part(1)
            rddev = _CephDev(rdata, _CephDevType.PART)
        elif self.ddev.is_part():
            rddev = self.ddev

        mount = False   # data device mounted by us manually
        path = ''       # location of OSD fs

        try:
            if self.ddev.is_disk() or self.ddev.is_part():
                (path, _, _) = rddev.get_mount_info()

                if path is None:
                    # not mounted, mount to a tmp location manually
                    path = rddev.mount_tmp(fstype)
                    mount = True
            else:
                # data device is a directory
                path = self.ddev.dev

            state = self._state

            if state == _CephOsdState.ACTIVE:
                daemon = _CephOsdDaemon(osdid, self.cluster)
                if daemon.is_running():
                    daemon.stop()

                    daemonchanges.append('Stop OSD daemon')

                self.__remove_auth(osdid, self.cfg)
                self.__remove_crush(osdid, self.cfg)

                tag = _CephOneLineTag(os.path.join(path, 'active'))
                tag.remove()

                daemonchanges.append('Remove OSD authentication')

                state = _CephOsdState.READY
            if state == _CephOsdState.READY:
                shutil.rmtree(os.path.join(path, 'current'))
                os.remove(os.path.join(path, 'superblock'))
                os.remove(os.path.join(path, 'store_version'))

                tag = _CephOneLineTag(os.path.join(path, 'ready'))
                tag.remove()

                daemonchanges.append('Remove OSD filesystem')

                state = _CephOsdState.CREATED
            if state == _CephOsdState.CREATED:
                self.__unregister(osdid, self.cfg)

                tag = _CephOneLineTag(os.path.join(path, 'whoami'))
                tag.remove()

                daemonchanges.append('Remove OSD entity')

                state = _CephOsdState.PREPARED

            self._state = state
        finally:
            if self.ddev.is_disk() or self.ddev.is_part():
                rddev.umount(umount_all=True)
                os.rmdir(path)

        changes['osd.{0}'.format(osdid)] = daemonchanges

        return ret

    def unmanage(self):
        ret = {
            'name': self.data,
            'result': True,
            'comment': 'OSD: ({d}, {j}) unmanaged'.format(
                d=self.data, j=self.journal),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        journalchanges = []
        daemonchanges = []

        # detect existing OSD
        self.init()

        if self._state == _CephOsdState.FREE:
            # not prepared
            ret['comment'] = 'OSD: ({d}, {j}) is not prepared, skip'\
                .format(d=self.data, j=self.journal)

            return ret

        if self.__old_signature is None:
            return _error(ret, 'OSD: ({d}, {j}) is prepared, but not by us, skip'
                          .format(d=self.data, j=self.journal))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['OSD: ({d}, {j}) is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(d=self.data, j=self.journal),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('data: {0}'.format(nsig['data']))
            new.append('journal: {0}'.format(nsig['journal']))
            new.append('data type: {0}'.format(nsig['dtype']))
            new.append('journal type: {0}'.format(nsig['jtype']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('data: {0}'.format(osig['data']))
            old.append('journal: {0}'.format(osig['journal']))
            old.append('data type: {0}'.format(osig['dtype']))
            old.append('journal type: {0}'.format(osig['jtype']))

            return ret

        # signature match

        # TODO: Check if this is a disk from another machine

        osdid = self.__old_id
        fstype = self.__old_fstype

        rddev = None

        if self.ddev.is_disk():
            rdata = self.ddev.get_disk_part(1)
            rddev = _CephDev(rdata, _CephDevType.PART)
        elif self.ddev.is_part():
            rddev = self.ddev

        mount = False   # data device mounted by us manually
        path = ''       # location of OSD fs

        try:
            if self.ddev.is_disk() or self.ddev.is_part():
                (path, _, _) = rddev.get_mount_info()

                if path is None:
                    # not mounted, mount to a tmp location manually
                    path = rddev.mount_tmp(fstype)
                    mount = True
            else:
                # data device is a directory
                path = self.ddev.dev

            state = self._state

            if state == _CephOsdState.ACTIVE:
                daemon = _CephOsdDaemon(osdid, self.cluster)
                if daemon.is_running():
                    daemon.stop()

                    daemonchanges.append('Stop OSD daemon')

                self.__remove_auth(osdid, self.cfg)
                self.__remove_crush(osdid, self.cfg)

                tag = _CephOneLineTag(os.path.join(path, 'active'))
                tag.remove()

                daemonchanges.append('Remove OSD authentication')

                state = _CephOsdState.READY
            if state == _CephOsdState.READY:
                tag = _CephOneLineTag(os.path.join(path, 'ready'))
                tag.remove()

                daemonchanges.append('Remove OSD filesystem')

                state = _CephOsdState.CREATED
            if state == _CephOsdState.CREATED:
                self.__unregister(osdid, self.cfg)

                tag = _CephOneLineTag(os.path.join(path, 'whoami'))
                tag.remove()

                daemonchanges.append('Remove OSD entity')

                state = _CephOsdState.PREPARED
            if state == _CephOsdState.PREPARED:
                if self.jdev is not None and self.jdev.is_disk():
                    if self.__old_juuid is None:
                        raise AssertionError('corrupted osd filesystem')

                    # journal device is created from another disk
                    rjournal = '/dev/disk/by-partuuid/{0}'.format(self.__old_juuid)
                    rjdev = _CephDev(rjournal, _CephDevType.PART)

                    journal = rjdev.get_part_disk()
                    num = rjdev.get_part_num()

                    jdev = _CephDev(journal, _CephDevType.DISK)
                    jdev.remove_disk_part(num)

                    cmd = ['partprobe']
                    cmd.append(self.jdev.dev)
                    _run(cmd)

                    journalchanges.append('Remove partition')

                self.__clear_dev(self.ddev)

                datachanges.append('Destroy device')

            self._state = state
        finally:
            if self.ddev.is_disk() or self.ddev.is_part():
                rddev.umount(umount_all=True)
                os.rmdir(path)

        if datachanges:
            changes[self.data] = datachanges
        if journalchanges:
            changes[self.journal] = journalchanges
        if daemonchanges:
            changes['osd.{0}'.format(osdid)] = daemonchanges

        return ret

    def takeover(self):
        pass

    def zap(self):
        pass


def osd_prepare(data,
                journal='',
                cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.prepare()


def osd_activate(data,
                 journal='',
                 cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.activate()


def osd_manage(data,
               journal='',
               cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.manage()


def osd_unprepare(data,
                  journal='',
                  cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.unprepare()


def osd_deactivate(data,
                   journal='',
                   cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.deactivate()


def osd_unmanage(data,
                 journal='',
                 cluster=CEPH_CLUSTER):
    osd = _CephOsd(data, journal, cluster)

    return osd.unmanage()


class _CephMonState(object):
    FREE = 1,
    READY = 2,
    ACTIVE = 3,


class _CephMon(object):
    def __init__(self,
                 mon_id,
                 auth_type='none',
                 mon_key='',
                 mon_addr='',
                 cluster=CEPH_CLUSTER):
        super(_CephMon, self).__init__()

        if auth_type is None:
            auth_type = 'none'
        if mon_key is None:
            mon_key = ''
        if mon_addr is None:
            mon_addr = ''
        if cluster is None:
            cluster = CEPH_CLUSTER

        if auth_type not in ['cephx', 'none']:
            raise AssertionError('Invalid auth_type: {0}'.format(auth_type))

        if auth_type == 'cephx' and not mon_key:
            raise AssertionError('cephx auth need auth key provided')

        cfg = _CephConf(cluster)

        if not os.path.exists(cfg.conf):
            raise AssertionError('ceph conf file does not exist')

        name = 'mon.{0}'.format(mon_id)

        mon_data = cfg.get_conf('mon_data', name)
        if not mon_data:
            raise AssertionError('mon_data mis-configured')
        if not os.path.isabs(mon_data):
            raise AssertionError(
                'mon_data configured is not an abs path'.format(mon_data)
            )

        fsid_str = cfg.get_conf('fsid')
        fsid = None
        try:
            fsid = uuid.UUID(fsid_str)
        except:
            raise AssertionError('fsid is not valid')

        if fsid.int == 0:
            raise AssertionError('fsid not configured')

        self.cluster = cfg.cluster
        self.conf = cfg.conf
        self.cfg = cfg
        self.fsid = fsid
        self.mon_id = mon_id
        self.auth_type = auth_type
        self.mon_key = mon_key
        self.mon_addr = mon_addr

        self.name = name
        self.mon_data = os.path.normpath(mon_data)

        self._state = None

        self.__old_signature = None

    @classmethod
    def __detect_mon(cls, path):
        (state, signature) = (None, None)

        state = cls.__get_state(path)
        signature = cls.__read_signature(path)

        return state, signature

    @classmethod
    def __get_state(cls, path):
        state = None

        tag = _CephOneLineTag(os.path.join(path, 'ready'))
        ready = tag.read()
        tag = _CephOneLineTag(os.path.join(path, 'active'))
        active = tag.read()

        if ready is not None:
            state = _CephMonState.READY
        elif active is not None:
            raise AssertionError('corrupted osd filesystem')
        if active is not None:
            state = _CephMonState.ACTIVE

        return state

    @classmethod
    def __read_signature(cls, path):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        return tag.read()

    @classmethod
    def __write_signature(cls, path, sig):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        tag.write(sig)

    @classmethod
    def __remove_signature(cls, path):
        tag = _CephMultiLineTag(os.path.join(path, 'signature'))

        tag.remove()

    @classmethod
    def __parse_signature(cls, sig):
        sig = [x.split('=', 1) for x in sig]

        return dict(sig)

    @property
    def state(self):
        return self._state

    def __signature(self):
        return ['magic={0}'.format('\xc3\xc3\xc8\xfd'),
                'version={0}'.format('v2'),
                'cluster={0}'.format(self.cluster),
                'fsid={0}'.format(self.fsid),
                'mon_id={0}'.format(self.mon_id),
                'auth_type={0}'.format(self.auth_type),
                'mon_key={0}'.format(self.mon_key),
                'mon_addr={0}'.format(self.mon_addr)]

    def __compare_signature(self, sig):
        if sig == self.__signature():
            return True

        return False

    def __mkfs(self):
        keyring = ''

        try:
            # prepare keyring
            if self.auth_type == 'cephx':
                (fd, keyring) = tempfile.mkstemp(
                    prefix='kr.', dir=os.path.dirname(self.mon_data)
                )
                os.close(fd)

                entity = _CephAuth('mon.', self.mon_key, mon_caps='allow *')
                entity.gen_keyring(keyring)

            # mkfs
            cmd = ['ceph-mon']
            cmd.append('--cluster {0}'.format(self.cluster))
            cmd.append('--conf {0}'.format(self.conf))
            cmd.append('--id {0}'.format(self.mon_id))
            cmd.append('--mkfs')
            if keyring:
                cmd.append('--keyring {0}'.format(keyring))
            if self.mon_addr:
                cmd.append('--public-addr {0}'.format(self.mon_addr))

            _check_run(cmd)

            tag = _CephOneLineTag(os.path.join(self.mon_data, 'ready'))
            tag.write('ready')
        finally:
            if os.path.exists(keyring):
                os.remove(keyring)

    def __register(self):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('mon')
        cmd.append('add')
        cmd.append(self.mon_id)

        _check_run(cmd)

    def __unregister(self):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('mon')
        cmd.append('remove')
        cmd.append(self.mon_id)

        _check_run(cmd)

    # ### interface ### #

    def init(self):
        assert self._state is None

        (state, signature) = self.__detect_mon(self.mon_data)

        self.__old_signature = signature
        self._state = state or _CephMonState.FREE

    def prepare(self):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} prepared'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []

        mon_id = self.mon_id
        mon_data = self.mon_data

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            # not prepared
            # prepare mon_data directory
            if not os.path.exists(mon_data):
                if os.path.islink(mon_data):
                    os.remove(mon_data)
                    datachanges.append('Remove dangling symbolic link')
                os.makedirs(mon_data)

                datachanges.append('New dir')
            else:
                if not os.path.isdir(mon_data):
                    os.remove(mon_data)
                    os.mkdir(mon_data)

                    datachanges.append('Not a dir, remove')
                    datachanges.append('New dir')
                elif os.listdir(mon_data):
                    _rmdir(mon_data)

                    datachanges.append('Clear mon data directory')

            # create mon fs
            self.__mkfs()

            # write signature
            self.__write_signature(mon_data, self.__signature())

            datachanges.append('Make mon filesystem')

            changes[mon_data] = datachanges

            return ret

        if self.__old_signature is None:
                # not managed by us
                return _error(ret, 'MON: mon.{0} is prepared, but not by us, skip'
                              .format(mon_id))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        # signature match

        ret['comment'] = 'MON: mon.{0} is already prepared, skip'.format(mon_id)

        return ret

    def activate(self, **kwargs):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} activated'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        confchanges = []
        daemonchanges = []

        host = None
        if 'host' in kwargs:
            host = kwargs['host']
            kwargs.pop('host')

        mon_id = self.mon_id
        name = self.name
        mon_data = self.mon_data
        daemon = _CephMonDaemon(self.mon_id, self.cluster)

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            return _error(ret, 'MON: mon.{0} is not prepared, skip'.format(mon_id))

        if self.__old_signature is None:
            # not managed by us
            return _error(ret, 'MON: mon.{0} is not prepared by us, skip'
                          .format(mon_id))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        # signature match

        state = self._state

        if state == _CephMonState.READY:
            # update ceph.conf
            opts = dict()
            if host and host != 'localhost':
                opts['host'] = host
            if self.mon_addr:
                opts['mon addr'] = self.mon_addr

            parser = self.cfg.open()
            write = True

            if not parser.has_section(name):
                parser.add_section(self.name)
                for opt, val in opts.iteritems():
                    parser.set(self.name, opt, val)

                confchanges.append('New section: {0}'.format(name))

                for opt, val in opts.iteritems():
                    confchanges.append('New option: {opt} = {val}'
                                       .format(opt=opt, val=val))
            else:
                # a list of (opt, value) tuples
                fopts = parser.items(name)
                add = set(opts.items())
                remove = set(fopts)

                if add != remove:
                    opts_add = add - remove
                    opts_remove = remove - add

                    for opt, val in opts_remove:
                        parser.remove_option(name, opt)

                        confchanges.append('Remove option: {opt} = {val}'
                                           .format(opt=opt, val=val))
                    for opt, val in opts_add:
                        parser.set(name, opt, val)

                        confchanges.append('New option: {opt} = {val}'
                                           .format(opt=opt, val=val))
                else:
                    write = False

            if write:
                self.cfg.write()

            tag = _CephOneLineTag(os.path.join(mon_data, 'active'))
            tag.write('active')

            state = _CephMonState.ACTIVE
        if state == _CephMonState.ACTIVE:
            if daemon.is_running():
                if self._state == _CephMonState.ACTIVE:
                    ret['comment'] = 'MON: mon.{0} is already activated, skip'\
                                     .format(mon_id)
                    return ret

                daemon.restart()
                daemonchanges.append('Restart daemon')
            else:
                # start daemon
                daemon.start()
                daemonchanges.append('Start daemon')

        if confchanges:
            changes[self.conf] = confchanges
        if daemonchanges:
            changes[name] = daemonchanges

        return ret

    def manage(self, **kwargs):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} managed'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        confchanges = []
        daemonchanges = []

        host = None
        if 'host' in kwargs:
            host = kwargs['host']
            kwargs.pop('host')

        mon_id = self.mon_id
        name = self.name
        mon_data = self.mon_data
        daemon = _CephMonDaemon(self.mon_id, self.cluster)

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            # prepare mon_data directory
            if not os.path.exists(mon_data):
                if os.path.islink(mon_data):
                    os.remove(mon_data)
                    datachanges.append('Remove dangling symbolic link')
                os.makedirs(mon_data)

                datachanges.append('New dir')
            else:
                if not os.path.isdir(mon_data):
                    os.remove(mon_data)
                    os.mkdir(mon_data)

                    datachanges.append('Not a dir, remove')
                    datachanges.append('New dir')
                elif os.listdir(mon_data):
                    _rmdir(mon_data)

                    datachanges.append('Clear mon data directory')
        elif self.__old_signature is None:
            # not managed by us
            return _error(ret, 'MON: mon.{0} is prepared, but not by us, skip'
                          .format(mon_id))
        elif not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        state = self._state

        if state == _CephMonState.FREE:
            # need to create mon fs
            self.__mkfs()

            # write signature
            self.__write_signature(mon_data, self.__signature())

            datachanges.append('Make mon filesystem')

            state = _CephMonState.READY
        if state == _CephMonState.READY:
            # update ceph.conf
            opts = dict()
            if host:
                opts['host'] = host
            if self.mon_addr:
                opts['mon addr'] = self.mon_addr

            parser = self.cfg.open()
            write = True

            if not parser.has_section(name):
                parser.add_section(self.name)
                for opt, val in opts.iteritems():
                    parser.set(self.name, opt, val)

                confchanges.append('New section: {0}'.format(name))

                for opt, val in opts.iteritems():
                    confchanges.append('New option: {opt} = {val}'.format(
                        opt=opt, val=val))
            else:
                # a list of (opt, value) tuples
                fopts = parser.items(name)
                add = set(opts.items())
                remove = set(fopts)

                if add != remove:
                    add -= remove
                    remove -= add

                    for opt, val in remove:
                        parser.remove_option(name, opt)

                        confchanges.append('Removed option: {opt} = {val}'
                                           .format(opt=opt, val=val))
                    for opt, val in add:
                        parser.set(name, opt, val)

                        confchanges.append('New option: {opt} = {val}'
                                           .format(opt=opt, val=val))
                else:
                    write = False

            if write:
                self.cfg.write()

            tag = _CephOneLineTag(os.path.join(mon_data, 'active'))
            tag.write('active')

            state = _CephMonState.ACTIVE
        if state == _CephMonState.ACTIVE:
            if daemon.is_running():
                if self._state == _CephMonState.ACTIVE:
                    ret['comment'] = 'MON: mon.{0} is already managed, skip'\
                                     .format(mon_id)
                    return ret

                daemon.restart()
                daemonchanges.append('Restart daemon')
            else:
                # start daemon
                daemon.start()
                daemonchanges.append('Start daemon')

        if datachanges:
            changes[mon_data] = datachanges
        if confchanges:
            changes[self.conf] = confchanges
        if daemonchanges:
            changes[name] = daemonchanges

        return ret

    def unprepare(self):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} unprepared'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []

        mon_id = self.mon_id
        mon_data = self.mon_data

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            # not prepared
            ret['comment'] = 'MON: mon.{0} is not prepared, skip'.format(mon_id)

            return ret

        if self.__old_signature is None:
            # not managed by us
            return _error(ret, 'MON: mon.{0} is not prepared by us, skip'
                          .format(mon_id))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        if self._state > _CephMonState.READY:
            return _error(ret, 'MON: mon.{0} is activated, skip'
                          .format(mon_id))

        shutil.rmtree(mon_data)

        datachanges.append('Clear mon data filesystem')

        changes[mon_data] = datachanges

        return ret

    def deactivate(self):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} deactivated'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        confchanges = []
        daemonchanges = []

        mon_id = self.mon_id
        name = self.name
        mon_data = self.mon_data
        daemon = _CephMonDaemon(mon_id, self.cluster)

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            # not prepared
            ret['comment'] = 'MON: mon.{0} is not prepared, skip'.format(mon_id)

            return ret

        if self._state == _CephMonState.READY:
            # not activated
            ret['comment'] = 'MON: mon.{0} is not activated, skip'.format(mon_id)

            return ret

        if self.__old_signature is None:
            # not managed by us
            return _error(ret, 'MON: mon.{0} is not prepared by us, skip'
                          .format(mon_id))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        if self._state == _CephMonState.ACTIVE:
            if daemon.is_running():
                daemon.stop()

                daemonchanges.append('Stop daemon')

            parser = self.cfg.open()

            if parser.has_section(name):
                fopts = parser.items(name)
                parser.remove_section(name)

                self.cfg.write()

                confchanges.append('Remove section: {0}'.format(name))
                for opt, val in fopts:
                    confchanges.append(
                        'Remove option: {opt} = {val}'.format(opt=opt, val=val)
                    )

            tag = _CephOneLineTag(os.path.join(mon_data, 'active'))
            tag.remove()

        if confchanges:
            changes[self.conf] = confchanges
        if daemonchanges:
            changes[name] = daemonchanges

        return ret

    def unmanage(self):
        ret = {
            'name': self.mon_id,
            'result': True,
            'comment': 'MON: mon.{0} unmanaged'.format(self.mon_id),
            'changes': {}
        }

        changes = ret['changes']
        datachanges = []
        confchanges = []
        daemonchanges = []

        mon_id = self.mon_id
        name = self.name
        mon_data = self.mon_data
        daemon = _CephMonDaemon(mon_id, self.cluster)

        # detect existing MON
        self.init()

        if self._state == _CephMonState.FREE:
            # not prepared
            ret['comment'] = 'MON: mon.{0} is not prepared, skip'.format(mon_id)

            return ret

        if self.__old_signature is None:
            # not managed by us
            return _error(ret, 'MON: mon.{0} is not prepared by us, skip'
                          .format(mon_id))

        if not self.__compare_signature(self.__old_signature):
            # signature mismatch
            nsig = self.__parse_signature(self.__signature())
            osig = self.__parse_signature(self.__old_signature)

            ret['result'] = False
            ret['comment'] = ['MON: mon.{0} is prepared, but arguments changed '
                              'since last preparation, skip'
                              .format(mon_id),
                              {'new config': [], 'old config': []}]
            new = ret['comment'][1]['new config']
            old = ret['comment'][1]['old config']

            new.append('cluster: {0}'.format(nsig['cluster']))
            new.append('fsid: {0}'.format(nsig['fsid']))
            new.append('mon id: {0}'.format(nsig['mon_id']))
            new.append('auth type: {0}'.format(nsig['auth_type']))
            new.append('mon key: {0}'.format(nsig['mon_key']))
            new.append('mon addr: {0}'.format(nsig['mon_addr']))

            old.append('cluster: {0}'.format(osig['cluster']))
            old.append('fsid: {0}'.format(osig['fsid']))
            old.append('mon id: {0}'.format(osig['mon_id']))
            old.append('auth type: {0}'.format(osig['auth_type']))
            old.append('mon key: {0}'.format(osig['mon_key']))
            old.append('mon addr: {0}'.format(osig['mon_addr']))

            return ret

        state = self._state

        if state == _CephMonState.ACTIVE:
            if daemon.is_running():
                daemon.stop()

                daemonchanges.append('Stop daemon')

            parser = self.cfg.open()

            if parser.has_section(name):
                fopts = parser.items(name)
                parser.remove_section(name)

                self.cfg.write()

                confchanges.append('Remove section: {0}'.format(name))
                for opt, val in fopts:
                    confchanges.append(
                        'Remove option: {opt} = {val}'.format(opt=opt, val=val)
                    )

            tag = _CephOneLineTag(os.path.join(mon_data, 'active'))
            tag.remove()

            state = _CephMonState.READY
        if state == _CephMonState.READY:
            shutil.rmtree(mon_data)

            datachanges.append('Clear mon data filesystem')

        if datachanges:
            changes[mon_data] = datachanges
        if confchanges:
            changes[self.conf] = confchanges
        if daemonchanges:
            changes[name] = daemonchanges

        return ret

    def takeover(self):
        pass


def mon_prepare(mon_id='',
                auth_type='none',
                mon_key='',
                mon_addr='',
                cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.prepare()


def mon_activate(mon_id='',
                 auth_type='none',
                 mon_key='',
                 mon_addr='',
                 cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']
    host = __grains__['host']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.activate(host=host)


def mon_manage(mon_id='',
               auth_type='none',
               mon_key='',
               mon_addr='',
               cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']
    host = __grains__['host']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.manage(host=host)


def mon_unprepare(mon_id='',
                  auth_type='none',
                  mon_key='',
                  mon_addr='',
                  cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.unprepare()


def mon_deactivate(mon_id='',
                   auth_type='none',
                   mon_key='',
                   mon_addr='',
                   cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.deactivate()


def mon_unmanage(mon_id='',
                 auth_type='none',
                 mon_key='',
                 mon_addr='',
                 cluster=CEPH_CLUSTER):
    mon_id = mon_id or __grains__['id']

    mon = _CephMon(mon_id, auth_type, mon_key, mon_addr, cluster)

    return mon.unmanage()


def mon_running(mon_id, cluster=CEPH_CLUSTER):
    daemon = _CephMonDaemon(mon_id, cluster)

    return daemon.is_running()


def mon_start(mon_id, cluster=CEPH_CLUSTER):
    daemon = _CephMonDaemon(mon_id, cluster)

    daemon.start()


def mon_stop(mon_id, cluster=CEPH_CLUSTER):
    daemon = _CephMonDaemon(mon_id, cluster)

    daemon.stop()


def mon_restart(mon_id, cluster=CEPH_CLUSTER):
    daemon = _CephMonDaemon(mon_id, cluster)

    daemon.restart()


class _CephIniFile(object):
    '''
    ConfigParser module of python 2.x does not support leading space
    in the ini file, so feed this to ConfigParser
    '''
    def __init__(self, fpath):
        super(_CephIniFile, self).__init__()
        self.fpath = fpath

    def __enter__(self):
        self.fobj = open(self.fpath, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fobj.close()
        return False

    def readline(self):
        line = self.fobj.readline()

        return line.lstrip(' \t')


def gen_key():
    key = os.urandom(16)
    header = struct.pack(
        '<hiih',
        1,                 # le16 type: CEPH_CRYPTO_AES
        int(time.time()),  # le32 created: seconds
        0,                 # le32 created: nanoseconds,
        len(key),          # le16: len(key)
    )
    return base64.b64encode(header + key)


class _CephAuth(object):
    def __init__(self, name, key='', mon_caps='', osd_caps='', mds_caps='',
                 cluster=CEPH_CLUSTER):
        super(_CephAuth, self).__init__()

        (etype, eid) = ('', '')
        if name:
            if '.' not in name:
                raise ValueError(
                    'Invalid name: {0}, must be $type.$id'.format(name)
                )

            (etype, eid) = name.split('.', 1)

            if etype not in ['mon', 'osd', 'mds', 'client']:
                raise ValueError('Invalid entity type: {0}'.format(etype))

        cfg = _CephConf(cluster)

        self.cluster = cfg.cluster
        self.conf = cfg.conf
        self.cfg = cfg
        self.type = etype
        self.id = eid
        self.name = name
        self.key = key
        self.mon_caps = mon_caps
        self.osd_caps = osd_caps
        self.mds_caps = mds_caps

    @classmethod
    def fromtypeid(cls, etype, eid, key, mon_caps='', osd_caps='', mds_caps='',
                   cluster=CEPH_CLUSTER):

        if etype not in ['mon', 'osd', 'mds', 'client']:
            raise ValueError('Invalid entity type: {0}'.format(etype))

        name = '{type}.{id}'.format(type=etype, id=eid)

        return cls(name, key, mon_caps, osd_caps, mds_caps, cluster)

    @classmethod
    def open_keyring(cls, keyring):
        parser = ConfigParser.SafeConfigParser()

        with _CephIniFile(keyring) as fobj:
            parser.readfp(fobj)

        return parser

    @classmethod
    def write_keyring(cls, parser, keyring):
        with open(keyring, 'wb') as fobj:
            parser.write(fobj)

    @classmethod
    def compare_keyring(cls, kr1, kr2):
        parser1 = cls.open_keyring(kr1)
        parser2 = cls.open_keyring(kr2)

        sections1 = parser1.sections()
        sections2 = parser2.sections()

        if set(sections1) != set(sections2):
            return False

        for section in sections1:
            if set(parser1.items(section)) != set(parser2.items(section)):
                return False

        return True

    @classmethod
    def compare_key(cls, name, kr1, kr2):
        parser1 = cls.open_keyring(kr1)
        parser2 = cls.open_keyring(kr2)

        key1 = parser1.get(name, 'key')
        key2 = parser2.get(name, 'key')

        if key1 == key2:
            return True

        return False

    def gen_keyring(self, keyring):
        if not os.path.exists(keyring):
            with open(keyring, 'wb'):
                pass

        cmd = ['ceph-authtool']
        cmd.append(keyring)
        cmd.append('--name {0}'.format(self.name))
        cmd.append('--add-key {0}'.format(self.key))
        if self.mon_caps:
            cmd.append('--cap mon "{0}"'.format(self.mon_caps))
        if self.osd_caps:
            cmd.append('--cap osd "{0}"'.format(self.osd_caps))
        if self.mds_caps:
            cmd.append('--cap mds "{0}"'.format(self.mds_caps))

        _check_run(cmd)

    def auth(self, name, keyring):
        tmpkr = ''
        try:
            (fd, tmpkr) = tempfile.mkstemp(prefix='kr.')
            os.close(fd)

            self.gen_keyring(tmpkr)

            cmd = ['ceph']
            cmd.append('--cluster {0}'.format(self.cluster))
            cmd.append('--conf {0}'.format(self.conf))
            cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
            cmd.append('--name {0}'.format(name))
            cmd.append('--keyring {0}'.format(keyring))
            cmd.append('--in-file {0}'.format(tmpkr))
            cmd.append('auth')
            cmd.append('add')
            cmd.append(self.name)

            _check_run(cmd)
        finally:
            if os.path.exists(tmpkr):
                os.remove(tmpkr)

    def unauth(self, name, keyring):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(name))
        cmd.append('--keyring {0}'.format(keyring))
        cmd.append('auth')
        cmd.append('del')
        cmd.append(self.name)

        _check_run(cmd)

    def export_auth(self, okeyring, name, keyring):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(name))
        cmd.append('--keyring {0}'.format(keyring))
        cmd.append('--out-file {0}'.format(okeyring))
        cmd.append('auth')
        cmd.append('export')
        cmd.append(self.name)

        _check_run(cmd)

    def update_caps(self, name, keyring,
                    mon_caps='', osd_caps='', mds_caps=''):
        caps = []
        if mon_caps:
            caps.append('mon "{0}"'.format(mon_caps))
        if osd_caps:
            caps.append('osd "{0}"'.format(osd_caps))
        if mds_caps:
            caps.append('mds "{0}"'.format(mds_caps))

        if caps:
            cmd = ['ceph']
            cmd.append('--cluster {0}'.format(self.cluster))
            cmd.append('--conf {0}'.format(self.conf))
            cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
            cmd.append('--name {0}'.format(name))
            cmd.append('--keyring {0}'.format(keyring))
            cmd.append('auth')
            cmd.append('caps')
            cmd.append(self.name)
            cmd.extend(caps)

            _check_run(cmd)
        else:
            self.unauth(name, keyring)

            self.mon_caps = mon_caps
            self.osd_caps = osd_caps
            self.mds_caps = mds_caps
            self.auth(name, keyring)

    def is_authed(self, name, keyring):
        cmd = ['ceph']
        cmd.append('--cluster {0}'.format(self.cluster))
        cmd.append('--conf {0}'.format(self.conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(name))
        cmd.append('--keyring {0}'.format(keyring))
        cmd.append('auth')
        cmd.append('get')
        cmd.append(self.name)

        (code, _, stderr) = _run(cmd)

        if code:
            if code == errno.ENOENT:
                return False
            raise RuntimeError(cmd, stderr, code)

        return True

    def auth_by_key(self, name, key):
        # construct an admin entity
        adm = _CephAuth(name, key)

        admkr = ''
        try:
            (fd, admkr) = tempfile.mkstemp(prefix='kr.')
            os.close(fd)

            adm.gen_keyring(admkr)

            self.auth(name, admkr)
        finally:
            if os.path.exists(admkr):
                os.remove(admkr)


def keyring_manage(keyring,
                   entity_name,
                   entity_key,
                   mon_caps='',
                   osd_caps='',
                   mds_caps='',
                   user='root',
                   group='root',
                   mode='600'):
    ret = {
        'name': keyring,
        'result': True,
        'comment': 'Keyring: {0} managed'.format(keyring),
        'changes': {}
    }

    changes = ret['changes']

    if not os.path.isabs(keyring):
        raise ValueError('Keyring: {0} is not an abs path'.format(keyring))

    keyring = os.path.normpath(keyring)
    pdir = os.path.dirname(keyring)
    auth = _CephAuth(entity_name, entity_key, mon_caps, osd_caps, mds_caps)

    dirchanges = []
    krchanges = []

    add = False         # add entity to exist keyring
    update = False      # update entity info

    if not os.path.exists(pdir):
        if os.path.islink(pdir):
            os.remove(pdir)

            dirchanges.append('Remove dangling symbolic link')
        os.makedirs(pdir)

        dirchanges.append('New dir')
    else:
        if os.path.isfile(pdir):
            os.remove(pdir)
            os.makedirs(pdir)
            dirchanges.append('Remove file has the same name as parent dir')
            dirchanges.append('New dir')

        if not os.path.exists(keyring):
            if os.path.islink(keyring):
                os.remove(keyring)

                krchanges.append('Remove dangling symbolic link')
        else:
            if not os.path.isfile(keyring):
                if os.path.islink(keyring):
                    os.remove(keyring)

                    krchanges.append('Not a valid file, remove')
                else:
                    shutil.rmtree(keyring)

                    krchanges.append('A dir is here, remove')
            else:
                parser = _CephAuth.open_keyring(keyring)

                if parser.has_section(entity_name):
                    fcont = parser.items(entity_name)
                    cont = [('key', entity_key)]
                    if mon_caps:
                        cont.append(('caps mon', '"{0}"'.format(mon_caps)))
                    if osd_caps:
                        cont.append(('caps osd', '"{0}"'.format(osd_caps)))
                    if mds_caps:
                        cont.append(('caps mds', '"{0}"'.format(mds_caps)))

                    if set(cont) == set(fcont):
                        ret['comment'] = 'Keyring already managed, skip'
                        return ret

                    update = True
                else:
                    add = True

    # TODO: right?
    if update:
        cmd = ['ceph-authtool']
        cmd.append(keyring)
        cmd.append('--name {0}'.format(entity_name))
        cmd.append('--add-key {0}'.format(entity_key))
        if mon_caps:
            cmd.append('--cap mon "{0}"'.format(mon_caps))
        if osd_caps:
            cmd.append('--cap osd "{0}"'.format(osd_caps))
        if mds_caps:
            cmd.append('--cap mds "{0}"'.format(mds_caps))

        _check_run(cmd)

        krchanges.append('Keyring updated')
    else:
        auth.gen_keyring(keyring)

        if add:
            krchanges.append('Add entity to keyring')
        else:
            krchanges.append('Generate new keyring')

    # TODO: manage keyring file perms

    if dirchanges:
        changes[pdir] = dirchanges
    if krchanges:
        changes[keyring] = krchanges

    return ret


def keyring_unmanage(keyring,
                     name=''):
    ret = {
        'name': keyring,
        'result': True,
        'comment': 'Keyring removed'
        if not name else 'Entity: {name} removed'.format(name=name),
        'changes': {}
    }

    if not os.path.exists(keyring):
        ret['comment'] = 'Keyring does not exist, skip'
        return ret

    if not os.path.isfile(keyring):
        ret['comment'] = 'Not a keyring file, skip'
        return ret

    if not name:
        os.remove(keyring)
        ret['changes'][keyring] = 'Remove keyring file'
        return ret

    parser = _CephAuth.open_keyring(keyring)

    if parser.has_section(name):
        if len(parser.sections()) > 1:
            parser.remove_section(name)
            _CephAuth.write_keyring(parser, keyring)

            ret['changes'][keyring] = 'Entity: {0} removed'.format(name)
            return ret

        os.remove(keyring)
        ret['changes'][keyring] = 'Keyring removed'
        ret['comment'] = 'Entity: {0} is the only one, keyring removed'.format(name)
        return ret

    ret['comment'] = 'Entity: {name} does not exist, skip'.format(name=name)

    return ret


def auth_manage(entity_name,
                entity_key,
                admin_name,
                admin_key,
                mon_caps='',
                osd_caps='',
                mds_caps='',
                cluster=CEPH_CLUSTER):
    ret = {
        'name': entity_name,
        'result': True,
        'comment': 'Entity: {0} authenticated'.format(entity_name),
        'changes': {}
    }

    changes = ret['changes']
    authchanges = []

    admkr = ''
    tmpkr = ''
    ourkr = ''

    try:
        (fd, admkr) = tempfile.mkstemp(prefix='kr.')
        os.close(fd)

        adm = _CephAuth(admin_name, admin_key)
        adm.gen_keyring(admkr)

        (fd, ourkr) = tempfile.mkstemp(prefix='kr.')
        os.close(fd)

        auth = _CephAuth(entity_name, entity_key, mon_caps, osd_caps, mds_caps)
        auth.gen_keyring(ourkr)

        if auth.is_authed(admin_name, admkr):
            (fd, tmpkr) = tempfile.mkstemp(prefix='kr.')
            os.close(fd)

            auth.export_auth(tmpkr, admin_name, admkr)
            if _CephAuth.compare_keyring(tmpkr, ourkr):
                ret['comment'] = 'Entity: {0} already managed, skip'\
                                 .format(entity_name)
                return ret

            if _CephAuth.compare_key(entity_name, tmpkr, ourkr):
                auth.update_caps(admin_name, admkr, mon_caps, osd_caps, mds_caps)
                changes[entity_name] = 'Entity authenticated, update caps'
                return ret

            # key not match
            auth.unauth(admin_name, admkr)
            authchanges.append('Del auth entity')

        auth.auth(admin_name, admkr)
        authchanges.append('New auth entity')
        changes[entity_name] = authchanges
        ret['comment'] = 'New entity: {0} authenticated'.format(entity_name)

        return ret
    finally:
        if os.path.exists(admkr):
            os.remove(admkr)
        if os.path.exists(tmpkr):
            os.remove(tmpkr)
        if os.path.exists(ourkr):
            os.remove(ourkr)


def auth_unmanage(entity_name,
                  admin_name,
                  admin_key,
                  cluster=CEPH_CLUSTER):
    ret = {
        'name': entity_name,
        'result': True,
        'comment': 'Entity: {0} unauthenticated'.format(entity_name),
        'changes': {}
    }

    changes = ret['changes']

    admkr = ''

    try:
        (fd, admkr) = tempfile.mkstemp(prefix='kr.')
        os.close(fd)

        adm = _CephAuth(admin_name, admin_key)
        adm.gen_keyring(admkr)

        auth = _CephAuth(entity_name)

        if auth.is_authed(admin_name, admkr):
            auth.unauth(admin_name, admkr)
            changes[entity_name] = 'Auth entity removed'
            return ret

        ret['comment'] = 'Entity: {0} does not exist, skip'.format(entity_name)

        return ret
    finally:
        if os.path.exists(admkr):
            os.remove(admkr)


def conf_manage(ctx,
                cluster=CEPH_CLUSTER):
    ret = {
        'name': cluster,
        'result': True,
        'comment': 'ceph conf for: {0} managed'.format(cluster),
        'changes': {}
    }

    changes = ret['changes']
    filechanges = []
    cfgchanges = {}

    if ctx is None:
        raise ValueError('Ctx must not be None')
    if not isinstance(ctx, dict):
        raise ValueError('Ctx must be an dict type')

    cfg = _CephConf(cluster)
    conf = cfg.conf

    pdir = os.path.dirname(conf)

    if not os.path.exists(pdir):
        if os.path.islink(pdir):
            os.remove(pdir)

            filechanges.append('Remove dangling parent dir symbolic link')
        os.makedirs(pdir)

        filechanges.append('New parent dir')
    else:
        if os.path.isfile(pdir):
            os.remove(pdir)
            os.makedirs(pdir)
            filechanges.append('Remove file has the same name as parent dir')
            filechanges.append('New parent dir')

        if not os.path.exists(conf):
            if os.path.islink(conf):
                os.remove(conf)

                filechanges.append('Remove dangling symbolic link')
        else:
            if not os.path.isfile(conf):
                if os.path.islink(conf):
                    os.remove(conf)

                    filechanges.append('Not a valid file, remove')
                else:
                    shutil.rmtree(conf)

                    filechanges.append('A dir is here, remove')

    # ok, create a blank file if not exist
    if not os.path.exists(conf):
        with open(conf, 'wb'):
            pass

    parser = cfg.open()

    sections = ctx.keys()
    fsections = parser.sections()

    add = set(sections)
    remove = set(fsections)

    sec_remain = add & remove
    sec_add = add - remove

    # if we remove existing sections then our newly added MON section
    # will be removed
    # sec_remove = remove - add

    # for sec in sec_remove:
    #     fopts = parser.items(sec)
    #
    #     parser.remove_section(sec)
    #
    #     cfgchanges[sec] = []
    #     cfgchanges[sec].append('Remove section: {0}'.format(sec))
    #
    #     for opt, val in fopts:
    #         cfgchanges[sec].append('Remove option: {opt} = {val}'.format(
    #             opt=opt, val=val))

    for sec in sec_add:
        parser.add_section(sec)

        cfgchanges[sec] = []
        cfgchanges[sec].append('New section: {0}'.format(sec))

        opts = ctx[sec].items()

        for opt, val in opts:
            parser.set(sec, opt, val)
            cfgchanges[sec].append('New option: {opt} = {val}'.format(
                opt=opt, val=val))

    for sec in sec_remain:
        # a list of (opt, value) tuples
        opts = ctx[sec].items()
        fopts = parser.items(sec)

        add = set(opts)
        remove = set(fopts)

        if add != remove:
            opts_add = add - remove
            opts_remove = remove - add

            sectionchanges = []

            for opt, val in opts_remove:
                parser.remove_option(sec, opt)

                sectionchanges.append('Remove option: {opt} = {val}'.format(
                    opt=opt, val=val)
                )

            for opt, val in opts_add:
                parser.set(sec, opt, val)

                sectionchanges.append('New option: {opt} = {val}'.format(
                    opt=opt, val=val)
                )

            if sectionchanges:
                cfgchanges[sec] = sectionchanges

    if cfgchanges:
        changes[conf] = cfgchanges
        cfg.write()
    else:
        ret['comment'] = 'ceph conf for: {0} is already managed, skip'.format(cluster)

    return ret
