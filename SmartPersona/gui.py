from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QPlainTextEdit, QLineEdit, QFileDialog, QMessageBox, QTabWidget,
    QGroupBox, QProgressBar, QScrollArea, QButtonGroup, QCheckBox, QRadioButton,
    QComboBox, QFormLayout, QDialog, QDialogButtonBox, QFrame,
    QListWidget, QListWidgetItem,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QFont
import sys
import os
import json
from brain import SmartPersonaBrain, MEMORY_TYPES
from persona import SmartPersona

# Theme (user-centric, consistent)
INSTRUCTION_BG = "#f5f5f5"
PRIMARY_GREEN = "#4CAF50"
PRIMARY_BLUE = "#2196F3"
STRIP_BG = "#e8eaf6"
HINT_COLOR = "#666"
BORDER_RADIUS = "5px"

# Reference size for responsive scaling (design base)
REF_WIDTH = 900
REF_HEIGHT = 700
MIN_SCALE = 0.65
MAX_SCALE = 1.4
MIN_WINDOW_WIDTH = 560
MIN_WINDOW_HEIGHT = 420


class TeachingThread(QThread):
    """Thread for processing message history without blocking UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        brain,
        message_history,
        format="auto",
        auto_reflect=True,
        store_conversation_summary=True,
    ):
        super().__init__()
        self.brain = brain
        self.message_history = message_history
        self.format = format
        self.auto_reflect = auto_reflect
        self.store_conversation_summary = store_conversation_summary

    def run(self):
        try:
            result = self.brain.teach_from_message_history(
                self.message_history,
                format=self.format,
                auto_reflect=self.auto_reflect,
                store_conversation_summary=self.store_conversation_summary,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ReplySuggestionThread(QThread):
    """Thread for getting reply suggestion from brain without blocking UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, chat_history, user_prompt=None, format="auto"):
        super().__init__()
        self.brain = brain
        self.chat_history = chat_history
        self.user_prompt = user_prompt
        self.format = format

    def run(self):
        try:
            result = self.brain.suggest_reply(
                self.chat_history,
                user_prompt=self.user_prompt,
                format=self.format,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ClassifyToneThread(QThread):
    """Thread for classifying reply tone (logical vs emotional) without blocking UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, reply):
        super().__init__()
        self.brain = brain
        self.reply = reply or ""

    def run(self):
        try:
            result = self.brain.classify_reply_tone(self.reply)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AdjustToneThread(QThread):
    """Thread for adjusting reply tone (more logical / more emotional) without blocking UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, reply, chat_history, direction):
        super().__init__()
        self.brain = brain
        self.reply = reply or ""
        self.chat_history = chat_history
        self.direction = direction  # "more_logical" or "more_emotional"

    def run(self):
        try:
            result = self.brain.adjust_reply_tone(
                self.reply,
                chat_history=self.chat_history,
                direction=self.direction,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ActionsSuggestionThread(QThread):
    """Thread for getting top 5 actions for a situation from brain without blocking UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, situation_text, persona_name=None):
        super().__init__()
        self.brain = brain
        self.situation_text = situation_text
        self.persona_name = persona_name

    def run(self):
        try:
            result = self.brain.suggest_actions_for_situation(
                self.situation_text,
                persona_name=self.persona_name,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PersonaChatThread(QThread):
    """Thread for chatting as the learned user persona (memory-backed, not simulating contacts)."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, user_message, conversation_messages, persona_display_name):
        super().__init__()
        self.brain = brain
        self.user_message = user_message
        self.conversation_messages = conversation_messages
        self.persona_display_name = persona_display_name or "You"

    def run(self):
        try:
            result = self.brain.chat_learned_self(
                self.user_message,
                self.persona_display_name,
                conversation_messages=self.conversation_messages,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ModelPingThread(QThread):
    """Quick Ollama ping for the selected model without blocking the UI."""
    finished = pyqtSignal(dict)

    def __init__(self, brain, model_name):
        super().__init__()
        self.brain = brain
        self.model_name = model_name or ""

    def run(self):
        try:
            self.finished.emit(self.brain.ping_model(self.model_name))
        except Exception as e:
            self.finished.emit({"ok": False, "error": str(e)})


class RefreshMemoryThread(QThread):
    """Thread for tidying memory and getting clarification questions."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain):
        super().__init__()
        self.brain = brain

    def run(self):
        try:
            self.brain.tidy_memory()
            questions = self.brain.review_memories_for_clarification(memory_limit=50)
            self.finished.emit({"questions": questions})
        except Exception as e:
            self.error.emit(str(e))


class AddMemoryValidationThread(QThread):
    """Thread for AI validation of a proposed memory before adding."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, brain, content, mem_type, person=None, topic=None, situation=None, role=None):
        super().__init__()
        self.brain = brain
        self.content = content
        self.mem_type = mem_type
        self.person = person
        self.topic = topic
        self.situation = situation
        self.role = role

    def run(self):
        try:
            result = self.brain.validate_memory_entry(
                self.content,
                type=self.mem_type,
                person=self.person,
                topic=self.topic,
                situation=self.situation,
                role=self.role,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class LoaderGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_active = False

    def start(self):
        """Show the loading window/start the loader."""
        self.setWindowTitle("💡 SmartPersona — Loading...")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setGeometry(100, 100, 300, 200)
        self.is_active = True
        self.show()

    def end(self):
        """Hide and clean up the loader."""
        self.is_active = False
        self.close()
        # Optionally, additional cleanup code here
 

class SmartPersonaGUI(QWidget):
    def __init__(self, root=None, persona=None):
        super().__init__(root)
        self.persona = persona if persona is not None else SmartPersona()
        settings = QSettings("SmartPersona", "SmartPersona")
        saved_model = settings.value("ollamaModel", "", type=str)
        self.brain = SmartPersonaBrain(
            persist=True,
            model=saved_model if saved_model.strip() else None,
        )
        # Thread-handling/working state
        self.model_ping_thread = None
        self.teaching_thread = None
        self.reply_suggestion_thread = None
        self.classify_tone_thread = None
        self.adjust_tone_thread = None
        self.refresh_memory_thread = None
        self.add_memory_validation_thread = None
        self.persona_chat_thread = None
        # Other state
        self._last_reply_chat_payload = None
        self._last_reply_format = "auto"
        self._persona_chat_history = []
        self._persona_chat_pending_user = ""
        self.init_ui()

    def _update_identity_strip(self):
        if not hasattr(self, "identity_summary_label"):
            return
        n_mem = len(self.brain.get_memory())
        n_thoughts = len(self.brain.get_thoughts(limit=999))
        self.identity_summary_label.setText(f"{n_mem} memories · {n_thoughts} thoughts")

    def _save_ollama_model_settings(self):
        QSettings("SmartPersona", "SmartPersona").setValue("ollamaModel", self.brain.get_model())

    def _populate_model_combo(self):
        if not hasattr(self, "model_combo"):
            return
        current = self.brain.get_model()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for nm in self.brain.list_local_models():
            self.model_combo.addItem(nm)
        if current and self.model_combo.findText(current) < 0:
            # unique model, maybe user-typed
            self.model_combo.insertItem(0, current)
        self.model_combo.setCurrentText(current)
        self.model_combo.blockSignals(False)

    def _apply_model_from_ui(self):
        name = self.model_combo.currentText().strip()
        if not name:
            QMessageBox.information(self, "Choose a Model", "To get started, select or type in an AI model name (installed in Ollama).")
            return
        try:
            self.brain.set_model(name)
        except ValueError:
            QMessageBox.warning(self, "Model Error", "The model could not be set. Please check that the model name is available in Ollama.")
            return
        self._save_ollama_model_settings()
        self.model_status_label.setText("<span style='color:green;'>Saved!</span>")
        QTimer.singleShot(1800, lambda: self._clear_model_status_if_saved())

    def _clear_model_status_if_saved(self):
        if hasattr(self, "model_status_label") and self.model_status_label.text().lower().startswith("saved"):
            self.model_status_label.setText("")

    def _on_refresh_ollama_models(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._populate_model_combo()
            self.model_status_label.setText("")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_test_ollama_model(self):
        name = self.model_combo.currentText().strip()
        if not name:
            QMessageBox.information(
                self, "Test Model", 
                "Type a model name, then click Test to check if it works."
            )
            return
        if self.model_ping_thread and self.model_ping_thread.isRunning():
            return
        self.model_test_btn.setEnabled(False)
        self.model_status_label.setText("… Testing …")
        self.model_ping_thread = ModelPingThread(self.brain, name)
        self.model_ping_thread.finished.connect(self._on_model_ping_finished)
        self.model_ping_thread.start()

    def _on_model_ping_finished(self, result):
        self.model_test_btn.setEnabled(True)
        if result.get("ok"):
            self.model_status_label.setText("<span style='color:green;'>✔ OK</span>")
        else:
            err = result.get("error", "Unknown error")
            self.model_status_label.setText("<span style='color:red;'>✖ Fail</span>")
            QMessageBox.warning(self, "Ollama", err)

    def _copy_to_clipboard(self, text_widget, status_label):
        text = text_widget.toPlainText()
        if text:
            QApplication.instance().clipboard().setText(text)
            status_label.setText("<span style='color:green;'>Copied!</span>")
            QTimer.singleShot(1600, lambda: status_label.setText(""))

    def _dismiss_first_run_hint(self):
        settings = QSettings("SmartPersona", "SmartPersona")
        settings.setValue("firstRunHintSeen", True)
        self._first_run_hint_seen = True
        if hasattr(self, "_first_run_hint_frame") and self._first_run_hint_frame:
            self._first_run_hint_frame.setVisible(False)

    def _scale_factor(self):
        w, h = self.width(), self.height()
        sx = w / REF_WIDTH if REF_WIDTH else 1.0
        sy = h / REF_HEIGHT if REF_HEIGHT else 1.0
        scale = min(sx, sy)
        return max(MIN_SCALE, min(MAX_SCALE, scale))

    def _apply_responsive_scale(self):
        scale = self._scale_factor()
        base_pt = 12
        font_pt = max(10, min(19, int(base_pt * scale)))
        hint_pt = max(10, int(font_pt * 0.97))
        title_pt = max(12, int(font_pt * 1.23))
        app_font = QFont()
        app_font.setPointSize(font_pt)
        self.setFont(app_font)
        self.main_tabs.setFont(app_font)
        self.identity_name_label.setStyleSheet(f"font-weight: bold; font-size: {title_pt}pt;")
        self.identity_summary_label.setStyleSheet(f"color: {HINT_COLOR}; font-size: {hint_pt}pt;")
        if hasattr(self, "model_status_label"):
            self.model_status_label.setStyleSheet(f"color: {HINT_COLOR}; font-size: {hint_pt}pt;")
        strip_btn_pad = max(4, int(8 * scale))
        for btn in (
            getattr(self, "model_refresh_btn", None),
            getattr(self, "model_apply_btn", None),
            getattr(self, "model_test_btn", None),
        ):
            if btn:
                btn.setStyleSheet(f"font-size: {font_pt}pt; padding: {strip_btn_pad}px;")
        pad = max(8, int(12 * scale))
        if hasattr(self, "_strip_frame"):
            self._strip_frame.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f8fafb, stop:1 #e8eeff); "
                f"border: 1px solid #c4d6fe; border-radius: {BORDER_RADIUS}; padding: {pad}px;"
            )
        for label in (
            getattr(self, "results_copy_status", None),
            getattr(self, "reply_copy_status", None),
            getattr(self, "actions_copy_status", None),
            getattr(self, "add_memory_type_hint", None),
        ):
            if label:
                label.setStyleSheet(f"color: {HINT_COLOR}; font-size: {hint_pt}pt;")
        btn_pad = max(8, int(12 * scale))
        for btn, color in (
            (getattr(self, "teach_btn", None), PRIMARY_GREEN),
            (getattr(self, "get_reply_btn", None), PRIMARY_BLUE),
            (getattr(self, "get_actions_btn", None), PRIMARY_BLUE),
            (getattr(self, "add_memory_btn", None), PRIMARY_GREEN),
        ):
            if btn:
                btn.setStyleSheet(
                    f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {color}, stop:1 #5bb5bc);"
                    f"color: white; padding: {btn_pad}px; font-weight: bold; border-radius: 7px; font-size: {font_pt}pt;"
                )
        def h_min(base): return max(60, int(base * scale))
        def h_max(base): return max(100, int(base * scale))
        if hasattr(self, "message_input"):
            self.message_input.setMinimumHeight(h_min(220))
        if hasattr(self, "results_display"):
            self.results_display.setMinimumHeight(h_min(180))
        if hasattr(self, "reply_chat_input"):
            self.reply_chat_input.setMinimumHeight(h_min(200))
        if hasattr(self, "reply_result_display"):
            self.reply_result_display.setMinimumHeight(h_min(160))
        if hasattr(self, "actions_situation_input"):
            self.actions_situation_input.setMinimumHeight(h_min(120))
            self.actions_situation_input.setMaximumHeight(h_max(220))
        if hasattr(self, "actions_result_display"):
            self.actions_result_display.setMinimumHeight(h_min(160))
        if hasattr(self, "add_memory_content_input"):
            self.add_memory_content_input.setMinimumHeight(h_min(100))
            self.add_memory_content_input.setMaximumHeight(h_max(200))
        if hasattr(self, "_first_run_hint_frame") and self._first_run_hint_frame:
            self._first_run_hint_frame.setStyleSheet(
                f"background-color: {STRIP_BG}; border-radius: {BORDER_RADIUS}; padding: {pad}px; border: 1px solid #dde3ec;"
            )
        for instr in getattr(self, "_instruction_labels", []):
            if instr:
                instr.setStyleSheet(
                    f"padding: {pad}px; background-color: {INSTRUCTION_BG}; border-radius: {BORDER_RADIUS};"
                )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_scale()

    def init_ui(self):
        self.setWindowTitle(f"💡 SmartPersona — {self.persona.get_name()}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = min(geo.width() * 7 // 10, REF_WIDTH)
            h = min(geo.height() * 4 // 5, REF_HEIGHT)
            x = geo.x() + (geo.width() - w) // 2
            y = geo.y() + (geo.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.resize(REF_WIDTH, REF_HEIGHT)

        self._instruction_labels = []

        # --- Title/Strip with friendly, humanized details ---
        self._strip_frame = strip = QFrame()
        strip.setStyleSheet(f"background-color: {STRIP_BG}; border-radius: {BORDER_RADIUS}; padding: 8px;")
        strip_layout = QHBoxLayout(strip)
        self.identity_name_label = QLabel(f"👤 Welcome, {self.persona.get_name()}!")
        self.identity_name_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #1a326c;")
        strip_layout.addWidget(self.identity_name_label)
        strip_layout.addSpacing(24)
        strip_layout.addWidget(QLabel("<b>AI Model:</b>"))

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(180)
        self.model_combo.setMaximumWidth(320)
        self.model_combo.setToolTip(
            "Choose a model installed in Ollama (click Refresh for latest list). Type and Use to switch models."
        )
        strip_layout.addWidget(self.model_combo)

        self.model_refresh_btn = QPushButton("🔄 Refresh")
        self.model_refresh_btn.setToolTip("Reload the list of models from your local Ollama daemon.")
        self.model_refresh_btn.clicked.connect(self._on_refresh_ollama_models)
        strip_layout.addWidget(self.model_refresh_btn)

        self.model_apply_btn = QPushButton("✔️ Use")
        self.model_apply_btn.setToolTip("Apply this model for all features. It will be remembered next launch.")
        self.model_apply_btn.clicked.connect(self._apply_model_from_ui)
        strip_layout.addWidget(self.model_apply_btn)

        self.model_test_btn = QPushButton("🧪 Test")
        self.model_test_btn.setToolTip("Check if Ollama responds to this model name.")
        self.model_test_btn.clicked.connect(self._on_test_ollama_model)
        strip_layout.addWidget(self.model_test_btn)

        self.model_status_label = QLabel("")
        self.model_status_label.setMinimumWidth(52)
        self.model_status_label.setStyleSheet(f"color: {HINT_COLOR}; font-size: 12px;")
        strip_layout.addWidget(self.model_status_label)

        strip_layout.addStretch()

        self.identity_summary_label = QLabel("")
        self.identity_summary_label.setStyleSheet(f"color: {HINT_COLOR}; font-size: 13px;")
        strip_layout.addWidget(self.identity_summary_label)
        self._populate_model_combo()

        main_layout = QVBoxLayout()
        main_layout.addWidget(strip)

        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.North)
        self.main_tabs.setMovable(True)

        # Build and add each tab with more user-friendly, warm, and helpful UIs
        self.main_tabs.addTab(self.create_teach_tab(), "🌱 Teach")
        self.main_tabs.addTab(self.create_ask_reply_tab(), "💬 Reply as you would")
        self.main_tabs.addTab(self.create_actions_tab(), "🧭 What would I do?")
        self.main_tabs.addTab(self.create_talk_to_personas_tab(), "👥 Chat with memories")
        add_memory_tab = self.create_add_memory_tab()
        self._add_memory_tab_widget = add_memory_tab
        self.main_tabs.addTab(add_memory_tab, "📝 Add memory")
        self.main_tabs.addTab(self.create_memories_tab(), "📚 My memories")
        self.main_tabs.addTab(self.create_thoughts_tab(), "💡 My thoughts")

        main_layout.addWidget(self.main_tabs)
        self.setLayout(main_layout)
        self._connect_signals()
        self._update_identity_strip()
        self._refresh_memories_display()
        self._refresh_thoughts_display()
        self._apply_responsive_scale()

    def _connect_signals(self):
        # Teach tab
        self.teach_btn.clicked.connect(self._on_teach_clicked)
        self.clear_teach_btn.clicked.connect(self._on_clear_teach_clicked)
        self.teach_load_file_btn.clicked.connect(self._on_load_teach_file_clicked)
        self.results_copy_btn.clicked.connect(
            lambda: self._copy_to_clipboard(self.results_display, self.results_copy_status)
        )

        # Reply tab
        self.get_reply_btn.clicked.connect(self._on_get_reply_clicked)
        self.reply_clear_btn.clicked.connect(self._on_reply_clear_clicked)
        self.reply_copy_btn.clicked.connect(
            lambda: self._copy_to_clipboard(self.reply_result_display, self.reply_copy_status)
        )

        # Actions tab
        self.get_actions_btn.clicked.connect(self._on_get_actions_clicked)
        self.actions_clear_btn.clicked.connect(self._on_actions_clear_clicked)
        self.actions_copy_btn.clicked.connect(
            lambda: self._copy_to_clipboard(self.actions_result_display, self.actions_copy_status)
        )

        # Persona chat tab
        self.persona_chat_send_btn.clicked.connect(self._on_persona_chat_send_clicked)
        self.persona_chat_clear_btn.clicked.connect(self._on_persona_chat_clear_clicked)

        # Add memory tab
        self.add_memory_btn.clicked.connect(self._on_add_memory_clicked)
        self.add_memory_clear_btn.clicked.connect(self._on_add_memory_clear_clicked)

        # Memory and thought tabs
        self.memories_refresh_btn.clicked.connect(self._refresh_memories_display)
        self.thoughts_refresh_btn.clicked.connect(self._refresh_thoughts_display)

    def _set_busy(self, button, is_busy, busy_text=None):
        if not button:
            return
        if is_busy:
            button.setProperty("_original_text", button.text())
            if busy_text:
                button.setText(busy_text)
            button.setEnabled(False)
            return
        original = button.property("_original_text")
        if original:
            button.setText(original)
            button.setProperty("_original_text", None)
        button.setEnabled(True)

    def _on_teach_clicked(self):
        if self.teaching_thread and self.teaching_thread.isRunning():
            return
        message_history = self.message_input.toPlainText().strip()
        if not message_history:
            QMessageBox.information(self, "Teach", "Please type something before teaching.")
            return
        self.teach_status_label.setText("Thinking...")
        self.results_display.clear()
        self._set_busy(self.teach_btn, True, "⏳ Teaching...")
        self.teaching_thread = TeachingThread(self.brain, message_history, format="auto")
        self.teaching_thread.finished.connect(self._on_teach_finished)
        self.teaching_thread.error.connect(self._on_teach_error)
        self.teaching_thread.start()

    def _on_teach_finished(self, result):
        self._set_busy(self.teach_btn, False)
        parts = [result.get("summary", "Completed.")]
        processed = result.get("processed", 0)
        if processed:
            parts.append(f"Processed messages: {processed}")
        review = result.get("conversation_review") or {}
        if review.get("emotions"):
            parts.append(f"Emotions: {review.get('emotions')}")
        if review.get("situation"):
            parts.append(f"Situation: {review.get('situation')}")
        if review.get("meaning"):
            parts.append(f"Meaning: {review.get('meaning')}")
        self.results_display.setPlainText("\n\n".join(parts))
        self.teach_status_label.setText("Done")
        self._update_identity_strip()

    def _on_teach_error(self, error):
        self._set_busy(self.teach_btn, False)
        self.teach_status_label.setText("Failed")
        QMessageBox.warning(self, "Teach Error", str(error))

    def _on_clear_teach_clicked(self):
        self.message_input.clear()
        self.teach_status_label.clear()

    def _on_load_teach_file_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load chat text or export",
            "",
            "Text / JSON (*.txt *.json);;All files (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.message_input.setPlainText(f.read())
            self.teach_status_label.setText("Loaded file")
        except OSError as e:
            QMessageBox.warning(self, "Load file", str(e))

    def _on_get_reply_clicked(self):
        if self.reply_suggestion_thread and self.reply_suggestion_thread.isRunning():
            return
        chat_history = self.reply_chat_input.toPlainText().strip()
        if not chat_history:
            QMessageBox.information(self, "Suggest Reply", "Please enter a conversation or prompt first.")
            return
        self.reply_loader_label.setVisible(True)
        self.reply_result_display.clear()
        self.reply_copy_status.clear()
        self._set_busy(self.get_reply_btn, True, "⏳ Thinking...")
        hint = ""
        if hasattr(self, "reply_style_hint"):
            hint = (self.reply_style_hint.text() or "").strip()
        user_prompt = None
        if hint:
            user_prompt = (
                "Based on the conversation above and what you know about me from memories, "
                "suggest a short reply I could send in the same informal texting style I use when possible. "
                "Reply with only the suggested message, no extra explanation.\n\n"
                f"Additional direction: {hint}"
            )
        self.reply_suggestion_thread = ReplySuggestionThread(
            self.brain,
            chat_history,
            user_prompt=user_prompt,
            format="auto",
        )
        self.reply_suggestion_thread.finished.connect(self._on_get_reply_finished)
        self.reply_suggestion_thread.error.connect(self._on_get_reply_error)
        self.reply_suggestion_thread.start()

    def _on_get_reply_finished(self, result):
        self.reply_loader_label.setVisible(False)
        self._set_busy(self.get_reply_btn, False)
        if result.get("error"):
            self.reply_result_display.setPlainText(result.get("error", "Unknown error."))
            return
        self.reply_result_display.setPlainText(result.get("reply", "").strip())

    def _on_get_reply_error(self, error):
        self.reply_loader_label.setVisible(False)
        self._set_busy(self.get_reply_btn, False)
        QMessageBox.warning(self, "Reply Suggestion Error", str(error))

    def _on_reply_clear_clicked(self):
        self.reply_chat_input.clear()
        self.reply_copy_status.clear()
        if hasattr(self, "reply_style_hint"):
            self.reply_style_hint.clear()

    def _on_get_actions_clicked(self):
        if hasattr(self, "actions_suggestion_thread") and self.actions_suggestion_thread and self.actions_suggestion_thread.isRunning():
            return
        situation_text = self.actions_situation_input.toPlainText().strip()
        if not situation_text:
            QMessageBox.information(self, "Get Actions", "Describe a situation first.")
            return
        self.actions_result_display.clear()
        self.actions_copy_status.clear()
        self._set_busy(self.get_actions_btn, True, "⏳ Thinking...")
        self.actions_suggestion_thread = ActionsSuggestionThread(
            self.brain,
            situation_text,
            persona_name=self.persona.get_name(),
        )
        self.actions_suggestion_thread.finished.connect(self._on_get_actions_finished)
        self.actions_suggestion_thread.error.connect(self._on_get_actions_error)
        self.actions_suggestion_thread.start()

    def _on_get_actions_finished(self, result):
        self._set_busy(self.get_actions_btn, False)
        if result.get("error"):
            self.actions_result_display.setPlainText(result.get("error", "Unknown error."))
            return
        actions = result.get("actions", [])
        text = "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(actions)) if actions else result.get("raw", "")
        self.actions_result_display.setPlainText(text)

    def _on_get_actions_error(self, error):
        self._set_busy(self.get_actions_btn, False)
        QMessageBox.warning(self, "Actions Error", str(error))

    def _on_actions_clear_clicked(self):
        self.actions_situation_input.clear()
        self.actions_copy_status.clear()

    def _on_persona_chat_send_clicked(self):
        if self.persona_chat_thread and self.persona_chat_thread.isRunning():
            return
        user_message = self.persona_chat_input.toPlainText().strip()
        if not user_message:
            QMessageBox.information(self, "Chat", "Please type a message first.")
            return
        self._persona_chat_pending_user = user_message
        self.persona_chat_display.append(f"You ({self.persona.get_name()}): {user_message}\n")
        self.persona_chat_input.clear()
        self._set_busy(self.persona_chat_send_btn, True, "⏳ Sending...")
        self.persona_chat_thread = PersonaChatThread(
            self.brain,
            user_message,
            self._persona_chat_history,
            self.persona.get_name(),
        )
        self.persona_chat_thread.finished.connect(self._on_persona_chat_finished)
        self.persona_chat_thread.error.connect(self._on_persona_chat_error)
        self.persona_chat_thread.start()

    def _on_persona_chat_finished(self, result):
        self._set_busy(self.persona_chat_send_btn, False)
        reply = (result.get("reply") or "").strip()
        error = result.get("error")
        if error:
            self.persona_chat_display.append(f"Error: {error}\n")
            return
        if reply:
            self.persona_chat_display.append(f"{reply}\n")
            if self._persona_chat_pending_user:
                self._persona_chat_history.append({"role": "user", "content": self._persona_chat_pending_user})
            self._persona_chat_history.append({"role": "assistant", "content": reply})
        self._persona_chat_pending_user = ""

    def _on_persona_chat_error(self, error):
        self._set_busy(self.persona_chat_send_btn, False)
        QMessageBox.warning(self, "Chat Error", str(error))
        self._persona_chat_pending_user = ""

    def _on_persona_chat_clear_clicked(self):
        self.persona_chat_input.clear()
        self._persona_chat_history = []
        self.persona_chat_display.clear()

    def _on_add_memory_clicked(self):
        if self.add_memory_validation_thread and self.add_memory_validation_thread.isRunning():
            return
        content = self.add_memory_content_input.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "Add Memory", "Please type memory content first.")
            return
        mem_type = self.add_memory_type_input.currentText().strip() or "fact"
        person = self.add_memory_person_input.text().strip() or None
        topic = self.add_memory_topic_input.text().strip() or None
        situation = self.add_memory_situation_input.text().strip() or None
        role = self.add_memory_role_input.text().strip() or None
        self._set_busy(self.add_memory_btn, True, "⏳ Validating...")
        self.add_memory_status_label.setText("")
        self.add_memory_result_display.clear()
        self.add_memory_validation_thread = AddMemoryValidationThread(
            self.brain,
            content,
            mem_type,
            person=person,
            topic=topic,
            situation=situation,
            role=role,
        )
        self.add_memory_validation_thread.finished.connect(
            lambda result: self._on_add_memory_validation_finished(
                result, content, mem_type, person, topic, situation, role
            )
        )
        self.add_memory_validation_thread.error.connect(self._on_add_memory_error)
        self.add_memory_validation_thread.start()

    def _on_add_memory_validation_finished(self, result, content, mem_type, person, topic, situation, role):
        self._set_busy(self.add_memory_btn, False)
        if not result.get("valid", True):
            feedback = result.get("feedback", "Memory validation failed.")
            self.add_memory_status_label.setStyleSheet("color: #b25b00;")
            self.add_memory_status_label.setText("Needs review")
            self.add_memory_result_display.setPlainText(feedback)
            return
        self.brain.add_memory(
            content,
            type=mem_type,
            source="user",
            person=person,
            topic=topic,
            situation=situation,
            role=role,
        )
        feedback = result.get("feedback", "").strip()
        self.add_memory_status_label.setStyleSheet("color: green;")
        self.add_memory_status_label.setText("Memory added")
        self.add_memory_result_display.setPlainText(
            "Saved this memory successfully." + (f"\n\nValidator note:\n{feedback}" if feedback else "")
        )
        self._update_identity_strip()
        self._refresh_memories_display()

    def _on_add_memory_error(self, error):
        self._set_busy(self.add_memory_btn, False)
        QMessageBox.warning(self, "Add Memory Error", str(error))

    def _on_add_memory_clear_clicked(self):
        self.add_memory_content_input.clear()
        self.add_memory_type_input.setCurrentText("fact")
        self.add_memory_person_input.clear()
        self.add_memory_topic_input.clear()
        self.add_memory_situation_input.clear()
        self.add_memory_role_input.clear()
        self.add_memory_status_label.clear()
        self.add_memory_result_display.clear()

    def _refresh_memories_display(self):
        memories = self.brain.get_memory()
        if not memories:
            self.memories_display.setPlainText("No memories recorded yet.")
            return
        lines = [f"{idx + 1}. {item}" for idx, item in enumerate(memories)]
        self.memories_display.setPlainText("\n".join(lines))
        self._update_identity_strip()

    def _refresh_thoughts_display(self):
        thoughts = self.brain.get_thoughts(limit=999)
        if not thoughts:
            self.thoughts_display.setPlainText("No thoughts generated yet.")
            return
        lines = []
        for idx, item in enumerate(thoughts, start=1):
            thought = (item.get("thought") or "").strip() if isinstance(item, dict) else str(item)
            context = (item.get("context") or "").strip() if isinstance(item, dict) else ""
            if context:
                lines.append(f"{idx}. {thought}\n   Context: {context}")
            else:
                lines.append(f"{idx}. {thought}")
        self.thoughts_display.setPlainText("\n\n".join(lines))
        self._update_identity_strip()

    # -----------------------------------------------------------------
    # Warm, user-centric, tooltip-rich tab creation methods
    # -----------------------------------------------------------------
    def create_teach_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "🌱 <b>Learn from your chats (Telegram, etc.)</b><br>"
            "Paste an export or copied chat: <b>Telegram</b> often looks like "
            "<code>Name, [date/time]</code> then the message on the next line—you can also use "
            "<code>Sender: message</code> lines or JSON from other tools.<br>"
            "You can also paste a short free-form note; the app will still try to extract memories.<br>"
            "<span style='color:#577;'>Set <code>PERSONA_NAME</code> in <code>.env</code> to match your handle in exports for best attribution.</span>")
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText(
            "Paste Telegram / WhatsApp export text, or lines like:\n"
            "Alex, [12/08/2024 10:00]\n"
            "Hey are you free tonight?\n\n"
            "Or a quick note: \"I usually reply with short messages and lots of stickers.\""
        )
        self.message_input.setToolTip(
            "Paste multi-message chat history or a single teaching note. Use Load from file for large exports."
        )
        layout.addWidget(self.message_input)
        btn_layout = QHBoxLayout()
        self.teach_load_file_btn = QPushButton("📂 Load from file…")
        self.teach_load_file_btn.setToolTip("Load a .txt or .json snippet (e.g. copied export) into the box above.")
        btn_layout.addWidget(self.teach_load_file_btn)
        self.teach_btn = QPushButton("✨ Teach me")
        self.teach_btn.setStyleSheet("font-weight: bold;")
        self.teach_btn.setToolTip("Add this as a new memory with your persona.")
        btn_layout.addWidget(self.teach_btn)
        self.clear_teach_btn = QPushButton("🧹 Clear")
        self.clear_teach_btn.setToolTip("Clear this teaching input.")
        btn_layout.addWidget(self.clear_teach_btn)
        btn_layout.addStretch()
        self.teach_status_label = QLabel("")
        self.teach_status_label.setStyleSheet("color: green;")
        btn_layout.addWidget(self.teach_status_label)
        layout.addLayout(btn_layout)
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("Your taught facts and AI suggestions will appear here. 🪄\n\nTry typing in the box above and click 'Teach me' to get started!")
        self.results_display.setToolTip("Results and summaries based on what you've shared with your persona.")
        layout.addWidget(self.results_display)
        self.results_copy_btn = QPushButton("📋 Copy Results")
        self.results_copy_btn.setToolTip("Copy result text above to clipboard.")
        self.results_copy_status = QLabel("")
        self.results_copy_status.setStyleSheet("color: green;")
        copy_layout = QHBoxLayout()
        copy_layout.addWidget(self.results_copy_btn)
        copy_layout.addWidget(self.results_copy_status)
        copy_layout.addStretch()
        layout.addLayout(copy_layout)
        # Connect signals/slots in the main window logic.
        return widget

    def create_ask_reply_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "💬 <b>How would you respond?</b> <br>"
            "Ask me to reply as your persona. Try providing a situation, message, or even a chat!"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        
        self.reply_chat_input = QTextEdit()
        self.reply_chat_input.setPlaceholderText(
            "Type a message or conversation you want your persona to reply to.\n(e.g., \"Hi! Are you going to the party?\")"
        )
        self.reply_chat_input.setToolTip(
            "Paste the thread you are replying to. The app uses stored memories (including texting style) to suggest what you might send."
        )
        layout.addWidget(self.reply_chat_input)

        hint_row = QHBoxLayout()
        hint_row.addWidget(QLabel("Style hint (optional):"))
        self.reply_style_hint = QLineEdit()
        self.reply_style_hint.setPlaceholderText("e.g. shorter · more formal · same energy as usual")
        self.reply_style_hint.setToolTip("Nudges the model without replacing your chat context.")
        hint_row.addWidget(self.reply_style_hint)
        layout.addLayout(hint_row)

        row = QHBoxLayout()
        self.get_reply_btn = QPushButton("💡 Suggest a Reply")
        self.get_reply_btn.setStyleSheet("font-weight: bold;")
        self.get_reply_btn.setToolTip("Let the AI suggest a warm, genuine response.")
        row.addWidget(self.get_reply_btn)

        self.reply_clear_btn = QPushButton("🧹 Clear")
        self.reply_clear_btn.setToolTip("Clear the chat/question input.")
        row.addWidget(self.reply_clear_btn)

        row.addStretch()
        self.reply_copy_status = QLabel("")
        self.reply_copy_status.setStyleSheet("color:green;")
        row.addWidget(self.reply_copy_status)
        layout.addLayout(row)

        self.reply_loader_label = QLabel("Thinking 🤔 ...")
        self.reply_loader_label.setStyleSheet("color: #888; font-style: italic; margin-top:6px;")
        self.reply_loader_label.setVisible(False)
        layout.addWidget(self.reply_loader_label)

        self.reply_result_display = QTextEdit()
        self.reply_result_display.setPlaceholderText(
            "Your persona's suggested replies will show here.\n\n"
            "Try typing a message above and click Suggest Reply!"
        )
        self.reply_result_display.setReadOnly(True)
        self.reply_result_display.setToolTip("Results will appear here. Copy to clipboard as needed.")
        layout.addWidget(self.reply_result_display)

        self.reply_copy_btn = QPushButton("📋 Copy Reply")
        self.reply_copy_btn.setToolTip("Copy the generated reply to your clipboard.")
        copyrow = QHBoxLayout()
        copyrow.addWidget(self.reply_copy_btn)
        copyrow.addStretch()
        layout.addLayout(copyrow)

        return widget
    def create_actions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "🧭 <b>What would you do?</b><br>"
            "Describe a scenario and I'll suggest what your persona might do or decide.\n"
            "<span style='color:#577;'>Great for exploring decisions, reactions, or advice!</span>"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.actions_situation_input = QTextEdit()
        self.actions_situation_input.setPlaceholderText(
            "Describe a situation or decision point.\n(e.g., \"You see someone forget their wallet in a café.\")"
        )
        self.actions_situation_input.setToolTip("Provide a scenario and I'll suggest how your persona might act.")
        layout.addWidget(self.actions_situation_input)
        row = QHBoxLayout()
        self.get_actions_btn = QPushButton("🎯 Get Actions")
        self.get_actions_btn.setToolTip("Figure out what your persona might decide or do here.")
        row.addWidget(self.get_actions_btn)
        self.actions_clear_btn = QPushButton("🧹 Clear")
        self.actions_clear_btn.setToolTip("Clear the scenario input.")
        row.addWidget(self.actions_clear_btn)
        row.addStretch()
        self.actions_copy_status = QLabel("")
        self.actions_copy_status.setStyleSheet("color: green;")
        row.addWidget(self.actions_copy_status)
        layout.addLayout(row)
        self.actions_result_display = QTextEdit()
        self.actions_result_display.setReadOnly(True)
        self.actions_result_display.setPlaceholderText(
            "Your persona's decision or possible actions will appear here.\n\n"
            "Try describing a scenario above, then click Get Actions."
        )
        self.actions_result_display.setToolTip("Results based on your scenario will show here. Copy to clipboard if needed.")
        layout.addWidget(self.actions_result_display)
        self.actions_copy_btn = QPushButton("📋 Copy Actions")
        self.actions_copy_btn.setToolTip("Copy the actions or decision to clipboard.")
        copyrow = QHBoxLayout()
        copyrow.addWidget(self.actions_copy_btn)
        copyrow.addStretch()
        layout.addLayout(copyrow)
        return widget

    def create_talk_to_personas_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "👥 <b>Chat as your learned self</b><br>"
            "Ask questions or try out wording; answers use <b>your</b> stored memories and texting style.<br>"
            "<span style='color:#577;'>This is not for simulating other people—that would need picking contacts elsewhere. "
            "Teach from exports in 🌱 Teach first.</span>"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.persona_chat_input = QTextEdit()
        self.persona_chat_input.setPlaceholderText(
            "e.g. \"How might I word a rain check to Alex?\" or \"What do I know about last week's trip?\""
        )
        self.persona_chat_input.setToolTip(
            "Messages here use your persona name and full memory—not every contact in memory at once."
        )
        layout.addWidget(self.persona_chat_input)
        btnrow = QHBoxLayout()
        self.persona_chat_send_btn = QPushButton("💬 Chat")
        self.persona_chat_send_btn.setToolTip("Send your message to start or continue the conversation!")
        btnrow.addWidget(self.persona_chat_send_btn)
        self.persona_chat_clear_btn = QPushButton("🧹 Clear")
        self.persona_chat_clear_btn.setToolTip("Clear the conversation input.")
        btnrow.addWidget(self.persona_chat_clear_btn)
        btnrow.addStretch()
        layout.addLayout(btnrow)
        self.persona_chat_display = QTextEdit()
        self.persona_chat_display.setReadOnly(True)
        self.persona_chat_display.setPlaceholderText(
            "The ongoing conversation will appear here.\n\nGet started by typing in the box above!"
        )
        self.persona_chat_display.setToolTip("See the current conversation here. Scroll for history.")
        layout.addWidget(self.persona_chat_display)
        return widget

    def create_add_memory_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "📝 <b>Add a Memory to Your Persona</b><br>"
            "Directly add a memory, trait, event, or detail about yourself.\n"
            "<span style='color:#577;'>Pro tip: Meaningful memories help me be more like you!</span>"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.add_memory_content_input = QTextEdit()
        self.add_memory_content_input.setPlaceholderText("Type a new memory, fact, or belief for your persona.")
        self.add_memory_content_input.setToolTip("Write a fact, story, trait, or anything meaningful to add as a memory.")
        layout.addWidget(self.add_memory_content_input)
        # Additional optional info (person, topic, situation, role, type)
        sub_layout = QHBoxLayout()
        self.add_memory_type_input = QComboBox()
        self.add_memory_type_input.addItems(list(MEMORY_TYPES))
        self.add_memory_type_input.setCurrentText("fact")
        self.add_memory_type_input.setToolTip("Choose the kind of memory you're adding (helps AI organize facts).")
        sub_layout.addWidget(QLabel("Type:"))
        sub_layout.addWidget(self.add_memory_type_input)
        self.add_memory_person_input = QLineEdit()
        self.add_memory_person_input.setPlaceholderText("Who is involved? (optional)")
        self.add_memory_person_input.setToolTip("Optionally state a person involved in this memory.")
        sub_layout.addWidget(QLabel("Person:"))
        sub_layout.addWidget(self.add_memory_person_input)
        self.add_memory_topic_input = QLineEdit()
        self.add_memory_topic_input.setPlaceholderText("Topic (optional)")
        self.add_memory_topic_input.setToolTip("Optionally specify a topic for this memory.")
        sub_layout.addWidget(QLabel("Topic:"))
        sub_layout.addWidget(self.add_memory_topic_input)
        layout.addLayout(sub_layout)
        sub2 = QHBoxLayout()
        self.add_memory_situation_input = QLineEdit()
        self.add_memory_situation_input.setPlaceholderText("Situation (optional)")
        self.add_memory_situation_input.setToolTip("Optionally describe a situation or context.")
        sub2.addWidget(QLabel("Situation:"))
        sub2.addWidget(self.add_memory_situation_input)
        self.add_memory_role_input = QLineEdit()
        self.add_memory_role_input.setPlaceholderText("Role (optional)")
        self.add_memory_role_input.setToolTip("Optionally, what role or hat were you wearing?")
        sub2.addWidget(QLabel("Role:"))
        sub2.addWidget(self.add_memory_role_input)
        layout.addLayout(sub2)
        btn_row = QHBoxLayout()
        self.add_memory_btn = QPushButton("💾 Add Memory")
        self.add_memory_btn.setStyleSheet("font-weight: bold;")
        self.add_memory_btn.setToolTip("Save this as a validated memory for your persona.")
        btn_row.addWidget(self.add_memory_btn)
        self.add_memory_clear_btn = QPushButton("🧹 Clear")
        self.add_memory_clear_btn.setToolTip("Clear your new memory input fields.")
        btn_row.addWidget(self.add_memory_clear_btn)
        btn_row.addStretch()
        self.add_memory_type_hint = QLabel("")
        self.add_memory_type_hint.setStyleSheet("color: #0c6;")
        btn_row.addWidget(self.add_memory_type_hint)
        layout.addLayout(btn_row)
        self.add_memory_status_label = QLabel("")
        self.add_memory_status_label.setStyleSheet("color: green;")
        layout.addWidget(self.add_memory_status_label)
        self.add_memory_result_display = QTextEdit()
        self.add_memory_result_display.setReadOnly(True)
        self.add_memory_result_display.setPlaceholderText(
            "Memory validation results and details will appear here.\n\n"
            "Type something above and click Add Memory when ready!"
        )
        self.add_memory_result_display.setToolTip("Validation and feedback on your submitted memory appears here.")
        layout.addWidget(self.add_memory_result_display)
        return widget

    def create_memories_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "📚 <b>Your Memories</b><br>"
            "See everything I've remembered from your lessons, chats, and direct memory additions.<br>"
            "<span style='color:#577;'>Having no memories? Go to the Teach tab or Add Memory to get started!</span>"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.memories_display = QTextEdit()
        self.memories_display.setReadOnly(True)
        self.memories_display.setPlaceholderText(
            "No memories recorded yet.\n🌱 Start teaching or add memories from other tabs to build your persona!"
        )
        self.memories_display.setToolTip("A summary of all facts, traits, and events the AI has learned about you.")
        layout.addWidget(self.memories_display)
        btnrow = QHBoxLayout()
        self.memories_refresh_btn = QPushButton("🔄 Refresh Memories")
        self.memories_refresh_btn.setToolTip("Fetch the latest memories from AI storage.")
        btnrow.addWidget(self.memories_refresh_btn)
        btnrow.addStretch()
        layout.addLayout(btnrow)
        return widget

    def create_thoughts_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "💡 <b>Your Persona's Thoughts</b><br>"
            "See what your persona is contemplating, deducing, or reflecting on based on your teachings."
            "<br><span style='color:#577;'>Start sharing with me to see my thoughts evolve!</span>"
        )
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; margin-bottom:8px;")
        layout.addWidget(label)
        self.thoughts_display = QTextEdit()
        self.thoughts_display.setReadOnly(True)
        self.thoughts_display.setPlaceholderText(
            "No thoughts generated yet.\n🧠 Teach me, chat, or add memories to start seeing reflections here."
        )
        self.thoughts_display.setToolTip("Thoughts and inferences based on your current persona's knowledge.")
        layout.addWidget(self.thoughts_display)
        btnrow = QHBoxLayout()
        self.thoughts_refresh_btn = QPushButton("🔄 Refresh Thoughts")
        self.thoughts_refresh_btn.setToolTip("Update with the most current thoughts from your persona.")
        btnrow.addWidget(self.thoughts_refresh_btn)
        btnrow.addStretch()
        layout.addLayout(btnrow)
        return widget
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = SmartPersonaGUI()
    gui.show()
    sys.exit(app.exec_())
