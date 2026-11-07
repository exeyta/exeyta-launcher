# -*- coding: utf-8 -*-
"""Раздел «Rust Edition»: Minecraft 26.3 на Rust (Horizon).

Отдельный запуск уже установленной сборки Horizon: свой клиент, свой
инстанс и свой .bat. Java-версии, моды и skin patcher сюда не вмешиваются.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

from exeyta_shared import theme

from .controls import Badge, CardPanel, FxButton, add_label, w
from .launch_panel import elide_path


class _AccentLine(QWidget):
    def __init__(self, parent=None, k=1.0):
        super().__init__(parent)
        self.k = float(k)

    def paintEvent(self, event=None):
        from PyQt5.QtCore import QRectF
        from PyQt5.QtGui import QColor, QLinearGradient, QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        g = QLinearGradient(r.left(), 0, r.right(), 0)
        g.setColorAt(0.0, QColor("#a8843c"))
        g.setColorAt(0.55, QColor("#d3b06a"))
        g.setColorAt(1.0, QColor("#c9a45c"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 2, 2)
        p.end()


class RustPanel(QWidget):
    """Страница «Rust Edition» (1144x640)."""

    play_clicked = pyqtSignal()
    open_home_clicked = pyqtSignal()
    open_bat_clicked = pyqtSignal()
    prepare_clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(1144 * k), round(640 * k))
        self._info = {}
        self._build()

    def _build(self):
        k = self.k

        # ------------------------------------------------------------ герой
        self.card = CardPanel(round(1144 * k), round(226 * k),
                              radius=14, border="#26272d", parent=self)
        self.card.move(0, 0)
        add_label(self.card, k, 26, 36, 11, 700, 500,
                  "MINECRAFT 26.3 · RUST EDITION", color="#8b8f98")
        add_label(self.card, k, 26, 96, 38, 800, 500, "Rust Edition")
        self.badge = Badge("не найдено", k=k, color="#c9a45c",
                           parent=self.card)
        self.badge.move(round(26 * k), round(112 * k))
        self.lbl_state = add_label(
            self.card, k, 112, 128, 12, 500, 780,
            "Horizon не найден", color="#8b8f98")
        self._line = _AccentLine(self.card, k=k)
        self._line.setGeometry(round(26 * k), round(148 * k),
                               round(1092 * k), round(4 * k))

        ico_play = theme.icon_pixmap(theme.ICON_PLAY, round(14 * k),
                                     "#1c1609", stroke=1.8, fill="#1c1609")
        self.btn_play = FxButton("Играть", kind="sun",
                                 w_=round(150 * k), h_=round(46 * k),
                                 radius=9, px=14, svg_w=700,
                                 icon=ico_play, gap=9, parent=self.card)
        self.btn_play.move(round(26 * k), round(164 * k))
        self.btn_play.clicked.connect(self.play_clicked.emit)

        ico_folder = theme.icon_pixmap(theme.ICON_FOLDER, round(15 * k),
                                       "#c7cad1", stroke=1.7)
        self.btn_home = FxButton("Открыть папку", kind="ghost",
                                 w_=round(172 * k), h_=round(46 * k),
                                 radius=9, px=13, svg_w=600,
                                 icon=ico_folder, gap=8, parent=self.card)
        self.btn_home.move(round(188 * k), round(164 * k))
        self.btn_home.clicked.connect(self.open_home_clicked.emit)

        self.btn_bat = FxButton("Открыть .bat", kind="ghost",
                                w_=round(172 * k), h_=round(46 * k),
                                radius=9, px=13, svg_w=600,
                                parent=self.card)
        self.btn_bat.move(round(372 * k), round(164 * k))
        self.btn_bat.clicked.connect(self.open_bat_clicked.emit)

        self.btn_prepare = FxButton("Как подготовить", kind="ghost",
                                    w_=round(180 * k), h_=round(46 * k),
                                    radius=9, px=13, svg_w=600,
                                    parent=self.card)
        self.btn_prepare.move(round(556 * k), round(164 * k))
        self.btn_prepare.clicked.connect(self.prepare_clicked.emit)

        # ------------------------------------------------------- три карточки
        cards = [
            (0, "СБОРКА", "v0.2.97.1", "Horizon Offline Launcher"),
            (386, "РЕСУРСЫ", "26.3", "подготовлены"),
            (772, "ПРОФИЛЬ", "puzzle999", "classic · скин Exeyta"),
        ]
        self.cards = []
        self.vals = {}
        for x, cap, val, sub in cards:
            c = CardPanel(round(372 * k), round(150 * k), radius=14,
                          border="#26272d", parent=self)
            c.move(round(x * k), round(246 * k))
            add_label(c, k, 22, 32, 10.5, 700, 320, cap, color="#8b8f98")
            v = add_label(c, k, 22, 74, 20, 700, 330, val)
            s = add_label(c, k, 22, 106, 11, 500, 330, sub, color="#8b8f98")
            self.vals[cap] = (v, s)
            self.cards.append(c)

        # ------------------------------------------------------------ пути
        self.paths = CardPanel(round(1144 * k), round(206 * k), radius=14,
                               border="#26272d", parent=self)
        self.paths.move(0, round(416 * k))
        add_label(self.paths, k, 26, 34, 10.5, 700, 500, "ПУТИ",
                  color="#8b8f98")
        self.lbl_home = self._row("Инстанс", "…")
        self.lbl_res = self._row("Ресурсы", "…")
        self.lbl_bat = self._row("Батник", "…")
        add_label(self.paths, k, 26, 180, 11, 500, 1080,
                  "Моды Java Edition сюда не подходят: у Horizon свои .hmod. "
                  "Java-версии остаются в разделе «Версии».",
                  color="#62666e")

    def _row(self, cap, val):
        k = self.k
        y = 66 if cap == "Инстанс" else (110 if cap == "Ресурсы" else 150)
        add_label(self.paths, k, 26, y, 11.5, 500, 150, cap, color="#9a9ea7")
        lbl = add_label(self.paths, k, 150, y, 11.5, 600, 964, val,
                        align=Qt.AlignRight | Qt.AlignVCenter)
        return lbl

    # --- обновления ------------------------------------------------------
    def set_info(self, info):
        self._info = dict(info or {})
        ok = bool(self._info.get("ok"))
        self.badge.set_text("готово" if ok else "не найдено")
        self.badge.set_color("#7fbf8f" if ok else "#c9a45c")
        if ok:
            self.lbl_state.setText(
                "Horizon · сборка %s · инстанс %s"
                % (self._info.get("tag") or "—",
                   self._info.get("instance") or "—"))
        else:
            self.lbl_state.setText(self._info.get("error") or "Horizon не найден")
        self.btn_play.set_disabled(not ok)

        build = self.vals["СБОРКА"]
        build[0].setText(str(self._info.get("tag") or "—"))
        build[1].setText("Horizon Offline Launcher")

        res = self.vals["РЕСУРСЫ"]
        res[0].setText(str(self._info.get("mc_version") or "26.3"))
        res[1].setText("подготовлены" if self._info.get("prepared")
                       else "не подготовлены")

        self.lbl_home.setText(elide_path(self._info.get("home") or "—",
                                         11.5, 940, self.k))
        self.lbl_home.setToolTip(str(self._info.get("home") or ""))
        self.lbl_res.setText(elide_path(self._info.get("resources") or "—",
                                        11.5, 940, self.k))
        self.lbl_res.setToolTip(str(self._info.get("resources") or ""))
        self.lbl_bat.setText(elide_path(
            self._info.get("bat_path") or "создастся при запуске",
            11.5, 940, self.k))
        self.lbl_bat.setToolTip(str(self._info.get("bat_path") or ""))

    def set_account(self, nick, skin="", model="classic"):
        prof = self.vals["ПРОФИЛЬ"]
        prof[0].setText(str(nick or "Player"))
        if skin:
            prof[1].setText("%s · %s" % (model, skin.rsplit("\\", 1)[-1]))
        else:
            prof[1].setText("%s · без скина" % model)

    def set_bat_path(self, path):
        self._info["bat_path"] = str(path)
        self.lbl_bat.setText(elide_path(str(path), 11.5, 940, self.k))
        self.lbl_bat.setToolTip(str(path))

    def set_busy(self, flag):
        self.btn_play.set_disabled(bool(flag) or not self._info.get("ok"))
        self.btn_play.set_text("Запуск…" if flag else "Играть")

    def set_status(self, text, color="#7fbf8f"):
        pass
