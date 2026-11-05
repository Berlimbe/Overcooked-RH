#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HR Overdrive: Fábrica em Caos  (versão Tkinter)
===============================================
Jogo de ação/gerenciamento em tempo real com humor corporativo e de RH.
Usa SOMENTE `tkinter` e `random` (bibliotecas padrão). Todos os gráficos são
desenhados proceduralmente no Canvas, sem imagens ou arquivos externos.

Execução:   python hr_overdrive_tk.py

Controles:
    W A S D / Setas ... mover o Analista de RH
    E / ESPAÇO ........ pegar item na estação / entregar ao operário / descartar
    P ................. pausar
    ESC ............... voltar ao menu
"""

import random
import tkinter as tk

# ----------------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------------
W, H = 1000, 700            # tamanho da janela
HUD_H = 70                  # altura do painel superior
TICK_MS = 16                # intervalo do game loop (~60 FPS)
SHIFT_SECONDS = 120         # duração do turno
WIN_CLIMATE = 50            # clima mínimo para vencer
ANGRY_PENALTY = 8           # queda de clima quando um operário vai embora
SERVE_BONUS = 2             # recuperação de clima por atendimento
MAX_WAITING = 8             # postos de espera dos operários (aumentado de 6 para 8)

# Paleta alegre + industrial
C_BG = "#2b2d42"
C_GRID = "#33354d"
C_HUD = "#1d1e33"
C_TEXT = "#f8f9fa"
C_SOFT = "#adb5bd"
C_SHADOW = "#14152a"
C_YELLOW = "#ffd60a"
C_GOOD = "#38b000"
C_BAD = "#d90429"
C_PLAYER = "#2ec4b6"        # verde-água

ITEM_HELMET, ITEM_DOC, ITEM_COFFEE = "capacete", "holerite", "cafe"

# Cada necessidade: texto do balão, cor do balão e cor do texto
NEEDS = {
    ITEM_HELMET: {"label": "Falta EPI!", "bubble": "#f77f00", "fg": "#ffffff", "item": "Capacete"},
    ITEM_DOC:    {"label": "Dúvida no Holerite", "bubble": "#4ea8de", "fg": "#10223a", "item": "Holerite"},
    ITEM_COFFEE: {"label": "Preciso de Café!", "bubble": "#38b000", "fg": "#ffffff", "item": "Café"},
}

# Frases de humor corporativo
QUIPS = [
    "Reunião que poderia ser um e-mail está em andamento...",
    "Lembrete: \"Somos uma família\" não conta como benefício.",
    "O café acabou? Ninguém sabe quem foi.",
    "O sindicato está de olho no seu desempenho.",
    "Feedback é um presente. Embrulhe com capacete.",
    "Alguém esqueceu a senha do holerite. De novo.",
    "Pesquisa de clima: 100% dos operários pediram café.",
    "Dica de RH: respire fundo e imprima mais um contrato.",
    "Happy hour da fábrica cancelado por excesso de EPI.",
]
THANKS = ["Valeu, RH!", "Salvou meu dia!", "Finalmente!", "Até que enfim!", "Você é demais!", "Melhor RH!"]
WRONG = ["Isso não é meu!", "Eu pedi outra coisa!", "Quem pediu isso?!", "Errou o pedido!"]
RAGE = ["Vou ao sindicato!", "Vou pro LinkedIn!", "Pedi demissão!", "Quero falar c/ gerente!", "Tô fora!"]

WORKER_COLORS = ["#ff9f1c", "#e07a9b", "#90be6d", "#9d79bc", "#f9c74f", "#4cc9f0", "#f4845f"]


# ----------------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE DESENHO
# ----------------------------------------------------------------------------
def lerp_color(c1, c2, t):
    """Interpola duas cores hexadecimais (t de 0 a 1)."""
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rrect(c, x1, y1, x2, y2, r=12, **kw):
    """Retângulo com cantos arredondados (polígono suavizado)."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def text(c, x, y, s, size=12, color=C_TEXT, bold=True, anchor="center", shadow=False):
    """Atalho para texto, com sombra opcional."""
    font = ("Helvetica", size, "bold" if bold else "normal")
    if shadow:
        c.create_text(x + 2, y + 2, text=s, font=font, fill=C_SHADOW, anchor=anchor)
    return c.create_text(x, y, text=s, font=font, fill=color, anchor=anchor)


