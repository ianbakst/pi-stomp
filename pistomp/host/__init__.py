from os import getcwd

from .host import Host
from .mod import Mod
from pistomp.audiocard import AudioCard
from pistomp.hardware import Hardware
from pistomp.lcd import LCD


__all__ = ["Factory", "Host", "Mod"]


class HostExistsError(Exception):
    pass


class Factory:
    __exists: bool = False

    @staticmethod
    def create(audio_card: AudioCard, hardware: Hardware, lcd: LCD) -> Host:
        if Factory.__exists:
            raise HostExistsError
        h = Mod(audio_card, hardware=hardware, lcd=lcd)
        Factory.__exists = True
        return h
