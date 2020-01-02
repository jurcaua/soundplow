import sys
from functools import partial

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWidget, QLineEdit, QTextEdit, QPushButton, QListWidget, QTabWidget, QLabel, QVBoxLayout, QShortcut
from PySide2.QtCore import QFile, QObject, Signal, Qt
from PySide2.QtGui import QKeySequence

from controller import Controller, DEFAULT_OUTPUT
from soundplow import Soundplow
from log import Log, MessageType
from exceptions import WidgetNotFound

MAIN_UI = 'resources/ui.ui'
SEARCH_RESULTS_POPUP_UI = 'resources/search_results.ui'
CLIENT_ID = 'resources/secret.txt'
STYLE_SHEET = 'resources/stylesheet.qss'

class UIObject(QObject):
    def __init__(self, parent=None):
        QObject.__init__(self)

        self.parent = parent

    def get_widget(self, qtype, name):
        widget = self.parent.findChild(qtype, name)
        if widget is None:
            raise WidgetNotFound("Widget with name \"{name}\" with type {type} was not found.".format(name=name, type=qtype))
        return widget

class Button(UIObject):
    def __init__(self, button):
        UIObject.__init__(self)

        self.parent = button

        self.enabled = False
        self.enabled_text = self.parent.text()
        self.disabled_text = self.parent.text()

    def when_clicked(self, event):
        self.parent.clicked.connect(event)

    def set_text(self, text):
        self.parent.setText(text)

    def toggle_text(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.set_text(self.enabled_text)
        else:
            self.set_text(self.disabled_text)

class Textbox(UIObject):
    def __init__(self, textbox):
        UIObject.__init__(self)

        self.parent = textbox

    def set_text(self, text):
        self.parent.setText(text)

    def get_text(self):
        return self.parent.text()

    def take_text(self):
        text = self.get_text()
        self.clear_text()
        return text

    def clear_text(self):
        self.parent.setText('')

class Tab(UIObject):
    on_click = Signal()

    def __init__(self, name, tab):
        UIObject.__init__(self)

        self.parent = tab
        self.textbox = Textbox(self.get_widget(QLineEdit, "textbox_{suffix}".format(suffix=name)))
        self.button= Button(self.get_widget(QPushButton, "button_{suffix}".format(suffix=name)))
        self.popup = None

        self.button.when_clicked(self.on_click.emit)

    def destroy_popup(self):
        del self.popup
        self.popup = None

class ListView(UIObject):
    def __init__(self, listview):
        UIObject.__init__(self)

        self.parent = listview

        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.parent)
        delete_shortcut.activated.connect(self.delete_current)

    def add_item(self, text):
        if not isinstance(text, str):
            raise RuntimeError("Only strings accepted in ListView object!")

        if text is '':
            Log.instance().warning("Please enter a link in the textbox.")
            return

        if ',' in text:
            Log.instance().warning("Invalid character \",\" found in link \"{}\". Please check your link.".format(text))
            return

        if r'soundcloud.com' not in text:
            Log.instance().warning("Invalid link \"{}\" entered. Link with: \"...soundcloud.com/...\" expected.".format(text))
            return

        self.parent.addItem(text)

    def get_items(self):
        num_items = self.parent.count()
        for i in range(num_items):
            yield str(self.parent.takeItem(0).text())

    def delete_current(self):
        if len(self.parent.selectedItems()) > 0:
            self.parent.takeItem(self.parent.currentRow())


