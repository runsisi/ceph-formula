# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import threading
import subprocess


class TimedProcTimeoutError(Exception):
    pass


class CommandExecutionError(Exception):
    pass


# Taken from saltstack with minor changes
class TimedProc(object):
    '''
    Create a TimedProc object, calls subprocess.Popen with passed args and **kwargs
    '''
    def __init__(self, args, **kwargs):

        self.command = args
        self.stdin = kwargs.pop('stdin', None)
        if self.stdin is not None:
            # Translate a newline submitted as '\n' on the CLI to an actual
            # newline character.
            self.stdin = self.stdin.replace('\\n', '\n')
            kwargs['stdin'] = subprocess.PIPE
        self.stdout = None
        self.stderr = None
        self.with_communicate = kwargs.pop('with_communicate', True)

        self.process = subprocess.Popen(args, **kwargs)

    def wait(self, timeout=None):
        '''
        wait for subprocess to terminate and return subprocess' return code.
        If timeout is reached, throw TimedProcTimeoutError
        '''
        def receive():
            if self.with_communicate:
                (self.stdout, self.stderr) = self.process.communicate(input=self.stdin)
            else:
                self.process.wait()
                (self.stdout, self.stderr) = (None, None)

        if timeout:
            if not isinstance(timeout, (int, float)):
                raise TimedProcTimeoutError('Error: timeout must be a number')
            rt = threading.Thread(target=receive)
            rt.start()
            rt.join(timeout)
            if rt.isAlive():
                # Subprocess cleanup (best effort)
                self.process.kill()

                def terminate():
                    if rt.isAlive():
                        self.process.terminate()
                threading.Timer(10, terminate).start()
                raise TimedProcTimeoutError(
                    '{0} : Timed out after {1} seconds'.format(
                        self.command,
                        str(timeout),
                    )
                )
        else:
            receive()
        return self.process.returncode


def run(cmd, timeout=None):
    if not isinstance(cmd, list):
        raise ValueError('cmd must be a list')

    ret = {}

    kwargs = {
        'stdin': None,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'with_communicate': True
    }

    try:
        proc = TimedProc(cmd, **kwargs)
    except (OSError, IOError) as exc:
        raise CommandExecutionError(
            'Unable to run command {0!r} with the context {1!r}, reason: {2}'
            .format(cmd, kwargs, exc)
        )

    try:
        proc.wait(timeout)
    except TimedProcTimeoutError as exc:
        ret['pid'] = proc.process.pid
        # ok return code for timeouts?
        ret['retcode'] = 255
        ret['stdout'] = ''
        ret['stderr'] = str(exc)

        return ret

    out, err = proc.stdout, proc.stderr

    if out is not None:
        out = out.rstrip()
    if err is not None:
        err = err.rstrip()

    ret['pid'] = proc.process.pid
    ret['retcode'] = proc.process.returncode
    ret['stdout'] = out
    ret['stderr'] = err

    return ret


def check_run(cmd, timeout=None):
    data = run(cmd, timeout)

    (retcode, stdout, stderr) = data['retcode'], data['stdout'], data['stderr']

    out = '\n' + stdout if stdout else ''
    err = '\n' + stderr if stderr else ''

    if retcode:
        raise CommandExecutionError('Execute command {0!r} exit with code: {1}\n'
                                    'Output:{2}\nDetails:{3}'
                                    .format(cmd, retcode, out, err))
