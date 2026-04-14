'''
Author: Fox Carnachan
Date: Mar 2026
Purpose: A simple game where two players move around and shoot each other with potato cannons
'''

"""
Controls:
  Player1 Red:   WASD move Q/E rotate cannon SPACE fire
  Player2 Blue:  Arrows move N/M rotate cannon ENTER fire
  R = restart   ESC = quit
"""

import pygame
import math
import sys
import os
from pygame.math import Vector2

# this is where i set all the variables for thing like player speed map size damage ect
MAP_W, MAP_H  = 256, 256
SCALE         = 3
WIN_W         = MAP_W * SCALE
WIN_H         = MAP_H * SCALE + 60

PLAYER_SPEED  = 0.9
CANNON_SPEED  = 2.5
BULLET_SPEED  = 5.0
FIRE_COOLDOWN = 45
EXPLOSION_FRAMES = 50
EXPLOSION_RADIUS = 38
EXPLOSION_DAMAGE = 35
PLAYER_RADIUS    = 8
WALL_THRESH = 40
FPS = 60


#defined funtions have pretty self explanatory names eg. _make_map
def ensure_assets():
    os.makedirs("assets", exist_ok=True)

    def _player_sheet(path, body_col, cannon_col):
        if os.path.exists(path):
            return
        surf = pygame.Surface((64, 32), pygame.SRCALPHA)
        pygame.draw.circle(surf, body_col,        (16, 16), 13)
        pygame.draw.circle(surf, (255,255,255),   (16, 16), 13, 2)
        pygame.draw.circle(surf, (255,255,255),   (20, 11), 3)
        pygame.draw.circle(surf, (0,0,0),         (21, 11), 1)
        pygame.draw.rect(surf, (60,60,60),  (42, 11, 12, 10))
        pygame.draw.rect(surf, cannon_col,  (50, 13, 14,  6))
        pygame.save(surf, path)

    def _make_map(path):
        if os.path.exists(path):
            return
        surf = pygame.Surface((256, 256))
        surf.fill((130, 130, 130))
        for rect in [
            (0,0,256,8),(0,248,256,8),(0,0,8,256),(248,0,8,256),
            (40,40,8,80),(40,40,80,8),(128,40,8,80),(170,40,50,8),
            (40,170,80,8),(40,128,8,50),(170,128,50,8),(128,170,8,50),
            (96,96,64,8),(96,96,8,64),(152,96,8,64),(96,152,64,8),
        ]:
            pygame.draw.rect(surf, (0,0,0), rect)
        pygame.save(surf, path)

    def _make_potato(path):
        if os.path.exists(path):
            return
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (180,140,80), (0,1,8,6))
        pygame.draw.ellipse(surf, (120,80,40),  (0,1,8,6), 1)
        pygame.save(surf, path)

    def _make_explosion(path):
        if os.path.exists(path):
            return
        surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        for i, col in enumerate([(255,220,0),(255,140,0),(255,60,0),(200,0,0)]):
            pygame.draw.circle(surf, col, (24,24), 24 - i*4)
        for a in range(0, 360, 30):
            ex = int(24 + 22*math.cos(math.radians(a)))
            ey = int(24 + 22*math.sin(math.radians(a)))
            pygame.draw.circle(surf, (255,255,100), (ex,ey), 3)
        pygame.save(surf, path)
    #pulling all the assets (sprites and sprite sheets from the assets folder)
    _player_sheet("assets/RedPlayer.png",  (200,40,40),  (160,30,30))
    _player_sheet("assets/BluePlayer.png", (40,80,200),  (30,60,160))
    _make_map("assets/PotatoCannonMap.png")
    _make_potato("assets/Potato.png")
    _make_explosion("assets/Explosion.png")

