from pistomp.screen.item import Item


class RebootMenuItem(Item):
    def __init__(self):
        self.name = "Reboot"
        self.text = "System Reboot"
        self.action = None
        self.highlightable = True