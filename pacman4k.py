#!/usr/bin/env python3
"""
PAC-MAN ARCADE - COMPLETE 256 LEVELS
=====================================
- All 256 arcade levels with kill screen
- Authentic ghost roll call with beeps & boops
- Progressive difficulty scaling
- Fruit bonuses per level
- No external files - everything generated
"""

import pygame
import math
import random
import numpy as np
from enum import Enum

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=256)

# Constants
WIDTH, HEIGHT = 900, 700
FPS = 60
CELL_SIZE = 16

# Colors
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (33, 33, 222)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PINK = (255, 184, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 184, 82)
GREEN = (0, 255, 0)

class GameState(Enum):
    INTRO = 0
    GHOST_ROLL = 1
    READY = 2
    PLAYING = 3
    DYING = 4
    GAME_OVER = 5
    LEVEL_COMPLETE = 6
    KILL_SCREEN = 7

class SoundGenerator:
    """Generate arcade-style sounds in software"""
    def __init__(self):
        self.sample_rate = 22050
        
    def generate_tone(self, frequency, duration, volume=0.3, wave='sine'):
        """Generate various waveforms"""
        frames = int(duration * self.sample_rate)
        arr = np.zeros(frames)
        
        for i in range(frames):
            t = i / self.sample_rate
            if wave == 'sine':
                arr[i] = volume * math.sin(2 * math.pi * frequency * t)
            elif wave == 'square':
                arr[i] = volume * (1 if math.sin(2 * math.pi * frequency * t) > 0 else -1)
            elif wave == 'triangle':
                arr[i] = volume * (2 * abs(2 * (frequency * t % 1) - 1) - 1)
                
        # Add envelope
        attack = int(0.01 * frames)
        release = int(0.05 * frames)
        for i in range(attack):
            arr[i] *= i / attack
        for i in range(release):
            arr[-(i+1)] *= i / release
            
        arr = (arr * 32767).astype(np.int16)
        arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
        return pygame.sndarray.make_sound(arr)
    
    def generate_sweep(self, start_freq, end_freq, duration, volume=0.3):
        """Generate frequency sweep"""
        frames = int(duration * self.sample_rate)
        arr = np.zeros(frames)
        for i in range(frames):
            t = i / frames
            freq = start_freq * (end_freq / start_freq) ** t
            arr[i] = volume * math.sin(2 * math.pi * freq * i / self.sample_rate)
        arr = (arr * 32767).astype(np.int16)
        arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
        return pygame.sndarray.make_sound(arr)
    
    def generate_chomp(self, base_freq, duration):
        """Generate pac-man chomp sound"""
        frames = int(duration * self.sample_rate)
        arr = np.zeros(frames)
        for i in range(frames):
            t = i / self.sample_rate
            # Modulated square wave
            carrier = 1 if math.sin(2 * math.pi * base_freq * t) > 0 else -1
            modulator = math.sin(2 * math.pi * 20 * t)
            arr[i] = 0.2 * carrier * (0.5 + 0.5 * modulator)
        arr = (arr * 32767).astype(np.int16)
        arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
        return pygame.sndarray.make_sound(arr)
    
    def generate_siren(self, duration):
        """Generate ghost siren sound"""
        frames = int(duration * self.sample_rate)
        arr = np.zeros(frames)
        for i in range(frames):
            t = i / self.sample_rate
            freq = 200 + 100 * math.sin(2 * math.pi * 4 * t)
            arr[i] = 0.15 * math.sin(2 * math.pi * freq * t)
        arr = (arr * 32767).astype(np.int16)
        arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
        return pygame.sndarray.make_sound(arr)

# Create arcade sounds
sound_gen = SoundGenerator()
sounds = {
    # Pac-Man sounds
    'chomp1': sound_gen.generate_chomp(420, 0.1),
    'chomp2': sound_gen.generate_chomp(440, 0.1),
    
    # Ghost sounds
    'siren': sound_gen.generate_siren(0.5),
    'retreat': sound_gen.generate_sweep(800, 400, 0.3, 0.2),
    'eaten': sound_gen.generate_tone(600, 0.3, 0.3, 'square'),
    
    # Power & bonus sounds
    'power': sound_gen.generate_sweep(100, 500, 0.4, 0.3),
    'fruit': sound_gen.generate_sweep(400, 800, 0.2, 0.3),
    'extra_life': sound_gen.generate_sweep(200, 1000, 0.5, 0.3),
    
    # UI sounds
    'intro_beep': sound_gen.generate_tone(262, 0.2, 0.3, 'square'),  # C4
    'ghost_beep1': sound_gen.generate_tone(330, 0.15, 0.3, 'square'), # E4
    'ghost_beep2': sound_gen.generate_tone(392, 0.15, 0.3, 'square'), # G4
    'ghost_beep3': sound_gen.generate_tone(523, 0.15, 0.3, 'square'), # C5
    'ghost_beep4': sound_gen.generate_tone(659, 0.15, 0.3, 'square'), # E5
    
    # Game state sounds
    'ready': sound_gen.generate_sweep(400, 600, 0.3, 0.3),
    'death': sound_gen.generate_sweep(500, 50, 1.0, 0.4),
    'complete': sound_gen.generate_sweep(300, 900, 0.4, 0.3),
    
    # Level 256 glitch sounds
    'glitch1': sound_gen.generate_tone(100, 0.05, 0.5, 'square'),
    'glitch2': sound_gen.generate_tone(37, 0.05, 0.5, 'triangle'),
}