'''
this following code handles the map collisions by essentially scanning the map sprite and making 
black pixels 'solid' (players collide against) again the defined functons are self explanatory'''
class CollisionMap:
    def __init__(self, surface):
        self._w = surface.get_width()
        self._h = surface.get_height()
        self._grid = bytearray(self._w * self._h)
        for y in range(self._h):
            for x in range(self._w):
                r, g, b, *_ = surface.get_at((x, y))
                brightness = (int(r) + int(g) + int(b)) // 3
                self._grid[y * self._w + x] = 1 if brightness < WALL_THRESH else 0

    def is_wall(self, x, y):
        ix, iy = int(x), int(y)
        if ix < 0 or iy < 0 or ix >= self._w or iy >= self._h:
            return True
        return bool(self._grid[iy * self._w + ix])

    def find_open_spot(self, hint_x, hint_y, radius):
        #Scan outward from hint until it finds a spot with no wall probes
        r2 = radius * 0.707
        probes = [(radius,0),(-radius,0),(0,radius),(0,-radius),
                  (r2,r2),(-r2,r2),(r2,-r2),(-r2,-r2)]
        for dist in range(0, 60, 2):
            for dy in range(-dist, dist+1, max(1,dist)):
                for dx in range(-dist, dist+1, max(1,dist)):
                    cx = hint_x + dx
                    cy = hint_y + dy
                    if all(not self.is_wall(cx+ox, cy+oy) for ox,oy in probes):
                        return cx, cy
        return hint_x, hint_y  # fallback


class Player(pygame.sprite.Sprite):

    def __init__(self, sheet_path, pos, controls, col_map, player_id):
        super().__init__()
        sheet = pygame.image.load(sheet_path).convert_alpha()
        raw_body   = sheet.subsurface((0,  0, 32, 32))
        raw_cannon = sheet.subsurface((32, 0, 32, 32))
        sw = int(32 * 1.5)
        self.body_img   = pygame.transform.scale(raw_body,   (sw, sw))
        self.cannon_img = pygame.transform.rotate(pygame.transform.scale(raw_cannon, (sw, sw)), -90)

        # find a guaranteed open spawn using the collision map itself
        sx, sy = col_map.find_open_spot(pos[0], pos[1], PLAYER_RADIUS)
        self.pos        = Vector2(sx, sy)
        self.cannon_ang = 0.0
        self.controls   = controls
        self.col_map    = col_map
        self.player_id  = player_id
        self.hp         = 100
        self.fire_timer = 0
        self.alive      = True

        self.image = pygame.Surface((sw, sw), pygame.SRCALPHA)
        self.rect  = self.image.get_rect()

        '''this builds a hitbox where the players coloured pixels are
         so that the hitbox is more accurate to what the player sees '''
        self._pixel_offsets = []
        half = sw // 2
        for py in range(0, sw, 2):
            for px in range(0, sw, 2):
                _, _, _, a = self.body_img.get_at((px, py))
                if a > 64:
                    #convert screen pixel offset to map space offset
                    ox = (px - half) / SCALE
                    oy = (py - half) / SCALE
                    self._pixel_offsets.append((ox, oy))
    
    def update(self, keys, bullets, other_player):
        if not self.alive:
            return
        c = self.controls

        dx = dy = 0
        if keys[c["up"]]:    dy -= 1
        if keys[c["down"]]:  dy += 1
        if keys[c["left"]]:  dx -= 1
        if keys[c["right"]]: dx += 1

        if dx or dy:
            move = Vector2(dx, dy).normalize() * PLAYER_SPEED
            nx = self.pos.x + move.x
            ny = self.pos.y + move.y
            if not self._wall_collides(nx, self.pos.y):
                self.pos.x = nx
            if not self._wall_collides(self.pos.x, ny):
                self.pos.y = ny

        # Player-vs-player: push apart if overlapping
        if other_player and other_player.alive:
            diff = self.pos - other_player.pos
            dist = diff.length()
            min_dist = PLAYER_RADIUS * 2
            if 0 < dist < min_dist:
                push = diff.normalize() * ((min_dist - dist) / 2)
                nx = self.pos.x + push.x
                ny = self.pos.y + push.y
                if not self._wall_collides(nx, self.pos.y):
                    self.pos.x = nx
                if not self._wall_collides(self.pos.x, ny):
                    self.pos.y = ny

        if keys[c["cannon_left"]]:
            self.cannon_ang = (self.cannon_ang - CANNON_SPEED) % 360
        if keys[c["cannon_right"]]:
            self.cannon_ang = (self.cannon_ang + CANNON_SPEED) % 360

        # Fire: simple cooldown gate works on hold too
        self.fire_timer = max(0, self.fire_timer - 1)
        if keys[c["fire"]] and self.fire_timer == 0:
            angle_rad = math.radians(self.cannon_ang)
            tip = self.pos + Vector2(math.cos(angle_rad), math.sin(angle_rad)) * 10
            bullets.add(Potato(tip, angle_rad, self.col_map, self.player_id))
            self.fire_timer = FIRE_COOLDOWN

        self.rect.center = (int(self.pos.x * SCALE), int(self.pos.y * SCALE))

    def _wall_collides(self, x, y):
        r  = PLAYER_RADIUS
        r2 = r * 0.707
        for ox, oy in [(r,0),(-r,0),(0,r),(0,-r),
                       (r2,r2),(-r2,r2),(r2,-r2),(-r2,-r2)]:
            if self.col_map.is_wall(x + ox, y + oy):
                return True
        return False

    def bullet_hits(self, bpos):
        """Pixel-perfect check: is bullet map-pos inside any opaque body pixel?"""
        for ox, oy in self._pixel_offsets:
            if abs(bpos.x - (self.pos.x + ox)) < 1.0 and abs(bpos.y - (self.pos.y + oy)) < 1.0:
                return True
        return False

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        cx = int(self.pos.x * SCALE)
        cy = int(self.pos.y * SCALE)
        br = self.body_img.get_rect(center=(cx, cy))
        surface.blit(self.body_img, br)
        cannon_rot = pygame.transform.rotate(self.cannon_img, -self.cannon_ang)
        cr = cannon_rot.get_rect(center=(cx, cy))
        surface.blit(cannon_rot, cr)


