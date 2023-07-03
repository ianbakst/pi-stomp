from pistomp.screen.item import Item


class RestartSoundMenuItem(Item):
    def __init__(self):
        self.name = "restart sound"
        self.text = "Restart Sound Engine"
        self.action = None
        self.highlightable = True