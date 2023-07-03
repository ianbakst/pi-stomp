from pistomp.screen.item import Item


class BackMenuItem(Item):
    def __init__(self):
        self.name = "back"
        self.text = "<- Back to Main Screen"
        self.action = None
        self.highlightable = True
