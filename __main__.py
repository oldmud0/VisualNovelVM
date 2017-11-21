import pygame
from vm import Runtime


WINDOW_SIZE = (800, 600)

class GraphicalDemo:

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        self.window = pygame.display.set_mode(WINDOW_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF)

        pygame.display.set_caption("Visual Novel VM Runtime Demo")

        self.clock = pygame.time.Clock()

        self.runtime = Runtime(self.window)
        self.running = False

    def poll_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.stop()
            elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if event.key == pygame.K_ESCAPE:
                    self.stop()

    def run(self):
        self.running = True
        self.runtime.start()
        self.loop()

    def loop(self):
        while self.running:
            self.poll_events()
            delta = self.clock.tick(60)
            pygame.display.flip()
        pygame.quit()

    def stop(self):
        """Halts the runtime and exits."""
        self.running = False
        self.runtime.reset()

if __name__ == "__main__":
    GraphicalDemo().run()