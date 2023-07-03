from pistomp.screen.item import Item


class SystemInfoMenuItem(Item):
    def __init__(self):
        self.name = "info"
        self.text = "System Info"
        self.action = None
        self.highlightable = True