def draw_item(c, kind, cx, cy, s):
    """Desenha o ícone de um item (ou da lixeira) centrado em (cx, cy)."""
    if kind == ITEM_HELMET:
        c.create_arc(cx - s, cy - s * 0.9, cx + s, cy + s * 1.1, start=0, extent=180,
                     fill=C_YELLOW, outline="#b8860b", width=2)
        c.create_rectangle(cx - s * 1.25, cy + s * 0.1, cx + s * 1.25, cy + s * 0.38,
                           fill="#f77f00", outline="#b85c00", width=2)
        c.create_rectangle(cx - s * 0.12, cy - s * 0.85, cx + s * 0.12, cy + s * 0.1,
                           fill="#fff3b0", outline="")
    elif kind == ITEM_DOC:
        c.create_polygon(cx - s * 0.7, cy - s, cx + s * 0.3, cy - s, cx + s * 0.7, cy - s * 0.6,
                         cx + s * 0.7, cy + s, cx - s * 0.7, cy + s,
                         fill="#ffffff", outline="#6c757d", width=2)
        c.create_polygon(cx + s * 0.3, cy - s, cx + s * 0.3, cy - s * 0.6, cx + s * 0.7, cy - s * 0.6,
                         fill="#ced4da", outline="#6c757d")
        for k in (-0.25, 0.15, 0.55):
            c.create_line(cx - s * 0.45, cy + s * k, cx + s * 0.45, cy + s * k, fill="#4ea8de", width=2)
    elif kind == ITEM_COFFEE:
        c.create_oval(cx + s * 0.3, cy, cx + s * 0.95, cy + s * 0.55, outline="#ffffff", width=3)
        c.create_rectangle(cx - s * 0.7, cy - s * 0.2, cx + s * 0.5, cy + s * 0.8,
                           fill="#ffffff", outline="#6c757d", width=2)
        c.create_rectangle(cx - s * 0.6, cy - s * 0.15, cx + s * 0.4, cy + s * 0.12, fill="#6f4518", outline="")
        for dx in (-0.25, 0.15):
            c.create_line(cx + s * dx, cy - s * 0.4, cx + s * (dx + 0.1), cy - s * 0.9,
                          fill="#dee2e6", width=2, smooth=True)
    elif kind == "trash":
        c.create_rectangle(cx - s * 0.6, cy - s * 0.5, cx + s * 0.6, cy + s,
                           fill="#f1f3f5", outline="#6c757d", width=2)
        c.create_rectangle(cx - s * 0.85, cy - s * 0.85, cx + s * 0.85, cy - s * 0.5,
                           fill="#ced4da", outline="#6c757d", width=2)
        for dx in (-0.3, 0, 0.3):
            c.create_line(cx + s * dx, cy - s * 0.3, cx + s * dx, cy + s * 0.8, fill="#adb5bd", width=2)


# ----------------------------------------------------------------------------
# ESTAÇÃO
# ----------------------------------------------------------------------------
class Station:
    """Estação interativa: produz um item (com tempo de preparo) ou descarta."""

    REACH = 38  # distância máxima de interação a partir da borda

    def __init__(self, name, subtitle, rect, color, produces=None, process_time=0.0, is_trash=False):
        self.name, self.subtitle = name, subtitle
        self.rect = rect                     # (x1, y1, x2, y2)
        self.color = color
        self.produces = produces
        self.process_time = process_time
        self.is_trash = is_trash

    def distance_to(self, x, y):
        x1, y1, x2, y2 = self.rect
        dx = max(x1 - x, 0, x - x2)
        dy = max(y1 - y, 0, y - y2)
        return (dx * dx + dy * dy) ** 0.5

    def in_reach(self, x, y):
        return self.distance_to(x, y) <= self.REACH

    def draw(self, c, highlight=False):
        x1, y1, x2, y2 = self.rect
        cx = (x1 + x2) / 2
        rrect(c, x1 + 5, y1 + 7, x2 + 5, y2 + 7, 16, fill=C_SHADOW, outline="")
        rrect(c, x1, y1, x2, y2, 16, fill=self.color, outline=lerp_color(self.color, "#000000", 0.35), width=4)
        # medalhão do ícone
        c.create_oval(cx - 30, y1 + 10, cx + 30, y1 + 70, fill=lerp_color(self.color, "#ffffff", 0.3), outline="")
        draw_item(c, self.produces if self.produces else "trash", cx, y1 + 38, 17)
        text(c, cx, y2 - 32, self.name, 12, "#ffffff", shadow=True)
        text(c, cx, y2 - 14, self.subtitle, 9, lerp_color(self.color, "#ffffff", 0.8), bold=False)
        if highlight:
            rrect(c, x1 - 5, y1 - 5, x2 + 5, y2 + 5, 18, fill="", outline=C_YELLOW, width=4)
            text(c, cx, y2 + 20, "[E] / [ESPAÇO]", 10, C_YELLOW, shadow=True)


