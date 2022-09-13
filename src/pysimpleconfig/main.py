import os
import os.path
import sys
import psutil
import json

from typing import Union

SuccessFailureType = bool
Success:SuccessFailureType = True
Failure:SuccessFailureType = False

class LogInterface:
    def warn(self, *args, **kwargs):
        print(*args, **kwargs)

log = LogInterface()


def dumpRecursiveDict(dictObj:dict, path:Union[tuple,list]):
    pathList = list(path)
    if len(pathList) == 0:
        return dictObj
    elif len(pathList) == 1:
        return dictObj[pathList[-1]]
    else:
        newDict = dictObj[pathList.pop(0)]
        return dumpRecursiveDict(newDict, pathList)


class PlatformException(BaseException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def prefix() -> str:
    ''' Configure path variables for this app
    '''
    config_dir:Union[str,None] = None

    __platform__ = sys.platform
    if __platform__ == 'win32':
        HOME = os.environ.get('HOMEPATH')
        assert HOME is not None
        config_dir = os.path.join(HOME, r'AppData\Roaming')

    elif __platform__ == 'linux':
        # TODO: try getting XDG_CONFIG
        HOME = os.environ.get('HOME')
        HOME = os.environ.get('HOME')
        assert HOME is not None
        config_dir = os.path.join(HOME, '.config')

    else:
        raise PlatformException('Only win32 and linux is supported for now')

    return config_dir


class SimpleConfig:
    def __is_locked_by_another_living_process(self) -> bool:
        if not os.path.isfile(self.lockfile):
            f'''{self.lockfile} did not exist'''
            return False

        with open(self.lockfile, 'r') as lf:
            try:
                lockfilepid = lf.readlines()[0]
            except BaseException as e:
                log.warn(f'{e.__class__.__name__}: {e}')
                return True
            if lockfilepid == self.pid:
                return False
            print(f'self.pid:{self.pid}\nlockfilepid:{lockfilepid}')
            print(f'file was:{self.lockfile}')
        return True

    def __lock(self) -> SuccessFailureType:
        if os.path.isfile(self.lockfile):
            log.warn(f'{self.lockfile} already exist')
            return Failure
        try:
            with open(self.lockfile, 'x') as lf:
                lf.writelines([self.pid])
                return Success
        except BaseException as e:
            log.warn(f'{e.__class__.__name__}: {e}')
        log.warn('something is failing')
        return Failure

    def __unlock(self) -> SuccessFailureType:
        if self.__is_locked_by_another_living_process():
            log.warn(f'another process is locking file')
            return Failure
        try:
            os.remove(self.lockfile)
            return Success
        except BaseException as e:
            log.warn(f'{e.__class__.__name__}: {e}')
        return Failure

    def read(self) -> SuccessFailureType:
        '''Reads file into self.config'''
        log.warn('not implemented')
        return Failure

    def write(self) -> SuccessFailureType:
        '''Writes file from self.config'''
        log.warn('not implemented')
        return Failure

    def pull(self) -> SuccessFailureType:
        if self.__is_locked_by_another_living_process():
            print('is locked by another proc')
            return Failure
        if self.__lock() == Success:
            return self.read()
        else:
            log.warn('locking failed')
            return Failure

    def push(self) -> SuccessFailureType:
        result = Failure
        if not self.__is_locked_by_another_living_process():
            result = self.write()
            self.__unlock()
        return result

    def __init__(
        self,
        name:str,
        prefix=prefix,
    ):
        self.config:dict = dict({})
        self.prefix = prefix()
        self.config_dir = os.path.join(self.prefix, name)
        os.makedirs(self.config_dir, exist_ok=True)

        # PID for this app's process
        self.pid = str(psutil.Process().pid)
        self.lockfile = os.path.join(self.config_dir, 'pysimpleconfig.lock')

    def __getitem__(self, path):
        self.pull()
        error = None
        try:
            data = dumpRecursiveDict(self.config, path)
        except KeyError as e:
            data = e
            error = e
        self.push()

        if error is not None:
            raise KeyError(path)

        return data

    def __setitem__(self, path, value):
        pathList = list(path)
        key = pathList.pop(-1)

        self.pull()

        for i in range(len(pathList)+1):
            _path = [pathList[j] for j in range(i)]
            try:
                _ = dumpRecursiveDict(self.config, _path)
            except KeyError:
                _key = _path.pop(-1)
                branch = dumpRecursiveDict(self.config, _path)
                branch[_key] = dict({})

        branch = dumpRecursiveDict(self.config, pathList)
        branch[key] = value

        self.push()


class SimpleJsonSingleConfig(SimpleConfig):
    def read(self):
        try:
            with open(os.path.join(self.config_dir, self.config_filename)) as cf:
                self.config = json.load(cf)
            return Success
        except BaseException as e:
            log.warn(f'{e.__class__.__name__}: {e}')
        return Failure

    def write(self):
        try:
            with open(os.path.join(self.config_dir, self.config_filename), 'w') as cf:
                json.dump(self.config, cf, indent=2, ensure_ascii=False)
            return Success
        except BaseException as e:
            log.warn(f'{e.__class__.__name__}: {e}')
        return Failure

    def __init__(self, name:str, config_filename:str, *args, **kwargs):
        self.config_filename = config_filename
        super().__init__(name, *args, **kwargs)

