from .item import Item


class SplashItem(Item):
    def __init__(self):
        self.name = "splash"
        self.text = "<- Back to Main Screen"
        self.action = None
        self.highlightable = True