# ----------------------------------------------------------------------------
# JOGADOR
# ----------------------------------------------------------------------------
class Player:
    R = 20
    SPEED = 250

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.fx, self.fy = 0.0, 1.0   # direção
        self.item = None              # inventário (1 item)
        self.busy_left = 0.0          # tempo restante de preparo
        self.busy_total = 1.0
        self.pending = None
        self.bob = 0.0

    @property
    def busy(self):
        return self.busy_left > 0

    def start_processing(self, item, seconds):
        self.pending = item
        self.busy_left = self.busy_total = max(0.01, seconds)

    def update(self, dt, keys, obstacles):
        if self.busy:
            self.busy_left -= dt
            if self.busy_left <= 0:
                self.busy_left = 0
                self.item = self.pending
                self.pending = None
                return True
            return False

        dx = (("d" in keys) or ("right" in keys)) - (("a" in keys) or ("left" in keys))
        dy = (("s" in keys) or ("down" in keys)) - (("w" in keys) or ("up" in keys))
        if dx or dy:
            n = (dx * dx + dy * dy) ** 0.5
            dx, dy = dx / n, dy / n
            self.fx, self.fy = dx, dy
            self.bob += dt * 10

        half = self.R - 4
        # move um eixo por vez para deslizar nas paredes
        self.x += dx * self.SPEED * dt
        for (x1, y1, x2, y2) in obstacles:
            if self.x + half > x1 and self.x - half < x2 and self.y + half > y1 and self.y - half < y2:
                self.x = x1 - half if dx > 0 else x2 + half
        self.y += dy * self.SPEED * dt
        for (x1, y1, x2, y2) in obstacles:
            if self.x + half > x1 and self.x - half < x2 and self.y + half > y1 and self.y - half < y2:
                self.y = y1 - half if dy > 0 else y2 + half

        self.x = max(self.R, min(W - self.R, self.x))
        self.y = max(HUD_H + self.R, min(H - self.R, self.y))
        return False

    def draw(self, c):
        hop = abs((self.bob % 2.0) - 1.0) * 4          # saltinho ao andar
        x, y = self.x, self.y - hop
        r = self.R
        c.create_oval(x - r, self.y + r - 8, x + r, self.y + r + 6, fill=C_SHADOW, outline="")
        c.create_oval(x - r, y - r, x + r, y + r, fill=C_PLAYER, outline="#ffffff", width=3)
        # nariz/indicador de direção
        c.create_oval(x + self.fx * r - 5, y + self.fy * r - 5, x + self.fx * r + 5, y + self.fy * r + 5,
                      fill="#ffffff", outline=C_SHADOW)
        text(c, x, y, "RH", 13, "#0b3d3a")
        # item carregado grudado no jogador
        if self.item:
            ix, iy = x + r + 4, y - r - 4
            c.create_line(x + r * 0.6, y - r * 0.6, ix, iy, fill="#ffffff", width=3)
            c.create_oval(ix - 18, iy - 18, ix + 18, iy + 18, fill="#ffffff", outline=NEEDS[self.item]["bubble"], width=3)
            draw_item(c, self.item, ix, iy, 10)
        # barra de preparo
        if self.busy:
            frac = 1 - self.busy_left / self.busy_total
            c.create_rectangle(x - 26, y - r - 18, x + 26, y - r - 8, fill=C_SHADOW, outline="#ffffff")
            c.create_rectangle(x - 24, y - r - 16, x - 24 + 48 * frac, y - r - 10, fill=C_YELLOW, outline="")


