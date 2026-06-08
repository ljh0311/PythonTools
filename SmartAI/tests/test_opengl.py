#!/usr/bin/env python3
"""
Simple OpenGL test to verify rendering works
"""

import pygame
import sys
from OpenGL.GL import *
from OpenGL.GLU import *

def main():
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("OpenGL Test")
    
    # Initialize OpenGL
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.2, 0.3, 0.3, 1.0)  # Dark cyan background
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Set up projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, 800/600, 0.1, 100.0)
        
        # Set up modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)
        
        # Render a simple colored cube
        glBegin(GL_QUADS)
        
        # Front face (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-1, -1, 1)
        glVertex3f(1, -1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(-1, 1, 1)
        
        # Back face (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, 1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, -1, -1)
        
        # Top face (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-1, 1, -1)
        glVertex3f(-1, 1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, 1, -1)
        
        # Bottom face (yellow)
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(1, -1, -1)
        glVertex3f(1, -1, 1)
        glVertex3f(-1, -1, 1)
        
        # Right face (magenta)
        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(1, -1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, -1, 1)
        
        # Left face (cyan)
        glColor3f(0.0, 1.0, 1.0)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, -1, 1)
        glVertex3f(-1, 1, 1)
        glVertex3f(-1, 1, -1)
        
        glEnd()
        
        # Update display
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 