class Potato(pygame.sprite.Sprite):
    def __init__(self, pos, angle_rad, col_map, owner_id):
        super().__init__()
        raw = pygame.image.load("assets/Potato.png").convert_alpha()
        base = pygame.transform.scale(raw, (16, 16))
        self.image    = pygame.transform.rotate(base, -math.degrees(angle_rad))
        self.rect     = self.image.get_rect()
        self.pos      = Vector2(pos)
        self.vel      = Vector2(math.cos(angle_rad), math.sin(angle_rad)) * BULLET_SPEED
        self.col_map  = col_map
        self.owner_id = owner_id
        self.dead     = False

    def update(self, *args, **kwargs):
        if self.dead:
            self.kill(); return
        self.pos += self.vel
        self.rect.center = (int(self.pos.x * SCALE), int(self.pos.y * SCALE))

    def hit_wall(self):
        """True if potato centre or any edge probe is in a wall or out of bounds."""
        x, y = self.pos.x, self.pos.y
        if not (0 <= x <= MAP_W and 0 <= y <= MAP_H):
            return True
        # Check centre plus 4 edge points so large sprite can't clip through thin walls
        for ox, oy in [(0,0),(4,0),(-4,0),(0,4),(0,-4)]:
            if self.col_map.is_wall(x + ox, y + oy):
                return True
        return False

    def explode(self):
        self.dead = True; self.kill()


class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        raw = pygame.image.load("assets/Explosion.png").convert_alpha()
        sr = EXPLOSION_RADIUS * SCALE
        self._orig = pygame.transform.scale(raw, (sr * 2, sr * 2))
        self.image = self._orig.copy()
        self.rect  = self.image.get_rect(center=(int(pos.x*SCALE), int(pos.y*SCALE)))
        self.pos   = Vector2(pos)
        self.timer = EXPLOSION_FRAMES

    def update(self, *args, **kwargs):
        self.timer -= 1
        img = self._orig.copy()
        img.set_alpha(max(0, int(255 * self.timer / EXPLOSION_FRAMES)))
        self.image = img
        if self.timer <= 0:
            self.kill()


