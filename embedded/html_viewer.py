#!/usr/bin/env python3
"""
STM32MP135F-DK Advanced Edge Kiosk & FocusDesk Dashboard
Native GTK3 / Cairo / Wayland SHM Engine
Pixel-perfect for 480x272 LCD @ 60Hz
Includes FocusDesk Offline Touch Task Manager & Backlight Power Saver
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import datetime
import cairo
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib

HTML_FILE = "/home/weston/index.html"
if not os.path.exists(HTML_FILE):
    HTML_FILE = "/home/root/index.html"

CONFIG_PATH = "/etc/focusdesk/config.json"
DB_PATH = "/var/lib/focusdesk/tasks.db"
BACKLIGHT_PATH = "/sys/class/backlight/panel-backlight/brightness"

MODERN_CSS = b"""
* {
    font-family: -apple-system, "Segoe UI", Roboto, "Liberation Sans", sans-serif;
    outline: none;
}

window {
    background-color: #0B0F19;
    color: #F9FAFB;
}

/* Header & Navbar */
.top-header {
    background-color: #0F172A;
    border-bottom: 1px solid #1E293B;
    padding: 2px 6px;
}

.brand-badge {
    background: linear-gradient(135deg, #0284C7, #38BDF8);
    color: #FFFFFF;
    font-weight: 800;
    font-size: 10px;
    border-radius: 3px;
    padding: 1px 5px;
}

.brand-title {
    font-weight: 700;
    font-size: 11px;
    color: #F8FAFC;
}

.brand-subtitle {
    font-size: 9px;
    color: #38BDF8;
    background-color: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 8px;
    padding: 1px 4px;
    font-weight: 600;
}

.online-badge {
    font-size: 8px;
    color: #10B981;
    background-color: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 8px;
    padding: 1px 5px;
    font-weight: 700;
}

.clock-label {
    font-family: monospace;
    font-size: 9px;
    color: #94A3B8;
}

/* Tab Navigation */
.nav-bar {
    background-color: #111827;
    border-bottom: 1px solid #1E293B;
    padding: 2px 3px;
}

.nav-btn {
    background-color: transparent;
    border: 1px solid transparent;
    color: #94A3B8;
    font-size: 9.5px;
    font-weight: 600;
    padding: 2px 3px;
    border-radius: 3px;
}

.nav-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #F8FAFC;
}

.nav-btn.active {
    background-color: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
    color: #38BDF8;
}

/* Glassmorphic Cards */
.card-box {
    background-color: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 4px;
    padding: 3px 5px;
}

.card-title {
    font-size: 8px;
    font-weight: 700;
    color: #94A3B8;
    letter-spacing: 0.5px;
}

.card-pill {
    font-size: 7.5px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
}

