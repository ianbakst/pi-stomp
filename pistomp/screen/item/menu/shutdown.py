from pistomp.screen.item import Item


class ShutdownMenuItem(Item):
    def __init__(self):
        self.name = "shutdown"
        self.text = "System Shutdown"
        self.action = None
        self.highlightable = True