# Arcade-accurate maze
MAZE = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,3,1,1,1,1,2,1,1,1,1,1,2,1,1,2,1,1,1,1,1,2,1,1,1,1,3,1],
    [1,2,1,1,1,1,2,1,1,1,1,1,2,1,1,2,1,1,1,1,1,2,1,1,1,1,2,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,2,1,1,1,1,2,1,1,2,1,1,1,1,1,1,1,1,2,1,1,2,1,1,1,1,2,1],
    [1,2,2,2,2,2,2,1,1,2,2,2,2,1,1,2,2,2,2,1,1,2,2,2,2,2,2,1],
    [1,1,1,1,1,1,2,1,1,1,1,1,0,1,1,0,1,1,1,1,1,2,1,1,1,1,1,1],
    [0,0,0,0,0,1,2,1,1,1,1,1,0,1,1,0,1,1,1,1,1,2,1,0,0,0,0,0],
    [0,0,0,0,0,1,2,1,1,0,0,0,0,0,0,0,0,0,0,1,1,2,1,0,0,0,0,0],
    [0,0,0,0,0,1,2,1,1,0,1,1,1,4,4,1,1,1,0,1,1,2,1,0,0,0,0,0],
    [1,1,1,1,1,1,2,1,1,0,1,0,0,0,0,0,0,1,0,1,1,2,1,1,1,1,1,1],
    [0,0,0,0,0,0,2,0,0,0,1,0,0,0,0,0,0,1,0,0,0,2,0,0,0,0,0,0],
    [1,1,1,1,1,1,2,1,1,0,1,0,0,0,0,0,0,1,0,1,1,2,1,1,1,1,1,1],
    [0,0,0,0,0,1,2,1,1,0,1,1,1,1,1,1,1,1,0,1,1,2,1,0,0,0,0,0],
    [0,0,0,0,0,1,2,1,1,0,0,0,0,5,5,0,0,0,0,1,1,2,1,0,0,0,0,0],
    [0,0,0,0,0,1,2,1,1,0,1,1,1,1,1,1,1,1,0,1,1,2,1,0,0,0,0,0],
    [1,1,1,1,1,1,2,1,1,0,1,1,1,1,1,1,1,1,0,1,1,2,1,1,1,1,1,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,1,1,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,2,1,1,1,1,2,1,1,1,1,1,2,1,1,2,1,1,1,1,1,2,1,1,1,1,2,1],
    [1,3,2,2,1,1,2,2,2,2,2,2,2,0,0,2,2,2,2,2,2,2,1,1,2,2,3,1],
    [1,1,1,2,1,1,2,1,1,2,1,1,1,1,1,1,1,1,2,1,1,2,1,1,2,1,1,1],
    [1,2,2,2,2,2,2,1,1,2,2,2,2,1,1,2,2,2,2,1,1,2,2,2,2,2,2,1],
    [1,2,1,1,1,1,1,1,1,1,1,1,2,1,1,2,1,1,1,1,1,1,1,1,1,1,2,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]

# Fruit bonuses per level (arcade accurate)
FRUITS = [
    (100, "🍒", "Cherry"),      # Level 1
    (300, "🍓", "Strawberry"),   # Level 2
    (500, "🍊", "Orange"),       # Level 3-4
    (500, "🍊", "Orange"),
    (700, "🍎", "Apple"),        # Level 5-6
    (700, "🍎", "Apple"),
    (1000, "🍈", "Melon"),       # Level 7-8
    (1000, "🍈", "Melon"),
    (2000, "🏆", "Galaxian"),    # Level 9-10
    (2000, "🏆", "Galaxian"),
    (3000, "🔔", "Bell"),        # Level 11-12
    (3000, "🔔", "Bell"),
    (5000, "🔑", "Key"),         # Level 13+
]