# ----------------------------------------------------------------------------
# OPERÁRIO (NPC)
# ----------------------------------------------------------------------------
class Worker:
    HIT_RADIUS = 75  # alcance de entrega a partir do jogador
    R = 22

    def __init__(self, need, slot, slot_pos, patience):
        self.need = need
        self.slot = slot
        self.x = slot_pos[0] + random.uniform(-10, 10)
        self.y = H + 40
        self.tx, self.ty = slot_pos
        self.state = "entering"              # entering | waiting | leaving
        self.mood = None                     # happy | angry (ao sair)
        self.patience_max = patience
        self.patience = patience
        self.dead = False
        self.color = random.choice(WORKER_COLORS)

    @property
    def active(self):
        return self.state != "leaving"

    @property
    def frac(self):
        return max(0.0, self.patience / self.patience_max)

    def _walk(self, dt, speed):
        dx, dy = self.tx - self.x, self.ty - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= speed * dt:
            self.x, self.y = self.tx, self.ty
            return True
        self.x += dx / dist * speed * dt
        self.y += dy / dist * speed * dt
        return False

    def leave(self, mood):
        self.state, self.mood = "leaving", mood
        self.tx, self.ty = W / 2 + random.uniform(-30, 30), H + 50

    def update(self, dt):
        """Retorna 'timeout' quando a paciência zera."""
        if self.state == "entering":
            if self._walk(dt, 150):
                self.state = "waiting"
        elif self.state == "waiting":
            self.patience -= dt
            if self.patience <= 0:
                return "timeout"
        else:
            if self._walk(dt, 180 if self.mood == "angry" else 130):
                self.dead = True
        return None

    def draw(self, c, t):
        x, y, r = self.x, self.y, self.R
        if self.state == "waiting" and self.frac < 0.3:      # treme de nervoso
            x += random.choice((-2, 0, 2))
        body = self.color
        if self.mood == "angry":
            body = "#e5383b"
        elif self.mood == "happy":
            body = "#80ed99"
        c.create_oval(x - r, y + r - 8, x + r, y + r + 6, fill=C_SHADOW, outline="")
        c.create_oval(x - r, y - r, x + r, y + r, fill=body, outline=C_SHADOW, width=2)
        # capacete de operário
        c.create_arc(x - r, y - r, x + r, y + r, start=20, extent=140, fill=C_YELLOW, outline="#b8860b", width=2)
        # olhos
        for ex in (-8, 8):
            c.create_oval(x + ex - 5, y - 4, x + ex + 5, y + 6, fill="#ffffff", outline=C_SHADOW)
            c.create_oval(x + ex - 2, y - 1, x + ex + 2, y + 3, fill=C_SHADOW, outline="")
        # boca conforme humor/paciência
        upset = self.mood == "angry" or (self.state == "waiting" and self.frac < 0.35)
        happy = self.mood == "happy" or self.frac > 0.65
        if happy:
            c.create_arc(x - 7, y + 4, x + 7, y + 16, start=180, extent=180, style="arc", outline=C_SHADOW, width=2)
        elif upset:
            c.create_arc(x - 7, y + 10, x + 7, y + 22, start=0, extent=180, style="arc", outline=C_SHADOW, width=2)
            c.create_line(x - 13, y - 9, x - 4, y - 6, fill=C_SHADOW, width=2)
            c.create_line(x + 13, y - 9, x + 4, y - 6, fill=C_SHADOW, width=2)
        else:
            c.create_line(x - 5, y + 11, x + 5, y + 11, fill=C_SHADOW, width=2)

        if self.state == "leaving":
            return
        # balão de fala colorido
        info = NEEDS[self.need]
        by = y - 82
        bw = 70
        c.create_polygon(x - 8, by + 14, x + 8, by + 14, x, by + 28, fill=info["bubble"], outline="")
        rrect(c, x - bw, by - 15, x + bw, by + 15, 12, fill=info["bubble"], outline="#ffffff", width=2)
        text(c, x, by, info["label"], 10, info["fg"])
        # barra de paciência em degradê (vermelho -> verde)
        bx1, bx2, byy = x - 36, x + 36, y + r + 12
        c.create_rectangle(bx1 - 2, byy - 2, bx2 + 2, byy + 9, fill=C_SHADOW, outline="#ffffff")
        segs = 12
        sw = (bx2 - bx1) / segs
        filled = self.frac * segs
        for i in range(segs):
            if filled <= i:
                break
            part = min(1.0, filled - i)
            col = lerp_color("#d90429", "#38b000", i / (segs - 1))
            c.create_rectangle(bx1 + i * sw, byy, bx1 + i * sw + sw * part, byy + 7, fill=col, outline="")


