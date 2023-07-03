from pistomp.screen.item import Item


class HeadphoneVolumeMenuItem(Item):
    def __init__(self):
        self.name = "headphone vol"
        self.text = "Adjust Headphone Volume"
        self.action = None
        self.highlightable = True