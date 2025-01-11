from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton, 
                            QWidget, QHBoxLayout, QVBoxLayout, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint, QSize
from PyQt6.QtGui import QClipboard, QIcon, QAction
import keyboard
import sys
import json
import os

NOTES_FILE = "sticky_notes.json"

class HotkeyHandler(QObject):
    note_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        keyboard.add_hotkey('ctrl+n', self.trigger_note)

    def trigger_note(self):
        self.note_requested.emit()

class StickyNotesApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.sticky_notes_app = self
        # Add this to prevent app closure when last window closes
        self.app.setQuitOnLastWindowClosed(False)  # This is the key fix!
        
        # Create hotkey handler
        self.hotkey_handler = HotkeyHandler()
        self.hotkey_handler.note_requested.connect(self.create_note_safe)
        
        # Create system tray icon
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.app.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxInformation))
        
        # Create tray menu
        tray_menu = QMenu()
        new_note_action = QAction("New Note", self.app)
        new_note_action.triggered.connect(self.create_note_safe)
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(new_note_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.show()

        # Load saved notes
        self.load_notes()
        
        # Show initial tray message
        self.tray.showMessage(
            "Sticky Notes Running",
            "Press Ctrl+N to create a new note!",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        

    def create_note_safe(self, text="", pos=None, size=None):
        note = StickyNote(text)
        if pos:
            note.move(pos.x(), pos.y())
        if size:
            note.resize(size.width(), size.height())
    
    def load_notes(self):
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r') as f:
                notes_data = json.load(f)
                for note_data in notes_data:
                    self.create_note_safe(
                        text=note_data['text'],
                        pos=QPoint(note_data['x'], note_data['y']),
                        size=QSize(note_data['width'], note_data['height'])
                    )

    def quit_app(self):
        self.save_notes()
        self.app.quit()

    def save_notes(self):
        notes_data = []
        for note in StickyNote.notes:
            notes_data.append({
                'text': note.text.toPlainText(),
                'x': note.x(),
                'y': note.y(),
                'width': note.width(),
                'height': note.height()
            })
        print(f"Saving {len(notes_data)} notes")  # Debug print
        with open(NOTES_FILE, 'w') as f:
            json.dump(notes_data, f)
        
    def run(self):
        return self.app.exec()

class StickyNote(QMainWindow):
    notes = []  # Class variable to track all notes

    def __init__(self, initial_text=""):
        super().__init__()
        StickyNote.notes.append(self)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )

        # Enable resizing
        self.setMinimumSize(100, 100)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        toolbar.setStyleSheet("background-color: rgba(225, 193, 59, 0.95);")
        toolbar.setFixedHeight(40)
        
        new_btn = QPushButton("+", toolbar)
        new_btn.setFixedSize(30, 30)
        new_btn.clicked.connect(self.create_new_note)
        
        close_btn = QPushButton("×", toolbar)
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.delete_note)
        
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: black;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 15px;
            }
        """
        
        new_btn.setStyleSheet(button_style)
        close_btn.setStyleSheet(button_style)
        
        toolbar_layout.addWidget(new_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(close_btn)
        
        layout.addWidget(toolbar)
        
        # Text area
        self.text = QTextEdit()
        self.text.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: black;
                font-size: 12px;
                padding: 5px;
            }
        """)
        self.text.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text)
        
        # Set initial text if provided
        if initial_text:
            self.text.setPlainText(initial_text)
        
        # Base window styling
        self.default_style = "background-color: rgba(255, 223, 89, 0.95);"
        self.setStyleSheet(f"QMainWindow {{ {self.default_style} }}")
        
        self.resize(200, 200)
        
        # For dragging and resizing
        self._dragging = False
        self._resizing = False
        self._start_pos = None
        self._start_size = None
        self.resize_margin = 25

        # Show the note
        self.show()

    def on_text_changed(self):
        # Fix the reference to save_notes
        app = QApplication.instance()
        if hasattr(app, 'sticky_notes_app'):
            app.sticky_notes_app.save_notes()


    def copy_with_feedback(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text.toPlainText())
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(50, 50, 50, 0.95);
            }
        """)
        
        QTimer.singleShot(200, lambda: self.setStyleSheet(
            f"QMainWindow {{ {self.default_style} }}"
        ))

    @classmethod
    def create_new_note(cls):
        note = cls()
        if len(cls.notes) > 1:
            current_pos = cls.notes[-2].pos()
            note.move(current_pos.x() + 20, current_pos.y() + 20)
    
    def delete_note(self):
        StickyNote.notes.remove(self)
        # Save before closing
        app = QApplication.instance()
        if hasattr(app, 'sticky_notes_app'):
            app.sticky_notes_app.save_notes()
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.copy_with_feedback()
            else:
                pos = event.position()
                if (pos.x() > self.width() - self.resize_margin and 
                    pos.y() > self.height() - self.resize_margin and
                    pos.y() > 40):
                    self._resizing = True
                    self._start_pos = pos
                    self._start_size = self.size()
                else:
                    self._dragging = True
                    self._start_pos = pos

    def mouseMoveEvent(self, event):
        if self._resizing and self._start_pos is not None:
            delta = event.position() - self._start_pos
            new_width = max(self._start_size.width() + delta.x(), self.minimumWidth())
            new_height = max(self._start_size.height() + delta.y(), self.minimumHeight())
            self.resize(int(new_width), int(new_height))
        elif self._dragging and self._start_pos is not None:
            delta = event.position() - self._start_pos
            self.move(self.x() + int(delta.x()), self.y() + int(delta.y()))

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._start_pos = None
        self._start_size = None

    def enterEvent(self, event):
        pos = event.position()
        if (pos.x() > self.width() - self.resize_margin and 
            pos.y() > self.height() - self.resize_margin and
            pos.y() > 40):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)

if __name__ == '__main__':
    sticky_app = StickyNotesApp()
    # Removed the automatic note creation
    sys.exit(sticky_app.run())