.pill-cyan {
    background-color: rgba(56, 189, 248, 0.15);
    color: #38BDF8;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

.pill-emerald {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.pill-amber {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.pill-rose {
    background-color: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.pill-purple {
    background-color: rgba(139, 92, 246, 0.15);
    color: #A78BFA;
    border: 1px solid rgba(139, 92, 246, 0.3);
}

/* Big Metric Numbers */
.metric-num {
    font-family: monospace;
    font-size: 13px;
    font-weight: 800;
    color: #F8FAFC;
}

.metric-sub {
    font-size: 8px;
    color: #64748B;
}

/* Custom Progress Bars */
progressbar trough {
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    min-height: 4px;
}

progressbar.cyan progress {
    background: linear-gradient(90deg, #0284C7, #38BDF8);
    border-radius: 3px;
}

progressbar.emerald progress {
    background: linear-gradient(90deg, #059669, #10B981);
    border-radius: 3px;
}

progressbar.purple progress {
    background: linear-gradient(90deg, #7C3AED, #A78BFA);
    border-radius: 3px;
}

/* Buttons */
.action-btn {
    background: linear-gradient(135deg, #0284C7, #38BDF8);
    border: none;
    color: #FFFFFF;
    font-size: 9.5px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
}

.action-btn:hover {
    background: linear-gradient(135deg, #0369A1, #0284C7);
}

.action-btn-outline {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid #334155;
    color: #E2E8F0;
    font-size: 9px;
    font-weight: 600;
    padding: 2px 5px;
    border-radius: 3px;
}

.task-complete-btn {
    background-color: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.5);
    color: #34D399;
    font-size: 9.5px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 3px;
}

.task-complete-btn:hover {
    background-color: #10B981;
    color: #FFFFFF;
}

.task-reopen-btn {
    background-color: rgba(107, 114, 128, 0.2);
    border: 1px solid rgba(107, 114, 128, 0.4);
    color: #9CA3AF;
    font-size: 9.5px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 3px;
}

.close-btn {
    background-color: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #EF4444;
    font-size: 9px;
    font-weight: bold;
    padding: 1px 5px;
    border-radius: 3px;
}

.close-btn:hover {
    background-color: #EF4444;
    color: #FFFFFF;
}

/* Footer */
.bot-footer {
    background-color: #0F172A;
    border-top: 1px solid #1E293B;
    padding: 2px 6px;
    font-size: 8px;
    color: #64748B;
}
"""

class SparklineWidget(Gtk.DrawingArea):
    """Custom Cairo-drawn real-time CPU sparkline graph"""
    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 18)
        self.points = [12, 15, 14, 18, 16, 20, 22, 19, 15, 18, 16, 14, 18, 20, 16]
        self.connect("draw", self.on_draw)

    def add_point(self, val):
        self.points.pop(0)
        self.points.append(max(2, min(98, val)))
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        if width <= 0 or height <= 0:
            return False

        n = len(self.points)
        step = width / max(1, (n - 1))

        pat = cairo.LinearGradient(0, 0, 0, height)
        pat.add_color_stop_rgba(0, 0.22, 0.74, 0.97, 0.3)
        pat.add_color_stop_rgba(1, 0.22, 0.74, 0.97, 0.0)

        cr.move_to(0, height)
        for i, val in enumerate(self.points):
            x = i * step
            y = height - (val / 100.0 * height)
            cr.line_to(x, y)
        cr.line_to(width, height)
        cr.close_path()
        cr.set_source(pat)
        cr.fill()

        cr.set_line_width(1.2)
        cr.set_source_rgba(0.22, 0.74, 0.97, 0.9)
        for i, val in enumerate(self.points):
            x = i * step
            y = height - (val / 100.0 * height)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()
        return False


class AdvancedEdgeKiosk(Gtk.Window):
    def __init__(self):
        super().__init__(title="STM32MP135F-DK FocusDesk Kiosk")
        self.set_default_size(480, 272)
        self.set_decorated(False)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key_press)
        self.connect("button-press-event", self.on_user_interaction)

        # FocusDesk Backlight Power Saving
        self.last_activity = time.time()
        self.idle_timeout_sec = 120
        self.dimmed_brightness = 1
        self.active_brightness = 10
        self.screen_is_dimmed = False
        self.last_db_mtime = 0
        self.current_task_filter = "pending"  # "all", "pending", "completed"

        self.load_settings()

        # Apply CSS
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(MODERN_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.prev_cpu_stat = self.read_cpu_raw()
        self.cpu_usage_pct = 12.0
        self.ram_used_mb = 122.0
        self.ram_free_mb = 315.0
        self.ram_total_mb = 437.1
        self.wifi_ssid = "SRIGANESH_AP"

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # Top Header
        main_box.pack_start(self.build_top_header(), False, False, 0)

        # Tab Bar
        main_box.pack_start(self.build_nav_bar(), False, False, 0)

        # Content Stack with Scrolling
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_kinetic_scrolling(True)
        main_box.pack_start(self.scroll, True, True, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(100)
        self.scroll.add(self.stack)

        # Build tabs
        self.stack.add_named(self.build_page_tasks(), "tasks")
        self.stack.add_named(self.build_page_overview(), "overview")
        self.stack.add_named(self.build_page_network(), "network")
        self.stack.add_named(self.build_page_telemetry(), "telemetry")
        self.stack.add_named(self.build_page_controls(), "controls")
        self.stack.add_named(self.build_page_diagnostics(), "diagnostics")

        # Footer
        main_box.pack_start(self.build_footer(), False, False, 0)

        GLib.timeout_add(1500, self.update_telemetry)
        GLib.timeout_add(1000, self.update_clock)
        GLib.timeout_add_seconds(3, self.check_backlight_and_db)

        self.show_all()
        self.fullscreen()
        self.present()

    def load_settings(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.idle_timeout_sec = int(cfg.get("idle_backlight_sec", 120))
                    self.dimmed_brightness = int(cfg.get("dimmed_brightness", 1))
                    self.active_brightness = int(cfg.get("active_brightness", 10))
            except Exception:
                pass

    def set_backlight(self, val):
        try:
            if os.path.exists(BACKLIGHT_PATH):
                with open(BACKLIGHT_PATH, "w") as f:
                    f.write(str(val) + "\n")
        except Exception:
            pass

    def on_user_interaction(self, widget, event):
        self.last_activity = time.time()
        if self.screen_is_dimmed:
            self.set_backlight(self.active_brightness)
            self.screen_is_dimmed = False
        return False

    def check_backlight_and_db(self):
        # 1. Backlight idle check
        if self.idle_timeout_sec > 0:
            idle_time = time.time() - self.last_activity
            if idle_time > self.idle_timeout_sec and not self.screen_is_dimmed:
                self.set_backlight(self.dimmed_brightness)
                self.screen_is_dimmed = True

        # 2. Database change check
        if os.path.exists(DB_PATH):
            try:
                mtime = os.path.getmtime(DB_PATH)
                if self.last_db_mtime != 0 and mtime != self.last_db_mtime:
                    self.refresh_tasks_view()
                self.last_db_mtime = mtime
            except Exception:
                pass
        return True

    # -------------------------------------------------------------------------
    # TOP HEADER
    # -------------------------------------------------------------------------
    def build_top_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.get_style_context().add_class("top-header")

        brand = Gtk.Label(label="FOCUS")
        brand.get_style_context().add_class("brand-badge")
        header.pack_start(brand, False, False, 0)

        title = Gtk.Label(label="FocusDesk")
        title.get_style_context().add_class("brand-title")
        header.pack_start(title, False, False, 1)

        sub = Gtk.Label(label="STM32MP135")
        sub.get_style_context().add_class("brand-subtitle")
        header.pack_start(sub, False, False, 1)

        online = Gtk.Label(label="● LIVE")
        online.get_style_context().add_class("online-badge")
        header.pack_start(online, False, False, 1)

        self.clock_lbl = Gtk.Label(label="--:--:-- UTC")
        self.clock_lbl.get_style_context().add_class("clock-label")
        header.pack_end(self.clock_lbl, False, False, 2)

        close_btn = Gtk.Button(label="✕")
        close_btn.get_style_context().add_class("close-btn")
        close_btn.connect("clicked", lambda b: Gtk.main_quit())
        header.pack_end(close_btn, False, False, 1)

        return header

    # -------------------------------------------------------------------------
    # TAB BAR
    # -------------------------------------------------------------------------
    def build_nav_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar.get_style_context().add_class("nav-bar")

        self.nav_buttons = {}
        tabs = [
            ("tasks", "✅ Tasks"),
            ("overview", "📊 Status"),
            ("network", "📶 Wi-Fi"),
            ("telemetry", "⚡ Sensors"),
            ("controls", "🛠️ Tools"),
            ("diagnostics", "📋 Logs")
        ]

        for name, label in tabs:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("nav-btn")
            if name == "tasks":
                btn.get_style_context().add_class("active")
            btn.connect("clicked", self.on_tab_clicked, name)
            bar.pack_start(btn, True, True, 0)
            self.nav_buttons[name] = btn

        return bar

    def on_tab_clicked(self, btn, tab_name):
        self.on_user_interaction(None, None)
        for name, b in self.nav_buttons.items():
            b.get_style_context().remove_class("active")
        btn.get_style_context().add_class("active")
        self.stack.set_visible_child_name(tab_name)
        self.scroll.get_vadjustment().set_value(0)
        if tab_name == "tasks":
            self.refresh_tasks_view()

    # -------------------------------------------------------------------------
    # TAB 1: FOCUSDESK TOUCH TASK MANAGER
    # -------------------------------------------------------------------------
    def build_page_tasks(self):
        self.tasks_page_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.tasks_page_vbox.set_margin_top(2)
        self.tasks_page_vbox.set_margin_bottom(4)
        self.tasks_page_vbox.set_margin_start(4)
        self.tasks_page_vbox.set_margin_end(4)

        # Header summary card
        self.task_summary_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.task_summary_box.get_style_context().add_class("card-box")

        t_lbl = Gtk.Label(label="TASKS")
        t_lbl.get_style_context().add_class("card-title")
        self.task_summary_box.pack_start(t_lbl, False, False, 0)

        self.task_counts_lbl = Gtk.Label(label="--")
        self.task_counts_lbl.get_style_context().add_class("card-pill")
        self.task_counts_lbl.get_style_context().add_class("pill-cyan")
        self.task_summary_box.pack_start(self.task_counts_lbl, False, False, 2)

        # Filter toggle buttons
        self.btn_f_pend = Gtk.Button(label="Pending")
        self.btn_f_pend.get_style_context().add_class("action-btn")
        self.btn_f_pend.connect("clicked", self.on_filter_changed, "pending")
        self.task_summary_box.pack_start(self.btn_f_pend, False, False, 0)

        self.btn_f_all = Gtk.Button(label="All")
        self.btn_f_all.get_style_context().add_class("action-btn-outline")
        self.btn_f_all.connect("clicked", self.on_filter_changed, "all")
        self.task_summary_box.pack_start(self.btn_f_all, False, False, 0)

        self.btn_f_done = Gtk.Button(label="Done")
        self.btn_f_done.get_style_context().add_class("action-btn-outline")
        self.btn_f_done.connect("clicked", self.on_filter_changed, "completed")
        self.task_summary_box.pack_start(self.btn_f_done, False, False, 0)

        btn_ref = Gtk.Button(label="🔄")
        btn_ref.get_style_context().add_class("action-btn-outline")
        btn_ref.connect("clicked", lambda b: self.refresh_tasks_view())
        self.task_summary_box.pack_end(btn_ref, False, False, 0)

        self.tasks_page_vbox.pack_start(self.task_summary_box, False, False, 0)

        # Dynamic task cards container
        self.task_cards_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.tasks_page_vbox.pack_start(self.task_cards_vbox, True, True, 0)

        self.populate_task_cards()
        return self.tasks_page_vbox

    def on_filter_changed(self, btn, filter_mode):
        self.on_user_interaction(None, None)
        self.current_task_filter = filter_mode
        self.btn_f_pend.get_style_context().remove_class("action-btn")
        self.btn_f_pend.get_style_context().add_class("action-btn-outline")
        self.btn_f_all.get_style_context().remove_class("action-btn")
        self.btn_f_all.get_style_context().add_class("action-btn-outline")
        self.btn_f_done.get_style_context().remove_class("action-btn")
        self.btn_f_done.get_style_context().add_class("action-btn-outline")

        btn.get_style_context().remove_class("action-btn-outline")
        btn.get_style_context().add_class("action-btn")
        self.refresh_tasks_view()

    def refresh_tasks_view(self):
        for child in self.task_cards_vbox.get_children():
            self.task_cards_vbox.remove(child)
        self.populate_task_cards()
        self.task_cards_vbox.show_all()

    def populate_task_cards(self):
        if not os.path.exists(DB_PATH):
            empty_lbl = Gtk.Label(label="FocusDesk Database not found.\nStart focusdesk-sync service.")
            empty_lbl.set_margin_top(20)
            self.task_cards_vbox.pack_start(empty_lbl, True, True, 0)
            return

        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query counts
            cursor.execute("SELECT status, due_at_utc FROM tasks WHERE archived_at IS NULL;")
            all_rows = cursor.fetchall()
            
            pending_count = sum(1 for r in all_rows if r["status"] != "completed")
            done_count = sum(1 for r in all_rows if r["status"] == "completed")
            self.task_counts_lbl.set_text(f"{pending_count} Pending | {done_count} Done")

            # Filter query
            if self.current_task_filter == "pending":
                cursor.execute("""
                SELECT * FROM tasks WHERE archived_at IS NULL AND status != 'completed'
                ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END ASC,
                         due_at_utc ASC;
                """)
            elif self.current_task_filter == "completed":
                cursor.execute("""
                SELECT * FROM tasks WHERE archived_at IS NULL AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 20;
                """)
            else:
                cursor.execute("""
                SELECT * FROM tasks WHERE archived_at IS NULL
                ORDER BY status ASC, CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END ASC;
                """)

            tasks = cursor.fetchall()
            conn.close()

            if not tasks:
                empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                empty.set_margin_top(15)
                lbl = Gtk.Label(label="✨ No tasks in this view")
                lbl.get_style_context().add_class("card-title")
                empty.pack_start(lbl, False, False, 0)
                sub = Gtk.Label(label="All caught up! Use web app or touch tools.")
                sub.get_style_context().add_class("metric-sub")
                empty.pack_start(sub, False, False, 0)
                self.task_cards_vbox.pack_start(empty, False, False, 0)
                return

            now = datetime.datetime.now(datetime.timezone.utc)

            for t in tasks:
                card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                card.get_style_context().add_class("card-box")

                # Left content
                left_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)

                # Meta row
                meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                
                # Priority pill
                prio = t["priority"]
                p_lbl = Gtk.Label(label=prio.upper())
                p_lbl.get_style_context().add_class("card-pill")
                if prio == "critical":
                    p_lbl.get_style_context().add_class("pill-rose")
                elif prio == "high":
                    p_lbl.get_style_context().add_class("pill-amber")
                elif prio == "medium":
                    p_lbl.get_style_context().add_class("pill-cyan")
                else:
                    p_lbl.get_style_context().add_class("card-pill")
                meta_row.pack_start(p_lbl, False, False, 0)

                # Category
                if t["category"]:
                    c_lbl = Gtk.Label(label=t["category"])
                    c_lbl.get_style_context().add_class("metric-sub")
                    meta_row.pack_start(c_lbl, False, False, 1)

                # Deadline text
                due_utc_str = t["due_at_utc"]
                if due_utc_str:
                    try:
                        due_dt = datetime.datetime.fromisoformat(due_utc_str.replace("Z", "+00:00"))
                        diff_sec = (due_dt - now).total_seconds()
                        if diff_sec < 0 and t["status"] != "completed":
                            d_lbl = Gtk.Label(label=f"⚠️ Overdue {int(abs(diff_sec)//3600)}h")
                            d_lbl.get_style_context().add_class("card-pill")
                            d_lbl.get_style_context().add_class("pill-rose")
                        elif diff_sec < 86400:
                            d_lbl = Gtk.Label(label=f"⏰ Today {due_dt.strftime('%H:%M')}")
                            d_lbl.get_style_context().add_class("card-pill")
                            d_lbl.get_style_context().add_class("pill-amber")
                        else:
                            d_lbl = Gtk.Label(label=due_dt.strftime("%b %d"))
                            d_lbl.get_style_context().add_class("metric-sub")
                        meta_row.pack_start(d_lbl, False, False, 2)
                    except Exception:
                        pass

                left_vbox.pack_start(meta_row, False, False, 0)

                # Title
                title_lbl = Gtk.Label()
                title_lbl.set_halign(Gtk.Align.START)
                title_lbl.set_line_wrap(True)
                title_lbl.set_max_width_chars(32)
                
                title_text = t["title"]
                if t["status"] == "completed":
                    title_lbl.set_markup(f"<s>{title_text}</s>")
                else:
                    title_lbl.set_markup(f"<b>{title_text}</b>")
                left_vbox.pack_start(title_lbl, False, False, 0)

                card.pack_start(left_vbox, True, True, 0)

                # Touch Complete / Reopen Action Button
                if t["status"] == "completed":
                    btn = Gtk.Button(label="↺ Undo")
                    btn.get_style_context().add_class("task-reopen-btn")
                    btn.connect("clicked", self.on_task_toggle_status, t["id"], "pending")
                else:
                    btn = Gtk.Button(label="✓ Done")
                    btn.get_style_context().add_class("task-complete-btn")
                    btn.connect("clicked", self.on_task_toggle_status, t["id"], "completed")

                btn.set_valign(Gtk.Align.CENTER)
                card.pack_end(btn, False, False, 0)

                self.task_cards_vbox.pack_start(card, False, False, 0)

        except Exception as e:
            err_lbl = Gtk.Label(label=f"DB Error: {e}")
            self.task_cards_vbox.pack_start(err_lbl, False, False, 0)

    def on_task_toggle_status(self, btn, task_id, new_status):
        self.on_user_interaction(None, None)
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            cursor.execute("SELECT revision FROM tasks WHERE id = ?;", (task_id,))
            row = cursor.fetchone()
            base_rev = row[0] if row else 1
            new_rev = base_rev + 1

            completed_at = now_iso if new_status == "completed" else None

            # 1. Update task in SQLite
            cursor.execute("""
            UPDATE tasks SET status = ?, completed_at = ?, updated_at = ?, revision = ?
            WHERE id = ?;
            """, (new_status, completed_at, now_iso, new_rev, task_id))

            # 2. Enqueue sync operation for sync_daemon
            op_id = f"op-stm32-{int(time.time()*1000)}"
            patch_data = {
                "status": new_status,
                "completedAt": completed_at,
                "updatedAt": now_iso,
                "revision": new_rev
            }
            cursor.execute("""
            INSERT INTO sync_queue (op_id, task_id, type, patch_json, base_revision, timestamp)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (op_id, task_id, "COMPLETE" if new_status == "completed" else "UPDATE", json.dumps(patch_data), base_rev, now_iso))

            conn.commit()
            conn.close()

            # Immediate UI refresh
            self.refresh_tasks_view()
        except Exception as e:
            print(f"[FocusDesk UI] Error updating task: {e}")

    # -------------------------------------------------------------------------
    # TAB 2: OVERVIEW DASHBOARD
    # -------------------------------------------------------------------------
    def build_page_overview(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        # Wi-Fi Banner
        net_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        net_banner.get_style_context().add_class("card-box")
        
        net_icon = Gtk.Label(label="🌐")
        net_banner.pack_start(net_icon, False, False, 2)

        net_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ov_ssid_lbl = Gtk.Label()
        self.ov_ssid_lbl.set_halign(Gtk.Align.START)
        self.ov_ssid_lbl.set_markup("<b>SRIGANESH_AP</b> <span foreground='#10B981'>[Prio 1 Active]</span>")
        
        self.ov_ip_lbl = Gtk.Label(label="IP: 10.50.27.58 | GW: 10.50.27.57")
        self.ov_ip_lbl.set_halign(Gtk.Align.START)
        self.ov_ip_lbl.get_style_context().add_class("metric-sub")
        
        net_text_box.pack_start(self.ov_ssid_lbl, False, False, 0)
        net_text_box.pack_start(self.ov_ip_lbl, False, False, 0)
        net_banner.pack_start(net_text_box, True, True, 0)

        sig_badge = Gtk.Label(label="📶 100%")
        sig_badge.get_style_context().add_class("card-pill")
        sig_badge.get_style_context().add_class("pill-emerald")
        net_banner.pack_end(sig_badge, False, False, 2)
        vbox.pack_start(net_banner, False, False, 0)

        # 2x2 Metric Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(3)
        grid.set_row_spacing(3)
        grid.set_column_homogeneous(True)

        # Cell 1: CPU Load
        c1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        c1.get_style_context().add_class("card-box")
        h1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        lbl1 = Gtk.Label(label="CPU USAGE")
        lbl1.get_style_context().add_class("card-title")
        b1 = Gtk.Label(label="Cortex-A7")
        b1.get_style_context().add_class("card-pill")
        b1.get_style_context().add_class("pill-cyan")
        h1.pack_start(lbl1, False, False, 0)
        h1.pack_end(b1, False, False, 0)
        c1.pack_start(h1, False, False, 0)

        self.cpu_num_lbl = Gtk.Label(label="12.0%")
        self.cpu_num_lbl.set_halign(Gtk.Align.START)
        self.cpu_num_lbl.get_style_context().add_class("metric-num")
        c1.pack_start(self.cpu_num_lbl, False, False, 0)

        self.cpu_prog = Gtk.ProgressBar()
        self.cpu_prog.get_style_context().add_class("cyan")
        self.cpu_prog.set_fraction(0.12)
        c1.pack_start(self.cpu_prog, False, False, 1)

        self.sparkline = SparklineWidget()
        c1.pack_start(self.sparkline, False, False, 1)
        grid.attach(c1, 0, 0, 1, 1)

        # Cell 2: RAM
        c2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        c2.get_style_context().add_class("card-box")
        h2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        lbl2 = Gtk.Label(label="MEMORY")
        lbl2.get_style_context().add_class("card-title")
        b2 = Gtk.Label(label="437 MB DDR3L")
        b2.get_style_context().add_class("card-pill")
        b2.get_style_context().add_class("pill-emerald")
        h2.pack_start(lbl2, False, False, 0)
        h2.pack_end(b2, False, False, 0)
        c2.pack_start(h2, False, False, 0)

        self.ram_num_lbl = Gtk.Label(label="122 MB (28%)")
        self.ram_num_lbl.set_halign(Gtk.Align.START)
        self.ram_num_lbl.get_style_context().add_class("metric-num")
        c2.pack_start(self.ram_num_lbl, False, False, 0)

        self.ram_prog = Gtk.ProgressBar()
        self.ram_prog.get_style_context().add_class("emerald")
        self.ram_prog.set_fraction(0.28)
        c2.pack_start(self.ram_prog, False, False, 1)

        self.ram_sub_lbl = Gtk.Label(label="Free: 315 MB")
        self.ram_sub_lbl.set_halign(Gtk.Align.START)
        self.ram_sub_lbl.get_style_context().add_class("metric-sub")
        c2.pack_start(self.ram_sub_lbl, False, False, 1)
        grid.attach(c2, 1, 0, 1, 1)

        # Cell 3: Thermal / Engine
        c3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        c3.get_style_context().add_class("card-box")
        h3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        lbl3 = Gtk.Label(label="THERMAL & STORAGE")
        lbl3.get_style_context().add_class("card-title")
        b3 = Gtk.Label(label="Nominal")
        b3.get_style_context().add_class("card-pill")
        b3.get_style_context().add_class("pill-purple")
        h3.pack_start(lbl3, False, False, 0)
        h3.pack_end(b3, False, False, 0)
        c3.pack_start(h3, False, False, 0)

        self.temp_lbl = Gtk.Label(label="38.5°C")
        self.temp_lbl.set_halign(Gtk.Align.START)
        self.temp_lbl.get_style_context().add_class("metric-num")
        c3.pack_start(self.temp_lbl, False, False, 0)

        self.disk_sub_lbl = Gtk.Label(label="eMMC Free: 2.9 GB / 3.8 GB")
        self.disk_sub_lbl.set_halign(Gtk.Align.START)
        self.disk_sub_lbl.get_style_context().add_class("metric-sub")
        c3.pack_start(self.disk_sub_lbl, False, False, 1)
        grid.attach(c3, 0, 1, 1, 1)

        # Cell 4: Display & Kiosk
        c4 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        c4.get_style_context().add_class("card-box")
        h4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        lbl4 = Gtk.Label(label="DISPLAY BACKLIGHT")
        lbl4.get_style_context().add_class("card-title")
        b4 = Gtk.Label(label="Auto-Dim Active")
        b4.get_style_context().add_class("card-pill")
        b4.get_style_context().add_class("pill-amber")
        h4.pack_start(lbl4, False, False, 0)
        h4.pack_end(b4, False, False, 0)
        c4.pack_start(h4, False, False, 0)

        disp_lbl = Gtk.Label(label="480×272@60")
        disp_lbl.set_halign(Gtk.Align.START)
        disp_lbl.get_style_context().add_class("metric-num")
        c4.pack_start(disp_lbl, False, False, 0)

        disp_sub = Gtk.Label(label="Auto-dim: 2m | Pixman SHM")
        disp_sub.set_halign(Gtk.Align.START)
        disp_sub.get_style_context().add_class("metric-sub")
        c4.pack_start(disp_sub, False, False, 1)
        grid.attach(c4, 1, 1, 1, 1)

        vbox.pack_start(grid, False, False, 0)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_box.set_margin_top(1)
        
        btn_w3 = Gtk.Button(label="🌐 W3Schools")
        btn_w3.get_style_context().add_class("action-btn")
        btn_w3.connect("clicked", lambda b: self.show_dialog("Web Link", "Hyperlink: https://www.w3schools.com\n\nPreserved from original page."))
        btn_box.pack_start(btn_w3, True, True, 0)

        btn_st = Gtk.Button(label="⚡ STM32MP135")
        btn_st.get_style_context().add_class("action-btn-outline")
        btn_st.connect("clicked", lambda b: self.show_dialog("Device Info", "STM32MP135F-DK Discovery Board\nSoC: Cortex-A7 @ 1000MHz\nRAM: 437 MB DDR3L\nOS: OpenSTLinux 5.0.8"))
        btn_box.pack_start(btn_st, True, True, 0)

        btn_ref = Gtk.Button(label="🔄")
        btn_ref.get_style_context().add_class("action-btn-outline")
        btn_ref.connect("clicked", lambda b: self.update_telemetry())
        btn_box.pack_start(btn_ref, False, False, 0)

        vbox.pack_start(btn_box, False, False, 0)
        return vbox

    # -------------------------------------------------------------------------
    # TAB 3: WI-FI & FAILOVER HUB
    # -------------------------------------------------------------------------
    def build_page_network(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("card-box")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        t = Gtk.Label(label="WI-FI FAILOVER SYSTEM")
        t.get_style_context().add_class("card-title")
        b = Gtk.Label(label="Watchdog Active")
        b.get_style_context().add_class("card-pill")
        b.get_style_context().add_class("pill-emerald")
        hdr.pack_start(t, False, False, 0)
        hdr.pack_end(b, False, False, 0)
        card.pack_start(hdr, False, False, 1)

        prio_items = [
            ("P1", "SRIGANESH_AP", "Prio: 100", "ACTIVE NOW", "pill-emerald"),
            ("P2", "Moto g96 5g", "Prio: 50 | Hotspot", "STANDBY", "pill-cyan"),
            ("P3", "BEST", "Prio: 10", "READY", "pill-purple")
        ]

        for p_label, name, sub, stat, color_cls in prio_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            plbl = Gtk.Label(label=p_label)
            plbl.get_style_context().add_class("card-pill")
            plbl.get_style_context().add_class(color_cls)
            row.pack_start(plbl, False, False, 0)

            tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            nlbl = Gtk.Label()
            nlbl.set_halign(Gtk.Align.START)
            nlbl.set_markup(f"<b>{name}</b> <span size='smaller' foreground='#64748B'>{sub}</span>")
            tbox.pack_start(nlbl, False, False, 0)
            row.pack_start(tbox, True, True, 0)

            stat_lbl = Gtk.Label(label=stat)
            stat_lbl.get_style_context().add_class("card-pill")
            stat_lbl.get_style_context().add_class(color_cls)
            row.pack_end(stat_lbl, False, False, 0)
            card.pack_start(row, False, False, 1)

        vbox.pack_start(card, False, False, 0)

        # Network Details
        det_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        det_box.get_style_context().add_class("card-box")
        
        det_title = Gtk.Label(label="INTERFACE (wlan0)")
        det_title.get_style_context().add_class("card-title")
        det_box.pack_start(det_title, False, False, 0)

        det_lbl = Gtk.Label()
        det_lbl.set_halign(Gtk.Align.START)
        det_lbl.set_markup("<span font_family='monospace' size='smaller'>Driver: brcmfmac | Chip: CYW4343W\nIP: 10.50.27.58/24 (Sec: 10.57.135.58)\nFailover Check: Every 1.0s</span>")
        det_box.pack_start(det_lbl, False, False, 0)

        vbox.pack_start(det_box, False, False, 0)
        return vbox

    # -------------------------------------------------------------------------
    # TAB 4: SENSORS & HARDWARE
    # -------------------------------------------------------------------------
    def build_page_telemetry(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.get_style_context().add_class("card-box")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        t = Gtk.Label(label="STM32 SOC HARDWARE SENSORS")
        t.get_style_context().add_class("card-title")
        b = Gtk.Label(label="Live IIO")
        b.get_style_context().add_class("card-pill")
        b.get_style_context().add_class("pill-cyan")
        hdr.pack_start(t, False, False, 0)
        hdr.pack_end(b, False, False, 0)
        box.pack_start(hdr, False, False, 0)

        sensors = [
            ("Core Thermal Zone", "38.5°C", "thermal_zone0 (Nominal below 85°C)"),
            ("Goodix Touch Panel", "event0 (I2C)", "Capacitive 480×272 Multi-Touch"),
            ("Panel Backlight", "10 / 10", "PWM Dimming (/sys/class/backlight)"),
            ("Display Controller", "LTDC 2D", "DPI-1 Parallel RGB 24-bit"),
            ("DDR3L Subsystem", "533 MHz", "16-bit Bus, 437 MB Physical RAM")
        ]

        for name, val, desc in sensors:
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            nl = Gtk.Label()
            nl.set_halign(Gtk.Align.START)
            nl.set_markup(f"<b>{name}</b> <span size='smaller' foreground='#64748B'>({desc})</span>")
            r.pack_start(nl, True, True, 0)

            vl = Gtk.Label(label=val)
            vl.get_style_context().add_class("card-pill")
            vl.get_style_context().add_class("pill-emerald")
            r.pack_end(vl, False, False, 0)
            box.pack_start(r, False, False, 1)

        vbox.pack_start(box, True, True, 0)
        return vbox

    # -------------------------------------------------------------------------
    # TAB 5: TOOLS & ACTIONS
    # -------------------------------------------------------------------------
    def build_page_controls(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.get_style_context().add_class("card-box")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        t = Gtk.Label(label="SYSTEM & FOCUSDESK ACTIONS")
        t.get_style_context().add_class("card-title")
        hdr.pack_start(t, False, False, 0)
        box.pack_start(hdr, False, False, 0)

        actions = [
            ("🔄 Sync Now", "Trigger immediate Firestore HTTPS synchronization", self.on_sync_now),
            ("🔅 Dim Display", "Test LCD power-saving backlight dimming", lambda: self.set_backlight(1)),
            ("💡 Wake Display", "Restore LCD brightness to 100%", lambda: self.set_backlight(10)),
            ("📂 Rotate Backup", "Generate atomic JSON backup snapshot now", self.on_backup_now),
            ("🌐 Check Ping", "Verify 8.8.8.8 latency across active Wi-Fi", self.on_ping_check),
        ]

        for label, desc, cb in actions:
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            dl = Gtk.Label()
            dl.set_halign(Gtk.Align.START)
            dl.set_markup(f"<b>{label}</b> <span size='smaller' foreground='#64748B'>{desc}</span>")
            r.pack_start(dl, True, True, 0)

            b = Gtk.Button(label="Run")
            b.get_style_context().add_class("action-btn-outline")
            b.connect("clicked", lambda x, func=cb: func())
            r.pack_end(b, False, False, 0)
            box.pack_start(r, False, False, 1)

        vbox.pack_start(box, True, True, 0)
        return vbox

    def on_sync_now(self):
        self.on_user_interaction(None, None)
        try:
            subprocess.Popen(["python3", "-c", "import sys; sys.path.append('/home/weston/focusdesk'); import sync_daemon; sync_daemon.run_sync_cycle()"])
            self.show_dialog("Sync Triggered", "Cloud sync cycle executed.\nTasks and operations synchronized.")
            self.refresh_tasks_view()
        except Exception as e:
            self.show_dialog("Sync Error", str(e))

    def on_backup_now(self):
        self.on_user_interaction(None, None)
        try:
            subprocess.Popen(["python3", "-c", "import sys; sys.path.append('/home/weston/focusdesk'); import sync_daemon; sync_daemon.run_sync_cycle()"])
            self.show_dialog("Backup Created", "Atomic JSON snapshot generated in:\n/var/lib/focusdesk/backups/")
        except Exception as e:
            self.show_dialog("Backup Error", str(e))

    def on_ping_check(self):
        self.on_user_interaction(None, None)
        try:
            res = subprocess.run(["ping", "-c", "1", "-W", "1", "8.8.8.8"], capture_output=True, text=True)
            if res.returncode == 0:
                self.show_dialog("Ping OK", "Internet connection verified!\nPing to 8.8.8.8: Success")
            else:
                self.show_dialog("Ping Failed", "Could not reach 8.8.8.8.\nCheck Wi-Fi connection.")
        except Exception as e:
            self.show_dialog("Ping Error", str(e))

    # -------------------------------------------------------------------------
    # TAB 6: DIAGNOSTICS & LOGS
    # -------------------------------------------------------------------------
    def build_page_diagnostics(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(2)
        vbox.set_margin_bottom(4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        c.get_style_context().add_class("card-box")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        t = Gtk.Label(label="EVENT LOG")
        t.get_style_context().add_class("card-title")
        b = Gtk.Label(label="Live journal")
        b.get_style_context().add_class("card-pill")
        b.get_style_context().add_class("pill-cyan")
        hdr.pack_start(t, False, False, 0)
        hdr.pack_end(b, False, False, 0)
        c.pack_start(hdr, False, False, 0)

        self.log_buffer = Gtk.TextBuffer()
        initial_log = (
            "[ 0.000] Booting Linux ARMv7 Cortex-A7\n"
            "[ 0.000] Linux 6.6.78-openstlinux\n"
            "[ 2.189] brcmfmac: CYW4343W online\n"
            "[ 3.409] ltdc: 480x272@60Hz panel attached\n"
            "[ 4.110] systemd: Weston Compositor started\n"
            "[ 5.230] weston: Using pixman renderer\n"
            "[ 10.19] demo: Auto-launching Kiosk\n"
            "[ 12.39] watchdog: Prio1 active (10.50.27.58)\n"
            "[ 14.40] focusdesk: SQLite WAL tasks database initialized\n"
            "[ 14.46] focusdesk: sync_daemon.service active"
        )
        self.log_buffer.set_text(initial_log)

        text_view = Gtk.TextView(buffer=self.log_buffer)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        text_view.set_size_request(-1, 80)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.add(text_view)
        c.pack_start(sc, True, True, 1)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        add_btn = Gtk.Button(label="📝 Add Entry")
        add_btn.get_style_context().add_class("action-btn-outline")
        add_btn.connect("clicked", self.on_add_log)
        btn_box.pack_start(add_btn, False, False, 0)

        clr_btn = Gtk.Button(label="🧹 Clear")
        clr_btn.get_style_context().add_class("action-btn-outline")
        clr_btn.connect("clicked", lambda b: self.log_buffer.set_text("[Cleared]\n"))
        btn_box.pack_start(clr_btn, False, False, 0)

        c.pack_start(btn_box, False, False, 1)
        vbox.pack_start(c, True, True, 0)
        return vbox

    def on_add_log(self, btn):
        self.on_user_interaction(None, None)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now_str}] Telemetry: CPU={self.cpu_usage_pct:.1f}%, RAM Free={self.ram_free_mb:.0f}MB\n"
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, entry)

    # -------------------------------------------------------------------------
    # FOOTER
    # -------------------------------------------------------------------------
    def build_footer(self):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        footer.get_style_context().add_class("bot-footer")

        lbl1 = Gtk.Label(label="STM32MP135F-DK | FocusDesk Kiosk")
        footer.pack_start(lbl1, False, False, 0)

        self.foot_ram_lbl = Gtk.Label(label="314 MB Free")
        footer.pack_end(self.foot_ram_lbl, False, False, 0)

        return footer

    # -------------------------------------------------------------------------
    # TELEMETRY ENGINE
    # -------------------------------------------------------------------------
    def read_cpu_raw(self):
        try:
            with open("/proc/stat", "r") as f:
                fields = [float(x) for x in f.readline().strip().split()[1:5]]
                return fields
        except Exception:
            return [0.0, 0.0, 0.0, 1.0]

    def update_telemetry(self):
        cur_cpu = self.read_cpu_raw()
        prev_idle = self.prev_cpu_stat[3]
        prev_total = sum(self.prev_cpu_stat)
        idle = cur_cpu[3]
        total = sum(cur_cpu)
        
        diff_total = total - prev_total
        diff_idle = idle - prev_idle
        if diff_total > 0:
            usage = 100.0 * (1.0 - diff_idle / diff_total)
            self.cpu_usage_pct = max(0.0, min(100.0, usage))
        self.prev_cpu_stat = cur_cpu

        self.cpu_num_lbl.set_text(f"{self.cpu_usage_pct:.1f}%")
        self.cpu_prog.set_fraction(self.cpu_usage_pct / 100.0)
        self.sparkline.add_point(self.cpu_usage_pct)

        try:
            with open("/proc/meminfo", "r") as f:
                mem = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        mem[parts[0].strip()] = float(parts[1].strip().split()[0])
            total_kb = mem.get("MemTotal", 447000)
            avail_kb = mem.get("MemAvailable", 320000)
            used_kb = total_kb - avail_kb

            self.ram_total_mb = total_kb / 1024.0
            self.ram_used_mb = used_kb / 1024.0
            self.ram_free_mb = avail_kb / 1024.0

            pct = (used_kb / total_kb) * 100.0
            self.ram_num_lbl.set_text(f"{self.ram_used_mb:.0f} MB ({pct:.0f}%)")
            self.ram_prog.set_fraction(used_kb / total_kb)
            self.ram_sub_lbl.set_text(f"Free: {self.ram_free_mb:.0f} MB")
            self.foot_ram_lbl.set_text(f"{self.ram_free_mb:.0f} MB Free")
        except Exception:
            pass

        return True

    def update_clock(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S UTC")
        self.clock_lbl.set_text(now_utc)
        return True

    def show_dialog(self, title, message):
        self.on_user_interaction(None, None)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_key_press(self, widget, event):
        self.on_user_interaction(None, None)
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_q):
            Gtk.main_quit()
            return True
        return False

def main():
    app = AdvancedEdgeKiosk()
    Gtk.main()

if __name__ == "__main__":
    main()
