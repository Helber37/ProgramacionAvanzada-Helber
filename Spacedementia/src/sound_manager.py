"""Sistema de sonido retro generado por código (síntesis con pygame.mixer).

Frecuencias calibradas según guía de audio arcade:
- Feedback/señales (disparos, coins, powerups): 2-4 kHz para claridad
- Impacto/explosiones: graves 80-250 Hz para peso
- Amplitudes moderadas para evitar fatiga auditiva
"""

import array
import math
import random

import pygame


class SoundManager:
    """Genera efectos de sonido retro usando ondas sintéticas puras."""

    def __init__(self):
        self.sfx_volume = 0.35
        self.music_volume = 0.3
        self.enabled = False
        self.sounds = {}
        self.music_sound = None
        self.music_playing = False
        self.music_channel = None

        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
            self._generate_sounds()
        except pygame.error:
            pass

    def _tone(self, frequency, duration_ms, wave="square", fade_out=True):
        """Genera un tono simple."""
        sr = 22050
        n = int(sr * duration_ms / 1000)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            if wave == "square":
                val = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0
            elif wave == "saw":
                val = 2.0 * (frequency * t % 1) - 1.0
            elif wave == "sine":
                val = math.sin(2 * math.pi * frequency * t)
            elif wave == "noise":
                val = random.uniform(-1, 1)
            else:
                val = 0.0
            if fade_out:
                val *= 1.0 - (i / n)
            buf[i] = max(-32000, min(32000, int(val * 10000)))
        return pygame.mixer.Sound(buffer=buf)

    def _sweep(self, f_start, f_end, duration_ms, wave="square"):
        """Genera un barrido de frecuencia."""
        sr = 22050
        n = int(sr * duration_ms / 1000)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            f = f_start + (f_end - f_start) * p
            if wave == "square":
                val = 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0
            elif wave == "saw":
                val = 2.0 * (f * t % 1) - 1.0
            else:
                val = math.sin(2 * math.pi * f * t)
            val *= 1.0 - p * 0.8
            buf[i] = max(-32000, min(32000, int(val * 9000)))
        return pygame.mixer.Sound(buffer=buf)

    def _laser(self):
        """Disparo jugador: sweep en zona de claridad (3kHz -> 800Hz)."""
        return self._sweep(3000, 800, 90, "square")

    def _enemy_laser(self):
        """Disparo enemigo: más grave para distinguirlo (1.5kHz -> 400Hz)."""
        return self._sweep(1500, 400, 70, "saw")

    def _explosion(self):
        """Explosión: graves con ruido (80-200 Hz para peso)."""
        sr = 22050
        n = int(sr * 0.25)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            # Fundamental grave (120 -> 60 Hz)
            low = math.sin(2 * math.pi * (120 - 60 * p) * t)
            # Ruido para textura
            noise = random.uniform(-1, 1)
            # Armónico medio sutil para definición (~500 Hz)
            mid = math.sin(2 * math.pi * 500 * t) * 0.15
            val = (low * 0.45 + noise * 0.4 + mid) * (1.0 - p)
            buf[i] = max(-32000, min(32000, int(val * 11000)))
        return pygame.mixer.Sound(buffer=buf)

    def _hit(self):
        """Impacto al jugador: transiente corto en medios (2.5kHz -> 200Hz)."""
        return self._sweep(2500, 200, 100, "saw")

    def _powerup(self):
        """Power-up: sweep ascendente en zona de claridad (1kHz -> 3.5kHz)."""
        return self._sweep(1000, 3500, 160, "sine")

    def _coin(self):
        """Coin/level-up: dos tonos en zona de feedback (2.5kHz / 3.5kHz)."""
        sr = 22050
        n = int(sr * 0.15)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            f = 2500 if p < 0.45 else 3500
            val = math.sin(2 * math.pi * f * t) * (1.0 - p * 0.5)
            buf[i] = max(-32000, min(32000, int(val * 8000)))
        return pygame.mixer.Sound(buffer=buf)

    def _boss_roar(self):
        """Boss aparece: graves profundos (60-200 Hz) con armónicos."""
        sr = 22050
        n = int(sr * 0.6)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            # Fundamental grave ascendente (60 -> 200 Hz)
            f = 60 + 140 * p
            low = math.sin(2 * math.pi * f * t) * 0.5
            # Armónico cuadrado para agresividad
            sq = (1.0 if math.sin(2 * math.pi * f * 1.5 * t) >= 0 else -1.0) * 0.25
            # Ruido sutil
            noise = random.uniform(-1, 1) * 0.15
            val = low + sq + noise
            # Envolvente: ataque rápido, sustain, release
            env = min(1.0, p * 4) * (1.0 - max(0, (p - 0.7) / 0.3))
            val *= env
            buf[i] = max(-32000, min(32000, int(val * 11000)))
        return pygame.mixer.Sound(buffer=buf)

    def _boss_defeat(self):
        """Boss derrotado: sweep ascendente gratificante (800 -> 4kHz)."""
        sr = 22050
        n = int(sr * 0.4)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            f = 800 + 3200 * p
            val = math.sin(2 * math.pi * f * t)
            # Armónico para brillo
            val += math.sin(2 * math.pi * f * 2 * t) * 0.2
            val *= (1.0 - p * 0.6)
            buf[i] = max(-32000, min(32000, int(val * 8000)))
        return pygame.mixer.Sound(buffer=buf)

    def _game_over(self):
        """Game over: descenso de medios a graves (600 -> 100 Hz)."""
        sr = 22050
        n = int(sr * 0.8)
        buf = array.array("h", [0] * n)
        for i in range(n):
            t = i / sr
            p = i / n
            f = 600 - 500 * p
            val = math.sin(2 * math.pi * f * t) * (1.0 - p * 0.85)
            buf[i] = max(-32000, min(32000, int(val * 9000)))
        return pygame.mixer.Sound(buffer=buf)

    def _menu_click(self):
        """Click de menú: tono corto en zona de claridad (2.8kHz)."""
        return self._tone(2800, 35, "square")

    def _menu_confirm(self):
        """Confirmación: sweep ascendente corto (2kHz -> 3.5kHz)."""
        return self._sweep(2000, 3500, 90, "sine")

    def _generate_music(self):
        """Genera la Novena Sinfonía de Beethoven (Oda a la Alegría) en versión chiptune."""
        sr = 22050
        bpm = 130
        beat = 60.0 / bpm

        NOTE = {
            "R": 0,
            "C3": 130.81, "Cs3": 138.59, "D3": 146.83, "Ds3": 155.56,
            "E3": 164.81, "F3": 174.61, "Fs3": 185.00, "G3": 196.00,
            "Gs3": 207.65, "A3": 220.00, "As3": 233.08, "B3": 246.94,
            "C4": 261.63, "Cs4": 277.18, "D4": 293.66, "Ds4": 311.13,
            "E4": 329.63, "F4": 349.23, "Fs4": 369.99, "G4": 392.00,
            "Gs4": 415.30, "A4": 440.00, "As4": 466.16, "B4": 493.88,
            "C5": 523.25, "Cs5": 554.37, "D5": 587.33, "Ds5": 622.25,
            "E5": 659.26, "F5": 698.46, "Fs5": 739.99, "G5": 783.99,
            "Gs5": 830.61, "A5": 880.00,
        }

        # Oda a la Alegría - melodía completa 24 compases
        melody = [
            # Frase A
            ("E4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5),
            ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 0.5),
            ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("E4", 0.5),
            ("E4", 0.75), ("D4", 0.25), ("D4", 1.0),
            # Frase B
            ("E4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5),
            ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 0.5),
            ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("E4", 0.5),
            ("D4", 0.75), ("C4", 0.25), ("C4", 1.0),
            # Frase C (parte media)
            ("D4", 0.5), ("D4", 0.5), ("E4", 0.5), ("C4", 0.5),
            ("D4", 0.5), ("E4", 0.25), ("F4", 0.25), ("E4", 0.5), ("C4", 0.5),
            ("D4", 0.5), ("E4", 0.25), ("F4", 0.25), ("E4", 0.5), ("D4", 0.5),
            ("C4", 0.5), ("D4", 0.5), ("G3", 0.5), ("R", 0.5),
            # Repite Frase A para cerrar
            ("E4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5),
            ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 0.5),
            ("C4", 0.5), ("C4", 0.5), ("D4", 0.5), ("E4", 0.5),
            ("D4", 0.75), ("C4", 0.25), ("C4", 1.0),
        ]

        # Bajo armónico
        bass = [
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
            # Parte media
            ("G3", 1.0), ("G3", 1.0), ("A3", 1.0), ("F3", 1.0),
            ("G3", 1.0), ("G3", 1.0), ("A3", 1.0), ("F3", 1.0),
            ("G3", 2.0), ("G3", 2.0), ("C3", 2.0), ("C3", 2.0),
            # Repite final
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
            ("E3", 2.0), ("E3", 2.0), ("C3", 2.0), ("D3", 2.0),
        ]

        total_beats_melody = sum(d for _, d in melody)
        total_beats_bass = sum(d for _, d in bass)
        total_beats = max(total_beats_melody, total_beats_bass)
        total_samples = int(sr * total_beats * beat)

        buf = array.array("h", [0] * total_samples)

        self._render_track(buf, melody, NOTE, sr, beat, wave="square", volume=0.35)
        self._render_track(buf, bass, NOTE, sr, beat, wave="sine", volume=0.18)

        self.music_sound = pygame.mixer.Sound(buffer=buf)
        self.music_sound.set_volume(self.music_volume)

    def _render_track(self, buf, notes, note_map, sr, beat, wave="square", volume=0.3):
        """Renderiza una pista de notas sobre un buffer existente (mezcla aditiva)."""
        pos = 0  # posición en samples
        for note_name, duration in notes:
            freq = note_map.get(note_name, 0)
            n_samples = int(sr * duration * beat)

            if freq > 0:
                for i in range(n_samples):
                    if pos + i >= len(buf):
                        break
                    t = i / sr
                    p = i / n_samples

                    if wave == "square":
                        val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
                        # Suavizar un poco la cuadrada para que suene más 8-bit amigable
                        val *= 0.8
                        # Agregar armónico sutil
                        val += math.sin(2 * math.pi * freq * 2 * t) * 0.15
                    elif wave == "sine":
                        val = math.sin(2 * math.pi * freq * t)
                    else:
                        val = math.sin(2 * math.pi * freq * t)

                    # Envolvente ADSR simple
                    attack = 0.02
                    release = 0.15
                    if p < attack:
                        env = p / attack
                    elif p > (1.0 - release):
                        env = (1.0 - p) / release
                    else:
                        env = 1.0

                    val *= env * volume
                    sample = buf[pos + i] + int(val * 16000)
                    buf[pos + i] = max(-32000, min(32000, sample))

            pos += n_samples

    def _generate_sounds(self):
        """Genera todos los efectos y música."""
        self.sounds["shoot"] = self._laser()
        self.sounds["enemy_shoot"] = self._enemy_laser()
        self.sounds["explosion"] = self._explosion()
        self.sounds["hit"] = self._hit()
        self.sounds["powerup"] = self._powerup()
        self.sounds["boss_appear"] = self._boss_roar()
        self.sounds["boss_defeat"] = self._boss_defeat()
        self.sounds["level_up"] = self._coin()
        self.sounds["menu_select"] = self._menu_click()
        self.sounds["menu_confirm"] = self._menu_confirm()
        self.sounds["game_over"] = self._game_over()
        self._generate_music()
        self._apply_volumes()

    def _apply_volumes(self):
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def play_music(self):
        """Inicia la música de fondo en loop."""
        if self.enabled and self.music_sound:
            self.music_channel = self.music_sound.play(loops=-1)
            if self.music_channel:
                self.music_channel.set_volume(self.music_volume)
            self.music_playing = True

    def stop_music(self):
        """Detiene la música."""
        if self.enabled and self.music_sound:
            self.music_sound.stop()
            self.music_playing = False

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))
        if self.enabled:
            self._apply_volumes()

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        if self.enabled and hasattr(self, "music_channel") and self.music_channel:
            self.music_channel.set_volume(self.music_volume)

    def get_sfx_volume(self):
        return self.sfx_volume

    def get_music_volume(self):
        return self.music_volume

    def cleanup(self):
        if self.enabled:
            pygame.mixer.quit()
