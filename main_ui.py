import asyncio
import sys
import urwid
import message
import text_utils
import view
import zephyr_utils

debug = False

keys = {
        'quit': 'q',
        'new_tab': 'ctrl n',
        'next_tab': 'n',
        'prev_tab': 'p',
        'close_tab': 'ctrl w'
}

class MainUI(object):
    """The main user interface for the program.

    MainUI is a singleton, so it can be referrenced simply by calling MainUI.
    """
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            cls._instance = instance
            instance.view = view.View()
            instance._keys = keys
            instance._running = False
            instance._tabbed_window = TabbedWindowWidget(instance._keys)
            instance._start_loop()
        return cls._instance

    def _start_loop(self):
        """Start the main loop."""
        self._event_loop = asyncio.get_event_loop()
        self._urwid_loop = urwid.MainLoop(
            LoadingWidget(), handle_mouse=False,
            input_filter=self._input_filter,
            event_loop=urwid.AsyncioEventLoop(loop=self._event_loop)
        )
        #self._urwid_loop.screen.set_terminal_properties(colors=palette_colors)
        self._urwid_loop.start()
        # Enable bracketed paste mode after the terminal has been switched to
        # the alternate screen (after MainLoop.start() to work around bug
        # 729533 in VTE.
        sys.stdout.write('\x1b[?2004h')
        try:
            self._task = asyncio.Task(self._start())
            self._event_loop.run_until_complete(self._task)
        finally:
            # Ensure urwid cleans up properly and doesn't wreck the
            # terminal.
            self._urwid_loop.stop()
            self._event_loop.close()
            sys.stdout.write('\x1b[?2004l')

    def _input_filter(self, keys, raw):
        """Handle global keybindings."""
        if keys == [self._keys['quit']]:
            self._on_quit()
        else:
            return keys

    def _on_message(self, msg):
        self.view.add_message(msg)

    def _on_quit(self):
        self._running = False
        self._task.cancel()

    async def _start(self):
        self._running = True
        if debug:
            self.subs = await zephyr_utils.loadsubs('short_subs')
        else:
            self.subs = await zephyr_utils.loadsubs()
        self._urwid_loop.widget = self._tabbed_window
        self._tabbed_window.set_tab(MainViewTab(), True, 'Main View')
        try:
            while self._running:
                msg = await zephyr_utils.receive()
                self._on_message(message.ZephyrMessage(msg))
        except asyncio.CancelledError:
            pass


class LoadingWidget(urwid.WidgetWrap):
    """Widget that shows a `loading' indicator."""
    def __init__(self):
        super().__init__(urwid.Filler(urwid.Text('Loading...', align='center')))


class TabbedWindowWidget(urwid.WidgetWrap):
    """Widget to display a list of Widgets via a tab bar."""
    def __init__(self, keybindings):
        self._widgets = []  # urwid.Widget
        self._widget_title = {}  # {urwid.Widget: str}
        self._cur_tab = None  # int
        self._keys = keybindings
        self._tabs = urwid.Text('')
        self._frame = urwid.Frame(body=None, header=self._tabs)
        super().__init__(self._frame)

    def _update_tabs(self):
        """Update tab display."""
        text = []
        for num, widget in enumerate(self._widgets):
            palette = ('active_tab' if num == self._cur_tab else
                'inactive_tab')
            text.append((palette, ' {} '.format(self._widget_title[widget])))
            text.append(('tab_background', ' '))
        self._tabs.set_text(text)
        self._frame.contents['body'] = (self._widgets[self._cur_tab], None)

    def get_current_widget(self):
        """Return the widget in the current tab."""
        return self._widgets[self._cur_tab]

    def del_tab(self, tab):
        """Remove a tab.

        Args:
            tab: If tab is an int or a slice, remove the tab(s) at that index.
                If it is a widget, remove the first tab with that widget.

        Raises:
            IndexError if tab is an int greater than the number of tabs.
            ValueError if a widget is provided but it does not correspond to
                any tab.
            KeyError if tab is of a type other than integer, slice, or widget.
        """
        try:
            idx = tab
            widget = self._widgets[tab]
        except TypeError:
            if isinstance(urwid.Widget):
                idx = self._widgets.index(tab)
                widget = tab
            else:
                raise TypeError('tab must be integer, slice, or widget, not '
                                '{}'.format(type(tab).__name__))
        del self._widgets[idx]
        del self._widget_title[widget]
        if idx <= self._cur_tab:
            self._cur_tab -= 1
        self._update_tabs()

    def set_tab(self, widget, switch=False, title=None):
        """Add or modify a tab.

        Args:
            widget: The widget to add or switch to. If it is not already a tab,
                it will be added.
            switch (optional): If switch is set to True, switch to the tab.
            title (optional): If title is provided, set the tab's title.
        """
        if widget not in self._widgets:
            self._widgets.append(widget)
            self._widget_title[widget] = ''
        if switch:
            self._cur_tab = self._widgets.index(widget)
        if title is not None:
            self._widget_title[widget] = title
        self._update_tabs()

    def keypress(self, size, key):
        key = super().keypress(size, key)
        num_tabs = len(self._widgets)
        if key == self._keys.get('prev_tab'):
            self._cur_tab = (self._cur_tab - 1) % num_tabs
            self._update_tabs()
        elif key == self._keys.get('next_tab'):
            self._cur_tab = (self._cur_tab + 1) % num_tabs
            self._update_tabs()
        elif key == self._keys.get('close_tab'):
            self.del_tab(self._cur_tab)
        elif key == self._keys.get('new_tab'):
            tab = MainViewTab()
            self.set_tab(tab, True, 'Main View')
        else:
            return key


class MainViewTab(urwid.WidgetWrap):
    """Widget for displaying a view."""
    def __init__(self, view=None):
        if view is None:
            self.view = MainUI().view
        else:
            self.view = view
        self.view.on_message.add_observer(self._on_message)
        self._list_walker = urwid.SimpleFocusListWalker(
                [MessageWidget(*text_utils.zephyr_format(msg))
                    for msg in self.view])
        super().__init__(urwid.ListBox(self._list_walker))

    def _on_message(self, msg, idx):
        self._list_walker.insert(
                idx,
                MessageWidget(*text_utils.zephyr_format(msg)))


class MessageWidget(urwid.WidgetWrap):
    """Widget for displaying a single message."""
    def __init__(self, msg_body=None, msg_header=None, indent=4):
        if msg_body is not None:
            body = urwid.Padding(urwid.Text(msg_body), left=indent)
        else:
            body = urwid.Text('')
        if msg_header is not None:
            header = urwid.Text(msg_header)
        else:
            header = urwid.Text('')
        focus_widget = (2, FocusMarkerWidget())
        main_widget = urwid.Pile([('pack', header), ('pack', body)])
        super().__init__(urwid.Columns([focus_widget, main_widget], dividechars=1))

    def selectable(self):
        return True


class FocusMarkerWidget(urwid.WidgetWrap):
    _selectable = True

    def __init__(self):
        self._text = urwid.Text('')
        super().__init__(self._text)

    def keypress(self, size, key):
        return key

    def render(self, size, focus=False):
        self._text.set_text('->' if focus else '')
        return self._text.render(size, focus)


if __name__ == '__main__':
    MainUI()
