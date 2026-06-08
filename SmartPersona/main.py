import sys
from persona import SmartPersona


def main():
    """Main entry point: launch the SmartPersona GUI."""
    from PyQt5.QtWidgets import QApplication
    from gui import SmartPersonaGUI

    app = QApplication(sys.argv)
    persona = SmartPersona()
    window = SmartPersonaGUI(persona=persona)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
