from pistomp.screen.item import Item


class SaveMenuItem(Item):
    def __init__(self):
        self.name = "save"
        self.text = "Save Current PedalBoard"
        self.action = None
        self.highlightable = True