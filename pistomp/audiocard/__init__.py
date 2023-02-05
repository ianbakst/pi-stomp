from pathlib import Path

from .audiocard import AudioCard
from .iqaudiocodec import IQaudioCodec


__all__ = [
    "AudioCard",
    "Factory",
    "IQaudioCodec",
]

SYSTEM_CARD_FILE = Path("/proc/asound/cards")

class Factory:
    __exists: bool = False

    @staticmethod
    def get_current_card():
        if SYSTEM_CARD_FILE.exists() is False:
            return
        with open(SYSTEM_CARD_FILE, 'r') as f:
            for line in f.readlines():
                strs = line.split()
                if len(strs) > 2 and strs[0] == "0":
                    return strs[1].lstrip("[").rstrip("]:")

    def create(self, cwd: Path) -> AudioCard:
        # get the current card
        card_name = self.get_current_card()
        if card_name == "IQaudIOCODEC":
            card = IQaudioCodec(cwd)
        # elif card_name == "sndrpihifiberry":
        #     card = pistomp.hifiberry.Hifiberry(self.cwd)
        # elif card_name == "audioinjectorpi":
        #     card = pistomp.audioinjector.Audioinjector(self.cwd)
        else:  # Could be explicit here but we need to return some card, so make it the most common option
            card = IQaudioCodec(cwd)
        Factory.__exists = True
        return card