def get_level_config(level):
    """Get speed and timing config for each level"""
    if level == 256:
        # Kill screen - everything breaks
        return {
            'pac_speed': 0.05,
            'ghost_speed': 0.3,
            'frightened_time': 10,
            'fruit': (0, "💀", "KILL SCREEN")
        }
    
    # Progressive difficulty
    level = min(level, 21)  # Cap at level 21 difficulty
    
    configs = {
        1: {'pac_speed': 0.15, 'ghost_speed': 0.12, 'frightened_time': 360},
        2: {'pac_speed': 0.16, 'ghost_speed': 0.13, 'frightened_time': 300},
        3: {'pac_speed': 0.16, 'ghost_speed': 0.14, 'frightened_time': 240},
        4: {'pac_speed': 0.17, 'ghost_speed': 0.15, 'frightened_time': 180},
        5: {'pac_speed': 0.17, 'ghost_speed': 0.16, 'frightened_time': 150},
        6: {'pac_speed': 0.18, 'ghost_speed': 0.17, 'frightened_time': 120},
        7: {'pac_speed': 0.18, 'ghost_speed': 0.18, 'frightened_time': 120},
        8: {'pac_speed': 0.19, 'ghost_speed': 0.19, 'frightened_time': 90},
        9: {'pac_speed': 0.19, 'ghost_speed': 0.20, 'frightened_time': 60},
        10: {'pac_speed': 0.20, 'ghost_speed': 0.21, 'frightened_time': 60},
        11: {'pac_speed': 0.20, 'ghost_speed': 0.22, 'frightened_time': 50},
        12: {'pac_speed': 0.21, 'ghost_speed': 0.23, 'frightened_time': 40},
        13: {'pac_speed': 0.21, 'ghost_speed': 0.24, 'frightened_time': 40},
        14: {'pac_speed': 0.22, 'ghost_speed': 0.25, 'frightened_time': 30},
        15: {'pac_speed': 0.22, 'ghost_speed': 0.26, 'frightened_time': 30},
        16: {'pac_speed': 0.23, 'ghost_speed': 0.27, 'frightened_time': 20},
        17: {'pac_speed': 0.23, 'ghost_speed': 0.28, 'frightened_time': 20},
        18: {'pac_speed': 0.24, 'ghost_speed': 0.29, 'frightened_time': 10},
        19: {'pac_speed': 0.24, 'ghost_speed': 0.30, 'frightened_time': 10},
        20: {'pac_speed': 0.25, 'ghost_speed': 0.31, 'frightened_time': 5},
        21: {'pac_speed': 0.25, 'ghost_speed': 0.32, 'frightened_time': 0},
    }
    
    config = configs.get(level, configs[21])
    
    # Add fruit info
    if level <= 13:
        config['fruit'] = FRUITS[level - 1]
    else:
        config['fruit'] = FRUITS[-1]
    
    return config

