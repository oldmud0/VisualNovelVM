import pygame, re



class SpriteSurface(pygame.sprite.Sprite):

    def __init__(self, path : str):
        super().__init__()
        self._images = dict()
        with open(path) as file:
            for image in re.finditer("^(.+)=(.+)$", file.read(), re.MULTILINE):
                try:
                    self._images[image[1]] = pygame.image.load(image[2])
                except IOError:
                    print("Couldn't load image {0} at path {1}.".format(image[0], image[1]))
        self._anim_name = "default"
        self._alpha = 255
        self.image = self._images[self._anim_name]
        self.rect = self.image.get_rect()

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, alpha):
        if not 0 <= alpha <= 255:
            raise ValueError("Alpha must be within bounds")
        self._alpha = alpha
        self.draw_alpha()

    def draw_alpha(self):
        if self.alpha == 255:
            self.image_alpha = self.image
        else:
            mask = pygame.Surface(self.image.get_size(), flags=pygame.SRCALPHA)
            mask.fill((255, 255, 255, self.alpha))
            self.image_alpha = self.image.copy()
            self.image_alpha.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    @property
    def anim_name(self):
        return self._anim_name

    @anim_name.setter
    def anim_name(self, name):
        self.image = self._images[name]
        self._anim_name = name