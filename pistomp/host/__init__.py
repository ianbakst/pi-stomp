from os import getcwd

from .host import Host
from .mod import Mod
from pistomp.audiocard import AudioCard


__all__ = ["Factory", "Host", "Mod"]

CWD = getcwd()


class HostExistsError(Exception):
    pass


class Factory:
    __exists: bool = False

    @staticmethod
    def create(audio_card: AudioCard):
        if Factory.__exists:
            raise HostExistsError
        h = Mod(audio_card, CWD)
        Factory.__exists = True
        return h