class Ghost:
    def __init__(self, x, y, color, name, nickname, personality):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.nickname = nickname
        self.personality = personality
        self.dx = 0
        self.dy = 0
        self.speed = 0.12
        self.move_accumulator = 0
        self.frightened = False
        self.eaten = False
        self.mode_timer = 0
        self.scatter_mode = False
        
    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.dx = 0
        self.dy = -1
        self.frightened = False
        self.eaten = False
        self.move_accumulator = 0
        
    def update(self, maze, pacman, level_config):
        # Update speed based on level
        if self.eaten:
            self.speed = 0.5  # Return to base quickly
        elif self.frightened:
            self.speed = level_config['ghost_speed'] * 0.5
        else:
            self.speed = level_config['ghost_speed']
        
        # Accumulate movement
        self.move_accumulator += self.speed
        
        while self.move_accumulator >= 1.0:
            self.move_accumulator -= 1.0
            
            if self.eaten:
                # Return to ghost house
                if abs(self.x - 14) < 1 and abs(self.y - 11) < 1:
                    self.eaten = False
                    self.frightened = False
                else:
                    self.return_to_base(maze)
            elif self.frightened:
                self.frightened_move(maze)
            else:
                self.ai_move(maze, pacman)
            
            # Execute move
            if self.can_move(self.x + self.dx, self.y + self.dy, maze):
                self.x += self.dx
                self.y += self.dy
    
    def return_to_base(self, maze):
        """Navigate back to ghost house"""
        target_x, target_y = 14, 11
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        best_dir = (0, 0)
        min_dist = float('inf')
        
        for dx, dy in directions:
            nx, ny = self.x + dx, self.y + dy
            if self.can_move(nx, ny, maze):
                dist = abs(nx - target_x) + abs(ny - target_y)
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)
        
        self.dx, self.dy = best_dir
    
    def frightened_move(self, maze):
        """Random movement when frightened"""
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        # Don't reverse direction
        opposite = (-self.dx, -self.dy)
        directions = [d for d in directions if d != opposite]
        
        random.shuffle(directions)
        for dx, dy in directions:
            if self.can_move(self.x + dx, self.y + dy, maze):
                self.dx, self.dy = dx, dy
                break
    
    def ai_move(self, maze, pacman):
        """Personality-based AI movement"""
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        # Don't reverse (except at intersections)
        opposite = (-self.dx, -self.dy)
        valid_dirs = []
        for d in directions:
            if d != opposite and self.can_move(self.x + d[0], self.y + d[1], maze):
                valid_dirs.append(d)
        
        if not valid_dirs:
            valid_dirs = [opposite]
        
        best_dir = valid_dirs[0]
        
        if self.personality == "chaser":
            # Blinky - direct pursuit
            min_dist = float('inf')
            for dx, dy in valid_dirs:
                nx, ny = self.x + dx, self.y + dy
                dist = (nx - pacman.x) ** 2 + (ny - pacman.y) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)
        
        elif self.personality == "ambusher":
            # Pinky - target 4 tiles ahead
            target_x = pacman.x + pacman.dx * 4
            target_y = pacman.y + pacman.dy * 4
            min_dist = float('inf')
            for dx, dy in valid_dirs:
                nx, ny = self.x + dx, self.y + dy
                dist = (nx - target_x) ** 2 + (ny - target_y) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)
        
        elif self.personality == "fickle":
            # Inky - complex targeting
            blinky_x, blinky_y = pacman.x, pacman.y  # Simplified
            pivot_x = pacman.x + pacman.dx * 2
            pivot_y = pacman.y + pacman.dy * 2
            target_x = pivot_x + (pivot_x - blinky_x)
            target_y = pivot_y + (pivot_y - blinky_y)
            
            min_dist = float('inf')
            for dx, dy in valid_dirs:
                nx, ny = self.x + dx, self.y + dy
                dist = (nx - target_x) ** 2 + (ny - target_y) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)
        
        else:  # "pokey"
            # Clyde - chase when far, scatter when close
            dist_to_pac = math.sqrt((self.x - pacman.x) ** 2 + (self.y - pacman.y) ** 2)
            
            if dist_to_pac > 8:
                # Chase
                min_dist = float('inf')
                for dx, dy in valid_dirs:
                    nx, ny = self.x + dx, self.y + dy
                    dist = (nx - pacman.x) ** 2 + (ny - pacman.y) ** 2
                    if dist < min_dist:
                        min_dist = dist
                        best_dir = (dx, dy)
            else:
                # Scatter to corner
                target_x, target_y = 0, 25
                min_dist = float('inf')
                for dx, dy in valid_dirs:
                    nx, ny = self.x + dx, self.y + dy
                    dist = (nx - target_x) ** 2 + (ny - target_y) ** 2
                    if dist < min_dist:
                        min_dist = dist
                        best_dir = (dx, dy)
        
        self.dx, self.dy = best_dir
    
    def can_move(self, x, y, maze):
        if x < 0 or x >= len(maze[0]) or y < 0 or y >= len(maze):
            return False
        cell = maze[int(y)][int(x)]
        return cell != 1
    
    def draw(self, screen, offset_x, offset_y):
        px = offset_x + self.x * CELL_SIZE + CELL_SIZE // 2
        py = offset_y + self.y * CELL_SIZE + CELL_SIZE // 2
        
        if self.eaten:
            # Just eyes returning to base
            pygame.draw.circle(screen, WHITE, (px - 3, py - 2), 3)
            pygame.draw.circle(screen, WHITE, (px + 3, py - 2), 3)
            pygame.draw.circle(screen, BLUE, (px - 3, py - 2), 1)
            pygame.draw.circle(screen, BLUE, (px + 3, py - 2), 1)
        else:
            color = BLUE if self.frightened else self.color
            
            # Body
            pygame.draw.circle(screen, color, (px, py), CELL_SIZE // 2 - 1)
            pygame.draw.rect(screen, color, 
                            (px - CELL_SIZE // 2 + 1, py, CELL_SIZE - 2, CELL_SIZE // 2))
            
            # Wavy bottom
            wave_offset = int(pygame.time.get_ticks() / 100) % 4
            for i in range(4):
                x = px - CELL_SIZE // 2 + 2 + i * 4
                y = py + CELL_SIZE // 2 + (wave_offset + i) % 2
                pygame.draw.circle(screen, color, (x, y), 2)
            
            if not self.frightened:
                # Normal eyes
                pygame.draw.circle(screen, WHITE, (px - 3, py - 2), 3)
                pygame.draw.circle(screen, WHITE, (px + 3, py - 2), 3)
                
                # Pupils look at Pac-Man
                dx = 1 if self.dx > 0 else -1 if self.dx < 0 else 0
                dy = 1 if self.dy > 0 else -1 if self.dy < 0 else 0
                pygame.draw.circle(screen, BLUE, (px - 3 + dx, py - 2 + dy), 1)
                pygame.draw.circle(screen, BLUE, (px + 3 + dx, py - 2 + dy), 1)
            else:
                # Frightened face
                if pygame.time.get_ticks() % 200 < 100:
                    pygame.draw.rect(screen, WHITE, (px - 4, py - 1, 2, 2))
                    pygame.draw.rect(screen, WHITE, (px + 2, py - 1, 2, 2))
                    # Wavy mouth
                    for i in range(5):
                        x = px - 4 + i * 2
                        y = py + 3 + (i % 2)
                        pygame.draw.circle(screen, WHITE, (x, y), 1)

class PacMan:
    def __init__(self):
        self.x = 14
        self.y = 20
        self.dx = 0
        self.dy = 0
        self.next_dx = 0
        self.next_dy = 0
        self.speed = 0.15
        self.move_accumulator = 0
        self.anim_counter = 0
        self.mouth_angle = 0
        self.chomp_sound = True
        
    def update(self, maze, level_config):
        # Update speed based on level
        self.speed = level_config['pac_speed']
        
        # Accumulate movement
        self.move_accumulator += self.speed
        
        while self.move_accumulator >= 1.0:
            self.move_accumulator -= 1.0
            
            # Try to turn
            if self.can_move(self.x + self.next_dx, self.y + self.next_dy, maze):
                self.dx = self.next_dx
                self.dy = self.next_dy
            
            # Move if possible
            if self.can_move(self.x + self.dx, self.y + self.dy, maze):
                old_x, old_y = self.x, self.y
                self.x += self.dx
                self.y += self.dy
                
                # Play chomp sound
                if (old_x != self.x or old_y != self.y) and (self.dx != 0 or self.dy != 0):
                    if self.chomp_sound:
                        sounds['chomp1'].play()
                    else:
                        sounds['chomp2'].play()
                    self.chomp_sound = not self.chomp_sound
        
        # Animate mouth
        self.anim_counter += 1
        self.mouth_angle = 45 * abs(math.sin(self.anim_counter * 0.2))
    
    def can_move(self, x, y, maze):
        if x < 0 or x >= len(maze[0]) or y < 0 or y >= len(maze):
            return False
        return maze[int(y)][int(x)] != 1
    
    def draw(self, screen, offset_x, offset_y):
        px = offset_x + self.x * CELL_SIZE + CELL_SIZE // 2
        py = offset_y + self.y * CELL_SIZE + CELL_SIZE // 2
        
        # Body
        pygame.draw.circle(screen, YELLOW, (px, py), CELL_SIZE // 2 - 1)
        
        # Mouth
        if self.mouth_angle > 5:
            angle_offset = 0
            if self.dx > 0: angle_offset = 0
            elif self.dx < 0: angle_offset = 180
            elif self.dy < 0: angle_offset = 90
            elif self.dy > 0: angle_offset = 270
            
            points = [(px, py)]
            for angle in range(-int(self.mouth_angle), int(self.mouth_angle) + 1, 5):
                a = math.radians(angle_offset + angle)
                x = px + math.cos(a) * (CELL_SIZE // 2)
                y = py - math.sin(a) * (CELL_SIZE // 2)
                points.append((x, y))
            
            if len(points) > 2:
                pygame.draw.polygon(screen, BLACK, points)

def draw_intro(screen, timer):
    """Arcade-style intro sequence"""
    screen.fill(BLACK)
    
    big_font = pygame.font.Font(None, 72)
    med_font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 24)
    
    # Play intro beeps at specific times
    if timer == 30:
        sounds['intro_beep'].play()
    elif timer == 60:
        sounds['intro_beep'].play()
    elif timer == 90:
        sounds['ready'].play()
    
    # BANDAI NAMCO
    if timer > 30:
        color1 = RED if timer % 20 < 10 else (128, 0, 0)
        bandai_text = big_font.render("BANDAI", True, color1)
        screen.blit(bandai_text, (WIDTH // 2 - 120, HEIGHT // 2 - 150))
    
    if timer > 60:
        color2 = YELLOW if timer % 20 < 10 else (128, 128, 0)
        namco_text = big_font.render("NAMCO", True, color2)
        screen.blit(namco_text, (WIDTH // 2 - 110, HEIGHT // 2 - 80))
    
    if timer > 90:
        presents_text = med_font.render("PRESENTS", True, WHITE)
        screen.blit(presents_text, (WIDTH // 2 - 100, HEIGHT // 2))
    
    if timer > 120:
        # PAC-MAN logo with animated Pac-Man
        pac_text = big_font.render("PAC-MAN", True, YELLOW)
        screen.blit(pac_text, (WIDTH // 2 - 120, HEIGHT // 2 + 80))
        
        # Animated Pac-Man
        px = WIDTH // 2 - 200
        py = HEIGHT // 2 + 100
        angle = 45 * abs(math.sin(timer * 0.1))
        pygame.draw.circle(screen, YELLOW, (px, py), 25)
        
        points = [(px, py)]
        for a in range(-int(angle), int(angle) + 1, 5):
            x = px + math.cos(math.radians(a)) * 25
            y = py - math.sin(math.radians(a)) * 25
            points.append((x, y))
        if len(points) > 2:
            pygame.draw.polygon(screen, BLACK, points)
        
        # Dots being eaten
        for i in range(3):
            if timer > 130 + i * 10:
                dot_x = px + 50 + i * 30
                if timer < 140 + i * 10:
                    pygame.draw.circle(screen, WHITE, (dot_x, py), 4)
    
    if timer > 160:
        credit_text = small_font.render("© 1980 NAMCO LTD.", True, WHITE)
        screen.blit(credit_text, (WIDTH // 2 - 100, HEIGHT - 60))
        
        arcade_text = small_font.render("ARCADE PERFECT - 256 LEVELS", True, CYAN)
        screen.blit(arcade_text, (WIDTH // 2 - 140, HEIGHT - 30))

def draw_ghost_roll(screen, ghosts, timer):
    """Arcade-style ghost introduction with beeps"""
    screen.fill(BLACK)
    
    title_font = pygame.font.Font(None, 48)
    name_font = pygame.font.Font(None, 36)
    desc_font = pygame.font.Font(None, 24)
    
    # Play beep for each ghost
    if timer == 30:
        sounds['ghost_beep1'].play()
    elif timer == 90:
        sounds['ghost_beep2'].play()
    elif timer == 150:
        sounds['ghost_beep3'].play()
    elif timer == 210:
        sounds['ghost_beep4'].play()
    
    # Title
    title_text = "CHARACTER / NICKNAME"
    if timer % 30 < 15:
        title = title_font.render(title_text, True, WHITE)
        screen.blit(title, (WIDTH // 2 - 200, 50))
    
    # Show ghosts with timing
    ghost_data = [
        (30, ghosts[0], "-SHADOW", "\"BLINKY\""),
        (90, ghosts[1], "-SPEEDY", "\"PINKY\""),
        (150, ghosts[2], "-BASHFUL", "\"INKY\""),
        (210, ghosts[3], "-POKEY", "\"CLYDE\"")
    ]
    
    y_offset = 150
    for start_time, ghost, name_suffix, nickname in ghost_data:
        if timer > start_time:
            # Draw ghost sprite
            px = WIDTH // 2 - 150
            py = y_offset
            
            # Animated ghost
            wave = int(timer / 5) % 4
            pygame.draw.circle(screen, ghost.color, (px, py), 12)
            pygame.draw.rect(screen, ghost.color, (px - 12, py, 24, 12))
            for i in range(4):
                x = px - 9 + i * 6
                y = py + 12 + (wave + i) % 2
                pygame.draw.circle(screen, ghost.color, (x, y), 3)
            
            # Eyes
            pygame.draw.circle(screen, WHITE, (px - 4, py - 2), 3)
            pygame.draw.circle(screen, WHITE, (px + 4, py - 2), 3)
            pygame.draw.circle(screen, BLUE, (px - 4, py - 2), 1)
            pygame.draw.circle(screen, BLUE, (px + 4, py - 2), 1)
            
            # Name
            name_text = name_font.render(name_suffix, True, ghost.color)
            screen.blit(name_text, (px + 40, py - 10))
            
            # Nickname
            nick_text = desc_font.render(nickname, True, WHITE)
            screen.blit(nick_text, (px + 200, py - 5))
            
            y_offset += 80
    
    # Show Pac-Man
    if timer > 270:
        px = WIDTH // 2 - 150
        py = y_offset + 20
        
        # Animated Pac-Man
        angle = 45 * abs(math.sin(timer * 0.1))
        pygame.draw.circle(screen, YELLOW, (px, py), 12)
        points = [(px, py)]
        for a in range(-int(angle), int(angle) + 1, 5):
            x = px + math.cos(math.radians(a)) * 12
            y = py - math.sin(math.radians(a)) * 12
            points.append((x, y))
        if len(points) > 2:
            pygame.draw.polygon(screen, BLACK, points)
        
        name_text = name_font.render("-PAC-MAN", True, YELLOW)
        screen.blit(name_text, (px + 40, py - 10))
    
    # Show pellet values
    if timer > 330:
        y = HEIGHT - 120
        
        # Pellet
        pygame.draw.circle(screen, WHITE, (WIDTH // 2 - 100, y), 3)
        text = desc_font.render("10 PTS", True, WHITE)
        screen.blit(text, (WIDTH // 2 - 60, y - 10))
        
        # Power pellet
        pygame.draw.circle(screen, WHITE, (WIDTH // 2 - 100, y + 30), 6)
        text = desc_font.render("50 PTS", True, WHITE)
        screen.blit(text, (WIDTH // 2 - 60, y + 20))
    
    if timer > 390:
        start_text = name_font.render("PRESS SPACE TO START", True, YELLOW)
        x = WIDTH // 2 - 150
        if timer % 30 < 15:
            screen.blit(start_text, (x, HEIGHT - 40))

def draw_kill_screen(screen, maze, offset_x, offset_y):
    """Draw the famous level 256 kill screen glitch"""
    # Draw half normal maze, half corrupted
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            px = offset_x + x * CELL_SIZE
            py = offset_y + y * CELL_SIZE
            
            if x < 14:  # Left half normal
                if cell == 1:
                    pygame.draw.rect(screen, BLUE, (px, py, CELL_SIZE, CELL_SIZE))
                elif cell == 2:
                    pygame.draw.circle(screen, WHITE, 
                                     (px + CELL_SIZE // 2, py + CELL_SIZE // 2), 2)
            else:  # Right half glitched
                # Random garbage
                if random.random() > 0.3:
                    color = random.choice([RED, BLUE, YELLOW, PINK, CYAN, ORANGE, WHITE, GREEN])
                    if random.random() > 0.5:
                        pygame.draw.rect(screen, color, 
                                       (px + random.randint(-2, 2), 
                                        py + random.randint(-2, 2), 
                                        CELL_SIZE, CELL_SIZE))
                    else:
                        char = random.choice(['2', '5', '6', '0', '/', '\\', '|', '-', '#'])
                        font = pygame.font.Font(None, CELL_SIZE)
                        text = font.render(char, True, color)
                        screen.blit(text, (px, py))
    
    # Glitch sounds
    if random.random() > 0.95:
        random.choice([sounds['glitch1'], sounds['glitch2']]).play()

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PAC-MAN ARCADE - 256 LEVELS")
    clock = pygame.time.Clock()
    
    # Fonts
    font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 20)
    big_font = pygame.font.Font(None, 48)
    
    # Game objects
    pacman = PacMan()
    ghosts = [
        Ghost(13, 11, RED, "BLINKY", "Shadow", "chaser"),
        Ghost(14, 11, PINK, "PINKY", "Speedy", "ambusher"),
        Ghost(13, 12, CYAN, "INKY", "Bashful", "fickle"),
        Ghost(14, 12, ORANGE, "CLYDE", "Pokey", "pokey")
    ]
    
    # Game state
    state = GameState.INTRO
    score = 0
    high_score = 0
    lives = 3
    level = 1
    dots_eaten = 0
    power_timer = 0
    intro_timer = 0
    death_timer = 0
    level_complete_timer = 0
    ghost_score = 200
    fruit_timer = 0
    fruit_active = False
    
    # Create maze copy
    maze = [row[:] for row in MAZE]
    
    # Calculate offsets
    maze_width = len(maze[0]) * CELL_SIZE
    maze_height = len(maze) * CELL_SIZE
    offset_x = (WIDTH - maze_width) // 2
    offset_y = (HEIGHT - maze_height) // 2 + 30
    
    running = True
    while running:
        dt = clock.tick(FPS)
        level_config = get_level_config(level)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif state == GameState.GHOST_ROLL and event.key == pygame.K_SPACE:
                    state = GameState.READY
                    intro_timer = 0
                    sounds['ready'].play()
                elif state == GameState.PLAYING:
                    if event.key == pygame.K_LEFT:
                        pacman.next_dx = -1
                        pacman.next_dy = 0
                    elif event.key == pygame.K_RIGHT:
                        pacman.next_dx = 1
                        pacman.next_dy = 0
                    elif event.key == pygame.K_UP:
                        pacman.next_dx = 0
                        pacman.next_dy = -1
                    elif event.key == pygame.K_DOWN:
                        pacman.next_dx = 0
                        pacman.next_dy = 1
        
        # State updates
        if state == GameState.INTRO:
            intro_timer += 1
            if intro_timer > 200:
                state = GameState.GHOST_ROLL
                intro_timer = 0
        
        elif state == GameState.GHOST_ROLL:
            intro_timer += 1
        
        elif state == GameState.READY:
            intro_timer += 1
            if intro_timer > 120:
                state = GameState.PLAYING
                if level != 256:
                    sounds['siren'].play()
        
        elif state == GameState.PLAYING:
            if level == 256:
                state = GameState.KILL_SCREEN
            else:
                # Update game
                pacman.update(maze, level_config)
                
                for ghost in ghosts:
                    ghost.update(maze, pacman, level_config)
                
                # Power pellet timer
                if power_timer > 0:
                    power_timer -= 1
                    if power_timer == 0:
                        for ghost in ghosts:
                            ghost.frightened = False
                        ghost_score = 200
                
                # Fruit timer
                if dots_eaten == 70 or dots_eaten == 170:
                    if not fruit_active:
                        fruit_active = True
                        fruit_timer = 600
                
                if fruit_active:
                    fruit_timer -= 1
                    if fruit_timer <= 0:
                        fruit_active = False
                
                # Check pellet eating
                x, y = int(pacman.x), int(pacman.y)
                if 0 <= y < len(maze) and 0 <= x < len(maze[0]):
                    if maze[y][x] == 2:  # Pellet
                        maze[y][x] = 0
                        score += 10
                        dots_eaten += 1
                    elif maze[y][x] == 3:  # Power pellet
                        maze[y][x] = 0
                        score += 50
                        power_timer = level_config['frightened_time']
                        sounds['power'].play()
                        ghost_score = 200
                        for ghost in ghosts:
                            if not ghost.eaten:
                                ghost.frightened = True
                    elif maze[y][x] == 5 and fruit_active:  # Fruit
                        score += level_config['fruit'][0]
                        sounds['fruit'].play()
                        fruit_active = False
                
                # Check ghost collision
                for ghost in ghosts:
                    if abs(ghost.x - pacman.x) < 0.5 and abs(ghost.y - pacman.y) < 0.5:
                        if ghost.frightened:
                            score += ghost_score
                            ghost_score *= 2
                            ghost.eaten = True
                            ghost.frightened = False
                            sounds['eaten'].play()
                        elif not ghost.eaten:
                            state = GameState.DYING
                            death_timer = 0
                            sounds['death'].play()
                
                # Check level complete
                pellets_left = sum(row.count(2) + row.count(3) for row in maze)
                if pellets_left == 0:
                    state = GameState.LEVEL_COMPLETE
                    level_complete_timer = 0
                    sounds['complete'].play()
                
                # Update high score
                if score > high_score:
                    high_score = score
                
                # Extra life at 10000
                if score // 10000 > (score - 10) // 10000:
                    lives += 1
                    sounds['extra_life'].play()
        
        elif state == GameState.DYING:
            death_timer += 1
            if death_timer > 120:
                lives -= 1
                if lives <= 0:
                    state = GameState.GAME_OVER
                    intro_timer = 0
                else:
                    # Reset positions
                    pacman.x = 14
                    pacman.y = 20
                    pacman.dx = 0
                    pacman.dy = 0
                    for ghost in ghosts:
                        ghost.reset()
                    state = GameState.READY
                    intro_timer = 0
        
        elif state == GameState.LEVEL_COMPLETE:
            level_complete_timer += 1
            if level_complete_timer > 180:
                level += 1
                if level > 256:
                    level = 1
                maze = [row[:] for row in MAZE]
                dots_eaten = 0
                fruit_active = False
                pacman.x = 14
                pacman.y = 20
                pacman.dx = 0
                pacman.dy = 0
                for ghost in ghosts:
                    ghost.reset()
                state = GameState.READY
                intro_timer = 0
        
        elif state == GameState.GAME_OVER:
            intro_timer += 1
            if intro_timer > 300:
                # Reset game
                level = 1
                score = 0
                lives = 3
                dots_eaten = 0
                maze = [row[:] for row in MAZE]
                pacman = PacMan()
                for ghost in ghosts:
                    ghost.reset()
                state = GameState.INTRO
                intro_timer = 0
        
        # Drawing
        screen.fill(BLACK)
        
        if state == GameState.INTRO:
            draw_intro(screen, intro_timer)
        
        elif state == GameState.GHOST_ROLL:
            draw_ghost_roll(screen, ghosts, intro_timer)
        
        else:
            # Draw maze
            if state == GameState.KILL_SCREEN:
                draw_kill_screen(screen, maze, offset_x, offset_y)
            else:
                for y, row in enumerate(maze):
                    for x, cell in enumerate(row):
                        px = offset_x + x * CELL_SIZE
                        py = offset_y + y * CELL_SIZE
                        
                        if cell == 1:  # Wall
                            pygame.draw.rect(screen, BLUE, (px, py, CELL_SIZE, CELL_SIZE))
                            pygame.draw.rect(screen, BLACK, (px, py, CELL_SIZE, CELL_SIZE), 1)
                        elif cell == 2:  # Pellet
                            pygame.draw.circle(screen, WHITE, 
                                             (px + CELL_SIZE // 2, py + CELL_SIZE // 2), 2)
                        elif cell == 3:  # Power pellet
                            if intro_timer % 20 < 10:
                                pygame.draw.circle(screen, WHITE, 
                                                 (px + CELL_SIZE // 2, py + CELL_SIZE // 2), 6)
                        elif cell == 4:  # Ghost door
                            pygame.draw.line(screen, PINK, 
                                           (px, py + CELL_SIZE // 2),
                                           (px + CELL_SIZE, py + CELL_SIZE // 2), 2)
                        elif cell == 5 and fruit_active:  # Fruit
                            fruit_char = level_config['fruit'][1]
                            fruit_font = pygame.font.Font(None, CELL_SIZE)
                            fruit_text = fruit_font.render(fruit_char, True, YELLOW)
                            screen.blit(fruit_text, (px, py))
            
            # Draw entities
            if state in [GameState.PLAYING, GameState.READY]:
                pacman.draw(screen, offset_x, offset_y)
                for ghost in ghosts:
                    ghost.draw(screen, offset_x, offset_y)
            
            # UI
            score_text = font.render(f"SCORE", True, WHITE)
            screen.blit(score_text, (50, 10))
            score_num = font.render(f"{score:07d}", True, WHITE)
            screen.blit(score_num, (50, 35))
            
            high_text = font.render(f"HIGH SCORE", True, WHITE)
            screen.blit(high_text, (WIDTH // 2 - 60, 10))
            high_num = font.render(f"{high_score:07d}", True, WHITE)
            screen.blit(high_num, (WIDTH // 2 - 50, 35))
            
            # Level indicator
            level_text = font.render(f"LEVEL {level}", True, WHITE)
            screen.blit(level_text, (WIDTH - 150, 10))
            
            # Show fruit icons for this level
            if level <= 7:
                for i in range(min(level, 7)):
                    fruit_data = FRUITS[min(i, len(FRUITS)-1)]
                    x = WIDTH - 140 + i * 20
                    fruit_font = pygame.font.Font(None, 20)
                    fruit_icon = fruit_font.render(fruit_data[1], True, YELLOW)
                    screen.blit(fruit_icon, (x, 40))
            
            # Lives
            for i in range(lives - 1):
                px = 50 + i * 30
                py = HEIGHT - 30
                pygame.draw.circle(screen, YELLOW, (px, py), 8)
                points = [(px, py)]
                for angle in range(-30, 31, 5):
                    a = math.radians(angle)
                    x = px + math.cos(a) * 8
                    y = py - math.sin(a) * 8
                    points.append((x, y))
                if len(points) > 2:
                    pygame.draw.polygon(screen, BLACK, points)
            
            # State-specific text
            if state == GameState.READY:
                ready_text = big_font.render("READY!", True, YELLOW)
                screen.blit(ready_text, (WIDTH // 2 - 70, HEIGHT // 2))
            
            elif state == GameState.GAME_OVER:
                go_text = big_font.render("GAME OVER", True, RED)
                screen.blit(go_text, (WIDTH // 2 - 120, HEIGHT // 2))
            
            elif state == GameState.KILL_SCREEN:
                kill_text = big_font.render("LEVEL 256 - KILL SCREEN!", True, RED)
                screen.blit(kill_text, (WIDTH // 2 - 200, 100))
                
                glitch_text = font.render("GAME BROKEN - CONGRATULATIONS!", True, 
                                        random.choice([RED, YELLOW, CYAN, PINK]))
                screen.blit(glitch_text, (WIDTH // 2 - 180, 150))
            
            # FPS
            fps_text = small_font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
            screen.blit(fps_text, (WIDTH - 70, HEIGHT - 25))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