# ----------------------------------------------------------------------------
# JOGO
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, root):
        self.root = root
        root.title("HR Overdrive: Fábrica em Caos")
        root.resizable(False, False)
        self.c = tk.Canvas(root, width=W, height=H, bg=C_BG, highlightthickness=0)
        self.c.pack()

        # entrada de teclado com tratamento de auto-repeat
        self.keys = set()
        self.release_jobs = {}
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        root.bind("<FocusOut>", lambda e: self.keys.clear())

        self.stations = [
            Station("Impressora DP", "Holerites & contratos", (40, 100, 240, 220), "#4ea8de", ITEM_DOC, 1.2),
            Station("Almoxarifado de EPIs", "Capacetes à vontade", (280, 100, 480, 220), "#f77f00", ITEM_HELMET, 0.5),
            Station("Cantinho do Café", "Combustível humano", (520, 100, 720, 220), "#38b000", ITEM_COFFEE, 1.5),
            Station("Gestão de Conflitos", "Lixeira: descarte aqui", (760, 100, 960, 220), "#d90429", None, 0.0, True),
        ]
        self.obstacles = [s.rect for s in self.stations]
        
        # Ajuste dinâmico dos slots de espera para acomodar o novo MAX_WAITING (8 slots distribuídos na tela)
        self.slots = [
            (60 + i * (880 / max(1, MAX_WAITING - 1)), 470) 
            for i in range(MAX_WAITING)
        ]

        self.state = "menu"      # menu | playing | victory | gameover
        self.paused = False
        self.anim = 0.0
        self.end_title = ""
        self.end_sub = ""
        self.reset()

        self.last = self.now_ms()
        self.tick()

    # -- utilidades -----------------------------------------------------------
    def now_ms(self):
        return int(self.root.tk.call("clock", "milliseconds"))

    def reset(self):
        self.player = Player(W / 2, 330)
        self.workers = []
        self.floaters = []
        self.elapsed = 0.0
        self.climate = 100
        self.served = 0
        self.lost = 0
        self.score = 0
        self.spawn_timer = 0.8
        self.quip = random.choice(QUIPS)
        self.quip_timer = 4.0
        self.paused = False

    def start_game(self):
        self.reset()
        self.state = "playing"

    def float_text(self, s, x, y, color=C_TEXT):
        self.floaters.append({"s": s, "x": x, "y": y, "t": 1.4, "color": color})

    # -- teclado ---------------------------------------------------------------
    def on_press(self, e):
        k = e.keysym.lower()
        job = self.release_jobs.pop(k, None)
        if job:
            self.root.after_cancel(job)
        if k in self.keys:          # auto-repeat do sistema: ignora
            return
        self.keys.add(k)
        self.key_down(k)

    def on_release(self, e):
        k = e.keysym.lower()
        # pequeno atraso: evita "soltar/pressionar" falsos do auto-repeat (Linux)
        self.release_jobs[k] = self.root.after(40, lambda: self.release_key(k))

    def release_key(self, k):
        self.keys.discard(k)
        self.release_jobs.pop(k, None)

    def key_down(self, k):
        if self.state == "menu":
            if k in ("return", "space", "kp_enter"):
                self.start_game()
            elif k == "escape":
                self.root.destroy()
        elif self.state == "playing":
            if k in ("e", "space") and not self.paused:
                self.interact()
            elif k == "p":
                self.paused = not self.paused
            elif k == "escape":
                self.state = "menu"
        else:
            if k in ("r", "return", "space"):
                self.start_game()
            elif k == "escape":
                self.state = "menu"

    # -- interação ---------------------------------------------------------------
    def interact(self):
        p = self.player
        if p.busy:
            return
        # 1) entregar ao operário certo
        if p.item:
            near = [w for w in self.workers if w.state == "waiting"
                    and ((w.x - p.x) ** 2 + (w.y - p.y) ** 2) ** 0.5 <= Worker.HIT_RADIUS]
            match = [w for w in near if w.need == p.item]
            if match:
                w = min(match, key=lambda k: (k.x - p.x) ** 2 + (k.y - p.y) ** 2)
                w.leave("happy")
                p.item = None
                self.served += 1
                bonus = 100 + int(w.frac * 50)       # rápido = mais pontos
                self.score += bonus
                self.climate = min(100, self.climate + SERVE_BONUS)
                self.float_text(random.choice(THANKS), w.x, w.y - 100, "#80ed99")
                self.float_text("+%d" % bonus, w.x, w.y - 78, C_YELLOW)
                return
        # 2) estação próxima
        near_st = [s for s in self.stations if s.in_reach(p.x, p.y)]
        if near_st:
            st = min(near_st, key=lambda s: s.distance_to(p.x, p.y))
            if st.is_trash:
                if p.item:
                    p.item = None
                    self.float_text("Problema empurrado p/ debaixo do tapete!", p.x, p.y - 50, "#ced4da")
                else:
                    self.float_text("Nada para descartar", p.x, p.y - 50, C_YELLOW)
            elif p.item:
                self.float_text("Mãos ocupadas!", p.x, p.y - 50, C_YELLOW)
            else:
                p.start_processing(st.produces, st.process_time)
            return
        # 3) item errado para quem está perto
        if p.item:
            close = [w for w in self.workers if w.state == "waiting"
                     and ((w.x - p.x) ** 2 + (w.y - p.y) ** 2) ** 0.5 <= Worker.HIT_RADIUS]
            if close:
                self.float_text(random.choice(WRONG), close[0].x, close[0].y - 100, "#ff8fa3")

    # -- atualização ---------------------------------------------------------------
    def spawn_worker(self):
        taken = {w.slot for w in self.workers if w.active}
        free = [i for i in range(MAX_WAITING) if i not in taken]
        if not free:
            return
        i = random.choice(free)
        # Tempo de paciência reduzido para os bonecos esperarem menos tempo (ex: 20 a 27 segundos em vez de 26 a 34)
        self.workers.append(Worker(random.choice(list(NEEDS)), i, self.slots[i], random.uniform(20, 27)))

    def update(self, dt):
        self.anim += dt
        if self.state != "playing" or self.paused:
            return
        self.elapsed += dt
        self.player.update(dt, self.keys, self.obstacles)

        # Chegada de operários: taxa aumentada em 20% (intervalos mais curtos)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_worker()
            # Intervalo base reduzido em ~20% para acelerar a taxa de spawn
            self.spawn_timer = max(2.7, 4.8 - self.elapsed * 0.024) * random.uniform(0.8, 1.2)

        for w in self.workers:
            if w.update(dt) == "timeout":
                w.leave("angry")
                self.lost += 1
                self.climate = max(0, self.climate - ANGRY_PENALTY)
                self.float_text(random.choice(RAGE), w.x, w.y - 100, "#ff8fa3")
                self.float_text("-%d%% Clima" % ANGRY_PENALTY, w.x, w.y - 78, "#ff4d6d")
        self.workers = [w for w in self.workers if not w.dead]

        for f in self.floaters:
            f["t"] -= dt
            f["y"] -= 28 * dt
        self.floaters = [f for f in self.floaters if f["t"] > 0]

        self.quip_timer -= dt
        if self.quip_timer <= 0:
            self.quip = random.choice(QUIPS)
            self.quip_timer = 4.0

        # fim de jogo
        if self.climate <= 0:
            self.end("gameover", "GREVE GERAL!", "O sindicato apareceu! A fábrica parou e o café esfriou.")
        elif self.elapsed >= SHIFT_SECONDS:
            if self.climate > WIN_CLIMATE:
                self.end("victory", "TURNO CONCLUÍDO!", self.rank())
            else:
                self.end("gameover", "CLIMA PESADO...",
                         "O turno acabou com Clima em %d%%. O RH foi convidado a \"se reinventar\"." % self.climate)

    def end(self, state, title, sub):
        self.state, self.end_title, self.end_sub = state, title, sub

    def rank(self):
        if self.served >= 25:
            return "Cargo: Diretor(a) de Gente & Gestão. Pizza na sexta por conta da casa!"
        if self.served >= 18:
            return "Cargo: Gerente de RH. Ganhou uma cadeira ergonômica!"
        if self.served >= 10:
            return "Cargo: Analista Sênior. Ganhou um \"parabéns\" por e-mail."
        return "Cargo: Estagiário(a) de RH. Pelo menos a fábrica sobreviveu!"

    # -- desenho -------------------------------------------------------------------
    def draw_floor(self):
        c = self.c
        for x in range(0, W, 50):
            c.create_line(x, HUD_H, x, H, fill=C_GRID)
        for y in range(HUD_H, H, 50):
            c.create_line(0, y, W, y, fill=C_GRID)
        # faixa de segurança amarela e preta
        for x in range(0, W, 30):
            c.create_polygon(x, HUD_H, x + 15, HUD_H, x + 7, HUD_H + 9, x - 8, HUD_H + 9, fill=C_YELLOW, outline="")
        # marcações dos postos de espera
        for sx, sy in self.slots:
            c.create_oval(sx - 32, sy + 12, sx + 32, sy + 34, outline="#4a4d6b", width=2)
        # portão de entrada
        rrect(c, W / 2 - 80, H - 26, W / 2 + 80, H + 10, 8, fill="#14152a", outline=C_YELLOW, width=3)
        text(c, W / 2, H - 12, "PORTÃO DA FÁBRICA", 9, C_YELLOW)

    def draw_hud(self):
        c = self.c
        c.create_rectangle(0, 0, W, HUD_H, fill=C_HUD, outline="")
        # clima da empresa
        text(c, 20, 10, "CLIMA DA EMPRESA", 9, C_SOFT, anchor="w")
        c.create_rectangle(20, 24, 300, 50, fill="#3a3c58", outline="#ffffff")
        col = lerp_color("#d90429", "#38b000", self.climate / 100)
        c.create_rectangle(22, 26, 22 + 276 * self.climate / 100, 48, fill=col, outline="")
        mx = 22 + 276 * WIN_CLIMATE / 100
        c.create_line(mx, 20, mx, 54, fill="#ffffff", width=2)
        text(c, 161, 37, "%d%%" % self.climate, 11, "#ffffff", shadow=True)
        # inventário
        text(c, 330, 10, "NAS MÃOS", 9, C_SOFT, anchor="w")
        rrect(c, 330, 22, 384, 62, 10, fill="#3a3c58", outline="#ffffff", width=2)
        if self.player.item:
            draw_item(c, self.player.item, 357, 42, 12)
            text(c, 394, 42, NEEDS[self.player.item]["item"], 13, C_YELLOW, anchor="w")
        else:
            text(c, 394, 42, "vazio", 12, C_SOFT, bold=False, anchor="w")
        # timer
        remaining = max(0, SHIFT_SECONDS - self.elapsed)
        s = int(remaining) + (1 if remaining % 1 > 0 else 0)
        blink = remaining < 15 and int(self.anim * 3) % 2 == 0
        text(c, 620, 10, "TURNO", 9, C_SOFT)
        text(c, 620, 40, "%02d:%02d" % (s // 60, s % 60), 24, "#ff4d6d" if blink else C_TEXT)
        # pontuação
        text(c, W - 20, 12, "Casos resolvidos: %d" % self.served, 12, "#80ed99", anchor="e")
        text(c, W - 20, 34, "Pontos: %d" % self.score, 12, C_YELLOW, anchor="e")
        text(c, W - 20, 54, "Insatisfeitos: %d" % self.lost, 10, "#ff8fa3", anchor="e")

    def draw_game(self):
        c = self.c
        self.draw_floor()
        p = self.player
        for st in self.stations:
            st.draw(c, highlight=st.in_reach(p.x, p.y) and not p.busy)
        # ordena por Y para dar profundidade
        for y, obj in sorted([(w.y, w) for w in self.workers] + [(p.y, p)], key=lambda d: d[0]):
            if isinstance(obj, Worker):
                obj.draw(c, self.anim)
            else:
                obj.draw(c)
        for f in self.floaters:
            text(c, f["x"], f["y"], f["s"], 12, f["color"], shadow=True)
        # frase de humor e dicas
        text(c, W / 2, H - 52, self.quip, 10, "#8d99ae", bold=False)
        text(c, 14, H - 12, "WASD/Setas: mover   E/Espaço: agir   P: pausa", 9, "#6c7293", bold=False, anchor="w")
        self.draw_hud()
        if self.paused:
            self.panel(300, 250, 700, 420, C_YELLOW)
            text(c, W / 2, 310, "PAUSA", 40, C_YELLOW, shadow=True)
            text(c, W / 2, 370, "Intervalo do cafezinho! Aperte P para voltar.", 11, C_TEXT, bold=False)

    def panel(self, x1, y1, x2, y2, border):
        rrect(self.c, x1 + 6, y1 + 8, x2 + 6, y2 + 8, 24, fill="#0d0e1c", outline="")
        rrect(self.c, x1, y1, x2, y2, 24, fill="#1d1e33", outline=border, width=5)

    def draw_menu(self):
        c = self.c
        self.draw_floor()
        self.panel(110, 40, 890, 660, C_YELLOW)
        text(c, W / 2, 110, "HR OVERDRIVE", 54, C_YELLOW, shadow=True)
        text(c, W / 2, 175, "Fábrica em Caos", 26, "#4ea8de", shadow=True)
        text(c, W / 2, 215, "Onde o \"bom dia\" vale 3 pontos de clima organizacional.", 11, C_SOFT, bold=False)
        # legenda das demandas
        rows = [
            (ITEM_HELMET, "Falta EPI!", "Pegue um Capacete no Almoxarifado", "#f77f00"),
            (ITEM_DOC, "Dúvida no Holerite", "Imprima um Holerite na Impressora DP", "#4ea8de"),
            (ITEM_COFFEE, "Preciso de Café!", "Sirva um Café no Cantinho do Café", "#38b000"),
        ]
        y = 275
        for kind, label, how, col in rows:
            rrect(c, 190, y - 28, 250, y + 28, 14, fill="#ffffff", outline=col, width=4)
            draw_item(c, kind, 220, y, 15)
            text(c, 275, y - 10, label, 14, col, anchor="w")
            text(c, 275, y + 12, how, 11, C_TEXT, bold=False, anchor="w")
            y += 68
        lines = [
            "Mover: WASD / Setas      Agir: E / Espaço      Pausar: P",
            "Carregue 1 item por vez. Pegou errado? Jogue na Gestão de Conflitos.",
            "Sobreviva %ds com Clima acima de %d%%. Se chegar a 0%%... o sindicato aparece!" % (SHIFT_SECONDS, WIN_CLIMATE),
        ]
        for i, ln in enumerate(lines):
            text(c, W / 2, 495 + i * 24, ln, 11, C_SOFT, bold=False)
        if int(self.anim * 2) % 2 == 0:
            text(c, W / 2, 595, "Pressione ENTER para começar o turno", 20, "#80ed99", shadow=True)
        text(c, W / 2, 635, "ESC para sair", 9, "#6c7293", bold=False)

    def draw_end(self):
        c = self.c
        self.draw_game()
        win = self.state == "victory"
        col = "#80ed99" if win else "#ff4d6d"
        self.panel(150, 130, 850, 580, col)
        text(c, W / 2, 205, self.end_title, 40, col, shadow=True)
        text(c, W / 2, 262, self.end_sub, 12, C_TEXT, bold=False)
        stats = ["Clima da empresa: %d%%" % self.climate,
                 "Casos resolvidos: %d" % self.served,
                 "Operários insatisfeitos: %d" % self.lost,
                 "Pontuação: %d" % self.score]
        for i, s in enumerate(stats):
            text(c, W / 2, 330 + i * 38, s, 17, C_YELLOW if i == 3 else C_TEXT, shadow=True)
        if int(self.anim * 2) % 2 == 0:
            text(c, W / 2, 530, "R / ENTER: novo turno      ESC: menu", 13, "#80ed99")

    def draw(self):
        self.c.delete("all")
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        else:
            self.draw_end()

    # -- loop principal ----------------------------------------------------------
    def tick(self):
        now = self.now_ms()
        dt = min((now - self.last) / 1000.0, 0.05)
        self.last = now
        self.update(dt)
        self.draw()
        self.root.after(TICK_MS, self.tick)


def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()