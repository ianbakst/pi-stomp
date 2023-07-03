from pistomp.screen.item import Item


class InputGainMenuItem(Item):
    def __init__(self):
        self.name = "input gain"
        self.text = "Adjust Input Gain"
        self.action = None
        self.highlightable = True