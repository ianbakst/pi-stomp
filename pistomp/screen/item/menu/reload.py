from pistomp.screen.item import Item


class ReloadMenuItem(Item):
    def __init__(self):
        self.name = "reload"
        self.text = "Reload Pedalboards"
        self.action = None
        self.highlightable = True
