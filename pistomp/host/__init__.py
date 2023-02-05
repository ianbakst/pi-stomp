from .host import Host
from .mod import Mod
from pistomp.audiocard import AudioCard


__all__ = ["Factory", "Host", "Mod"]


class HostExistsError(Exception):
    pass


class Factory:
    __exists: bool = False

    @staticmethod
    def create(audio_card: AudioCard, home_dir):
        if Factory.__exists:
            raise HostExistsError
        h = Mod(audio_card, home_dir)
        Factory.__exists = True
        return h