class UI(UIObject):
    tab_names = ["search", "like", "link"]

    def __init__(self, ui_file_path=MAIN_UI):
        UIObject.__init__(self)

        self.controller = None

        # Load .ui file
        self.parent = self.load_ui_file(ui_file_path)

        # Load stylesheet
        #self.parent.setStyleSheet(open(STYLE_SHEET).read());

        # Initialize all tab widgets
        self.get_widget(QTabWidget, "tabs").setCurrentIndex(0)

        self.tabs = {}
        for name in self.tab_names:
            self.tabs[name] = Tab(name, self.get_widget(QWidget, "tab_{suffix}".format(suffix=name)))

        if 'link' in self.tabs:
            self.track_list = ListView(self.get_widget(QListWidget, "track_list"))
            self.download_all_button = Button(self.get_widget(QPushButton, "button_download_all"))

        self.output_textbox = Textbox(self.get_widget(QLineEdit, "textbox_output"))

        Log.instance().load(self.get_widget(QTextEdit, "log"))

        self.parent.show()

        Log.instance().info("UI initialized...")

    def load(self):
        self.initialize_tabs()

        Log.instance().info("UI loaded with tabs: {tabs}.".format(tabs=", ".join(self.tab_names)))

    def load_ui_file(self, ui_file_path):
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        return loader.load(ui_file)

    def set_controller(self, controller):
        self.controller = controller

    def initialize_tabs(self):
        if 'link' in self.tabs:
            self.tabs['link'].on_click.connect(lambda: self.track_list.add_item(self.tabs['link'].textbox.take_text()))

            self.download_all_button.when_clicked(lambda : self.controller.batch_download_urls(self.track_list.get_items()))

        if 'search' in self.tabs:
            self.tabs['search'].on_click.connect(lambda: self.search_result_popup(self.tabs['search'].textbox.get_text(), self.controller.get_search_results(self.tabs['search'].textbox.get_text())))

        if 'like' in self.tabs:
            tab = self.tabs['like']
            self.tabs['like'].button.disabled_text = "Start Listening"
            self.tabs['like'].button.enabled_text = "Stop Listening"
            self.tabs['like'].on_click.connect(lambda: self.controller.toggle_listen_for_likes(self.tabs['like'].textbox.get_text()))

    def search_result_popup(self, query, search_results):
        if 'search' in self.tabs:
            self.tabs['search'].textbox.clear_text()

        if query is None or query is '':
            Log.instance().warning("Please enter a non-empty search query.")
            return

        if len(search_results) == 0:
            Log.instance().warning("No search results found for search: \"{query}\"".format(query=query))
            return

        if 'search' in self.tabs and self.tabs['search'].popup is None:
            self.tabs['search'].textbox.clear_text()

            # Load popup .ui file
            self.tabs['search'].popup = UIObject(self.load_ui_file(SEARCH_RESULTS_POPUP_UI))
            self.tabs['search'].popup.parent.setAttribute(Qt.WA_DeleteOnClose)

            # Format title
            title = self.tabs['search'].popup.get_widget(QLabel, 'title')
            title.setText(title.text().format(query=query)) # already set to {query} in QtDesigner

            # Get button area
            button_area = self.tabs['search'].popup.get_widget(QVBoxLayout, 'button_area')
            for i in range(len(search_results)):
                # Create a button out of each search_result
                button = QPushButton(text=self.controller.get_track_name(search_results[i]))
                button_font = button.font()
                button_font.setPointSize(12)
                button.setFont(button_font)

                # Connect each button to downloading the song
                # NOTE: Partial used instead of lambda because they save the current value to excude the func (lambda would use the last i value cause its incremented)
                button.clicked.connect(partial(self.controller.download_track_by_id, search_results[i].id))
                button.clicked.connect(partial(button.setEnabled, False))

                button_area.addWidget(button)

            # Handle closing the dialog
            self.tabs['search'].popup.parent.destroyed.connect(self.reset_search_dialog)

            # Show popup
            self.tabs['search'].popup.parent.show()
        else:
            if 'search' not in self.tabs:
                Log.instance().warning("Cannot display search results dialog when search module is not enabled!")
            elif self.tabs['search'].popup is not None:
                Log.instance().warning("Search results dialog already displayed. Please close the previous dialog before searching again.")

    def reset_search_dialog(self):
        self.tabs['search'].popup = None


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)

    # Instantiate
    ui = UI()
    controller = Controller()
    soundplow = Soundplow(open(CLIENT_ID, 'r').read().strip())

    # Set dependencies
    ui.set_controller(controller)
    controller.set_ui(ui)
    controller.set_model(soundplow)
    soundplow.set_controller(controller)

    # Finish loading after dependencies are set
    ui.load()
    controller.load()
    soundplow.load()

    controller.close_app(app.exec_())
