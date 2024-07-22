################################################################################
## Play Sound

import pygame

def play(filepath):
    """
    Play audio file.
    """
    pygame.mixer.init()
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