def draw_hud(surface, p1, p2, font):
    hy = WIN_H - 60
    pygame.draw.rect(surface, (18,18,18), (0, hy, WIN_W, 60))
    pygame.draw.line(surface, (70,70,70), (0, hy), (WIN_W, hy), 2)
    pygame.draw.rect(surface, (100,20,20), (20, hy+8, 160, 18))
    pygame.draw.rect(surface, (240,70,70), (20, hy+8, int(160*max(p1.hp,0)/100), 18))
    surface.blit(font.render(f"{p1.name}  {p1.hp}/100", True, (255,255,255)), (20, hy+30))
    bx2 = WIN_W - 180
    pygame.draw.rect(surface, (20,40,120), (bx2, hy+8, 160, 18))
    w2 = int(160 * max(p2.hp,0) / 100)
    pygame.draw.rect(surface, (60,100,230), (bx2 + 160 - w2, hy+8, w2, 18))
    surface.blit(font.render(f"{p2.name}  {p2.hp}/100", True, (255,255,255)), (bx2, hy+30))
    tip = font.render(
        "P1: WASD | Q/E cannon | SPACE fire      P2: Arrows | N/M cannon | ENTER fire",
        True, (110,110,110))
    surface.blit(tip, tip.get_rect(center=(WIN_W//2, hy+42)))


def draw_game_over(surface, winner, font_big, font_small, p1_name="Player 1", p2_name="Player 2"):
    overlay = pygame.Surface((WIN_W, WIN_H - 60), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))
    if winner == 0:
        msg, col = "Draw!", (255,215,0)
    elif winner == 1:
        msg, col = f"{p1_name} Wins!", (230,60,60)
    else:
        msg, col = f"{p2_name} Wins!", (60,100,230)
    txt = font_big.render(msg, True, col)
    surface.blit(txt, txt.get_rect(center=(WIN_W//2, WIN_H//2 - 40)))
    sub = font_small.render("R = restart   ESC = quit", True, (200,200,200))
    surface.blit(sub, sub.get_rect(center=(WIN_W//2, WIN_H//2 + 20)))



def start_screen(screen, clock):
    """Show name-entry screen. Returns (p1_name, p2_name)."""
    font_title  = pygame.font.SysFont("consolas", 48, bold=True)
    font_label  = pygame.font.SysFont("consolas", 22, bold=True)
    font_input  = pygame.font.SysFont("consolas", 26)
    font_hint   = pygame.font.SysFont("consolas", 14)

    names   = ["Player 1", "Player 2"]
    active  = None   # which box is focused: 0, 1, or None
    colors  = [(200, 40,  40),  (40,  80, 200)]
    box_rects = [
        pygame.Rect(WIN_W // 2 - 180, WIN_H // 2 - 40, 360, 44),
        pygame.Rect(WIN_W // 2 - 180, WIN_H // 2 + 60, 360, 44),
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); import sys; sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); import sys; sys.exit()
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # Move focus to next box or start game
                    if active == 0:
                        active = 1
                    else:
                        return names[0] or "Player 1", names[1] or "Player 2"
                if event.key == pygame.K_TAB:
                    active = 1 if active == 0 else 0
                if active is not None:
                    if event.key == pygame.K_BACKSPACE:
                        names[active] = names[active][:-1]
                    elif event.unicode.isprintable() and len(names[active]) < 16:
                        names[active] += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                active = None
                for i, rect in enumerate(box_rects):
                    if rect.collidepoint(event.pos):
                        active = i
                        break

        # ── draw ────────────────────────────────────────────────────────────
        screen.fill((15, 15, 20))

        # Title
        title = font_title.render("POTATO CANNON", True, (230, 180, 40))
        screen.blit(title, title.get_rect(center=(WIN_W // 2, WIN_H // 2 - 160)))
        sub = font_hint.render("2-Player Top-Down Artillery", True, (130, 130, 130))
        screen.blit(sub, sub.get_rect(center=(WIN_W // 2, WIN_H // 2 - 110)))

        labels = ["RED PLAYER NAME", "BLUE PLAYER NAME"]
        for i, (rect, col, label) in enumerate(zip(box_rects, colors, labels)):
            # Label above box
            lbl = font_label.render(label, True, col)
            screen.blit(lbl, (rect.x, rect.y - 28))

            # Box background
            border_col = (255, 255, 255) if active == i else (80, 80, 80)
            pygame.draw.rect(screen, (30, 30, 35), rect, border_radius=6)
            pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)

            # Text inside box
            display = names[i]
            if active == i and (pygame.time.get_ticks() // 500) % 2 == 0:
                display += "|"   # blinking cursor
            txt = font_input.render(display, True, (240, 240, 240))
            screen.blit(txt, (rect.x + 10, rect.y + 9))

        # Start hint
        hint = font_hint.render("Click a box to select  |  ENTER to confirm  |  TAB to switch", True, (90, 90, 90))
        screen.blit(hint, hint.get_rect(center=(WIN_W // 2, WIN_H // 2 + 140)))

        start_btn = pygame.Rect(WIN_W // 2 - 100, WIN_H // 2 + 170, 200, 44)
        pygame.draw.rect(screen, (50, 130, 50), start_btn, border_radius=8)
        pygame.draw.rect(screen, (100, 220, 100), start_btn, 2, border_radius=8)
        btn_txt = font_label.render("START GAME", True, (255, 255, 255))
        screen.blit(btn_txt, btn_txt.get_rect(center=start_btn.center))

        # Start button click
        if pygame.mouse.get_pressed()[0]:
            if start_btn.collidepoint(pygame.mouse.get_pos()):
                return names[0] or "Player 1", names[1] or "Player 2"

        pygame.display.flip()
        clock.tick(60)

def make_players(col_map, name1="Player 1", name2="Player 2"):
    c1 = dict(up=pygame.K_w, down=pygame.K_s, left=pygame.K_a, right=pygame.K_d,
              cannon_left=pygame.K_q, cannon_right=pygame.K_e, fire=pygame.K_SPACE)
    c2 = dict(up=pygame.K_UP, down=pygame.K_DOWN, left=pygame.K_LEFT, right=pygame.K_RIGHT,
              cannon_left=pygame.K_n, cannon_right=pygame.K_m, fire=pygame.K_RETURN)
    p1 = Player("assets/RedPlayer.png",  (20, 20),   c1, col_map, player_id=1)
    p2 = Player("assets/BluePlayer.png", (236, 236), c2, col_map, player_id=2)
    p1.name = name1
    p2.name = name2
    return p1, p2


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Potato Cannon - 2 Player")
    clock = pygame.time.Clock()

    ensure_assets()
    font_small = pygame.font.SysFont("consolas", 13)
    font_big   = pygame.font.SysFont("consolas", 52, bold=True)

    print("Building collision map...")
    raw_map  = pygame.image.load("assets/PotatoCannonMap.png").convert()
    col_map  = CollisionMap(raw_map)
    map_surf = pygame.transform.scale(raw_map, (MAP_W*SCALE, MAP_H*SCALE))
    print("Ready!")

    def new_game():
        p1, p2 = make_players(col_map)
        bullets    = pygame.sprite.Group()
        explosions = pygame.sprite.Group()
        return p1, p2, bullets, explosions

    p1_name, p2_name = start_screen(screen, clock)

    def new_game_named():
        p1, p2 = make_players(col_map, p1_name, p2_name)
        bullets    = pygame.sprite.Group()
        explosions = pygame.sprite.Group()
        return p1, p2, bullets, explosions

    p1, p2, bullets, explosions = new_game_named()
    game_over = False
    winner    = None

    while True:
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    p1, p2, bullets, explosions = new_game_named()
                    game_over = False; winner = None

        if not game_over:
            p1.update(keys, bullets, p2)
            p2.update(keys, bullets, p1)
            bullets.update()
            explosions.update()

            for bullet in list(bullets):
                if bullet.dead:
                    continue
                # Wall collision — explode on impact
                if bullet.hit_wall():
                    exp = Explosion(bullet.pos)
                    explosions.add(exp)
                    bullet.explode()
                    continue
                # Player collision — explode on the player
                for player in (p1, p2):
                    if not player.alive or bullet.owner_id == player.player_id:
                        continue
                    if player.bullet_hits(bullet.pos):
                        exp = Explosion(player.pos)
                        explosions.add(exp)
                        player.take_damage(EXPLOSION_DAMAGE)
                        bullet.explode()
                        break

            for exp in explosions:
                if exp.timer == EXPLOSION_FRAMES - 1:
                    for player in (p1, p2):
                        if player.alive and player.pos.distance_to(exp.pos) <= EXPLOSION_RADIUS:
                            player.take_damage(EXPLOSION_DAMAGE // 3)

            if not p1.alive and not p2.alive:
                game_over, winner = True, 0
            elif not p1.alive:
                game_over, winner = True, 2
            elif not p2.alive:
                game_over, winner = True, 1

        screen.blit(map_surf, (0, 0))
        explosions.draw(screen)
        bullets.draw(screen)
        p1.draw(screen)
        p2.draw(screen)
        draw_hud(screen, p1, p2, font_small)
        if game_over:
            draw_game_over(screen, winner, font_big, font_small, p1.name, p2.name)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run()