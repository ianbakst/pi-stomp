from .item import Item


"""
class Factory:
    def __init__(self, display):
        self.disp = display

    def create(self, screen_type: Optional[str] = None):
        s_type = ScreenType(screen_type)
        if s_type == ScreenType.SPLASH:
            return Splash(self.disp.width, self.disp.height)
"""