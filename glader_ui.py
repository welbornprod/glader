#!/usr/bin/env python3
""" Glader - Gtk GUI
    Provides the user interface for Glader.
    -Christopher Welborn 09-15-2014
"""

import os
import sys
from glader_util import (
    import_fail,
    settings,
    GladeFile,
    NAME, VERSIONSTR, __version__)

try:
    from gi.repository import Gtk, GtkSource, GObject, Pango
except ImportError as eximp:
    import_fail(eximp)


class App(Gtk.Window):

    """ Main window with all components. """

    def __init__(self, filename=None, outputfile=None, dynamic_init=False):
        Gtk.Window.__init__(self)
        self.builder = Gtk.Builder()
        # Register the GtkSourceView type.
        GObject.type_register(GtkSource.View)

        try:
            scriptdir = os.path.abspath(sys.path[0])
            gladefile = os.path.join(scriptdir, 'glader.glade')
            self.builder.add_from_file(gladefile)
        except Exception as ex:
            print('\nError building main window!\n{}'.format(ex))
            sys.exit(1)
        # A GladeFile() instance set by generate_code().
        self.glade = None

        # Get gui objects
        self.btnFileOpen = self.builder.get_object('btnFileOpen')
        if filename:
            # This will automatically trigger code generation
            # because of btnFileOpen_selection_changed_cb()
            self.btnFileOpen.set_filename(filename)

        self.btnGenerate = self.builder.get_object('btnGenerate')
        self.btnSave = self.builder.get_object('btnSave')
        self.chkDynamic = self.builder.get_object('chkDynamic')
        if not dynamic_init:
            # Load from settings if not set already.
            dynamic_init = settings.get_bool('dynamic_init', default=False)
        self.chkDynamic.set_active(dynamic_init)

        self.comboTheme = self.builder.get_object('comboTheme')
        # Initialize the cell renderer for the theme list.
        celltheme = Gtk.CellRendererText()
        self.comboTheme.pack_start(celltheme, True)
        self.comboTheme.add_attribute(celltheme, 'text', 0)
        # List store for the theme names.
        self.listTheme = self.builder.get_object('listTheme')

        self.lblFileOpen = self.builder.get_object('lblFileOpen')

        self.lblOutput = self.builder.get_object('lblOutput')
        self.scrollOutput = self.builder.get_object('scrollOutput')
        # Build the SourceView and SourceBuffer with Python highlighting
        self.bufferOutput = GtkSource.Buffer()
        self.langManager = GtkSource.LanguageManager()
        self.bufferLang = self.langManager.get_language('python3')
        self.bufferOutput.set_language(self.bufferLang)
        self.bufferOutput.set_highlight_syntax(True)
        self.bufferOutput.set_highlight_matching_brackets(True)
        # Set theme.
        self.themeManager = GtkSource.StyleSchemeManager()
        # Map from theme id to StyleScheme.
        self.themes = {
            tid: self.themeManager.get_scheme(tid)
            for tid in self.themeManager.get_scheme_ids()}
        # Holds the currently selected theme info.
        self.theme = None
        # Load theme from config if available.
        if not self.set_theme_config():
            # Use first preferred theme if available.
            themeprefs = (
                'oblivion', 'tomorrownighteighties', 'twilight', 'kate')
            for themeid in themeprefs:
                theme = self.themes.get(themeid, None)
                if theme:
                    self.set_theme(theme)
                    break

        # Load theme names and select the chosen theme.
        self.build_theme_list()

        # Build actual view for the code.
        self.srcviewOutput = self.builder.get_object('srcviewOutput')
        self.srcviewOutput.set_buffer(self.bufferOutput)
        self.srcviewOutput.modify_font(Pango.FontDescription('monospace'))
        # This window.
        self.winMain = self.builder.get_object('winMain')

        # Initialize a MessageBoxes class to work with.
        self.msgs = MessageBoxes(parent=self.winMain, title=NAME)
        self.dlgSave = FileDialogSave(
            parent=self.winMain,
            title='Select an output file',
            filters=(('Python Files', '*.py'), ('All Files', '*')),
            filename=outputfile
        )
        # Connect all signals.
        self.builder.connect_signals(self)

        # Show the main window.
        self.winMain.show_all()

    def btnFileOpen_selection_changed_cb(self, widget, user_data=None):
        """ Handler for btnFileOpen.selection-changed. """
        filename = widget.get_filename()
        if filename:
            # Automatically generate code for selected files.
            self.generate_code()

    def btnGenerate_activate_cb(self, widget, user_data=None):
        """ Handler for btnGenerate.activate. """
        return self.btnGenerate_clicked_cb(user_data=user_data)

    def btnGenerate_clicked_cb(self, widget, user_data=None):
        """ Handler for btnGenerate.clicked """
        return self.generate_code()

    def btnSave_activate_cb(self, widget, user_data=None):
        """ Handler for btnSave.activate. """
        return self.btnSave_clicked_cb(user_data=user_data)

    def btnSave_clicked_cb(self, widget, user_data=None):
        """ Handler for btnSave.activate. """
        return self.write_file()

    def comboTheme_changed_cb(self, widget, user_data=None):
        """ Handler for comboTheme.changed
            Sets the current theme for srcviewOutput.
        """
        # Selected TreeIter.
        selitr = self.comboTheme.get_active_iter()
        if selitr is None:
            return None
        # Value for column 0 (the theme name)
        themename = self.listTheme.get_value(selitr, 0)
        self.set_theme(themename)

    def winMain_destroy_cb(self, widget, user_data=None):
        """ Handler for winMain.destroy. """
        # Try saving some preferences.
        # Setting dynamic_init as a string is not needed with EasySettings,
        # but I am doing it for human-friendly editing reasons.
        # Pickle strings are ugly, and EasySettings.get_bool() will parse it.
        settings.set('dynamic_init', str(self.chkDynamic.get_active()).lower())
        settings.set('theme_id', self.theme.get_id())
        settings.save()
        Gtk.main_quit()

    # Helper functions -----------------------------------------------------
    def build_theme_list(self):
        """ Build the content for self.listTheme based on self.themes.
            Sorts the names first.
        """
        selected = -1
        sort_by_name = lambda k: self.themes[k].get_name()
        themeids = sorted(self.themes, key=sort_by_name)
        themenames = sorted((self.themes[k].get_name() for k in themeids))
        selthemename = self.theme.get_name()
        for i, themename in enumerate(themenames):
            newrow = self.listTheme.append((themename, ))
            self.listTheme.set_value(newrow, 0, themename)
            if themename == selthemename:
                selected = i
        # Set the currently selected theme.
        if selected > -1:
            self.comboTheme.set_active(selected)

    def generate_code(self):
        """ Does the actual glade parsing/code generation. """
        filename = self.btnFileOpen.get_filename()
        if not filename:
            self.msgs.warn('Please select an input file.')
            return None
        elif not os.path.exists(filename):
            self.glade = None
            self.bufferOutput.set_text('')
            self.msgs.warn('Glade file does not exist: {}'.format(filename))
            return None

        dynamic = self.chkDynamic.get_active()
        try:
            gladefile = GladeFile(filename=filename, dynamic_init=dynamic)
        except Exception as ex:
            errfmt = 'Error parsing glade file:\n   {}\n\n{}'
            self.msgs.error(errfmt.format(filename, ex))
            self.glade = None
            return None

        content = gladefile.get_content()
        self.bufferOutput.set_text(content)
        self.glade = gladefile

    def get_theme_by_name(self, name):
        """ Retrieves a StyleScheme from self.themes by it's proper name.
            Like: Kate, or Oblivion.
            Returns None if the theme can't be found.
        """
        for themeid, stylescheme in self.themes.items():
            themename = stylescheme.get_name()
            if name == themename:
                return stylescheme
        return None

    def set_theme(self, scheme_identifier):
        """ Sets the current highlight theme by id, name, or StyleScheme.
            or by prefetched StyleScheme.
            Return True if the theme was set, otherwise False.
        """
        if isinstance(scheme_identifier, str):
            # Id or name?
            theme = self.themes.get(scheme_identifier, None)
            if theme is None:
                # Name.
                theme = self.get_theme_by_name(scheme_identifier)
        elif isinstance(scheme_identifier, GtkSource.StyleScheme):
            # StyleScheme (prefetched)
            theme = scheme_identifier
        else:
            # Unknown type for set_theme().
            errfmt = 'Expected name, id, or StyleScheme. Got: {}'
            raise ValueError(errfmt.format(type(scheme_identifier)))

        if theme is not None:
            self.theme = theme
            self.bufferOutput.set_style_scheme(theme)
            return True
        return False

    def set_theme_config(self):
        """ Try loading a theme from config.
            Return True if a theme was set, otherwise False.
        """
        themeid = settings.get('theme_id', None)
        if themeid:
            return self.set_theme(themeid)

    def write_file(self):
        """ Write the generated code to a file. """
        # Get generated code content.
        content = self.bufferOutput.get_text(
            self.bufferOutput.get_start_iter(),
            self.bufferOutput.get_end_iter(),
            True)

        if not content:
            self.msgs.error('There is nothing to save.')
            return None

        outputfile = self.dlgSave.show()
        if not outputfile:
            return None

        try:
            with open(outputfile, 'w') as f:
                f.write(content)
        except EnvironmentError as ex:
            errfmt = 'There was an error writing to:\n    {}\n\n{}'
            self.msgs.error(errfmt.format(outputfile, ex))
            return None

        msglines = ['File was saved: {}'.format(outputfile)]
        try:
            self.glade.make_executable(outputfile)
            msglines.append('Mode +rwx (774) was set to make it executable.')
        except (PermissionError, EnvironmentError) as experm:
            errfmt = 'Unable to make it executable:\n  {}'
            msglines.append(errfmt.format(experm))

        self.msgs.info('\n'.join(msglines))
        return None


class FileDialogSave(object):

    """ A quick and easy file save dialog. """

    def __init__(self, parent=None, title=None, filters=None, filename=None):
        self.parent = parent
        self.title = title or 'Select a file name'
        self.filters = filters or (('All Files', '*'),)
        # Initial filename to show.
        self.filename = filename

    def _build_filters(self, filters=None):
        """ build dlgwindow filters from list/tuple of filters
            filters = (('Description', '*.type'), ('Desc2', '*.typ2'))
        """
        filters = filters or self.filters
        # use self.filter to build from instead of custom filters
        if filters is None:
            filters = (('All Files', '*'),)

        filefilters = []
        for desc, pat in filters:
            dfilter = Gtk.FileFilter()
            dfilter.set_name(desc)
            dfilter.add_pattern(pat)
            filefilters.append(dfilter)
        return filefilters

    def show(self):
        # Create Dialog.
        dlg = Gtk.FileChooserDialog(
            self.title,
            self.parent,
            Gtk.FileChooserAction.SAVE,
            (
                '_Cancel', Gtk.ResponseType.CANCEL,
                '_Save', Gtk.ResponseType.OK)
        )
        dlg.set_default_response(Gtk.ResponseType.OK)
        if self.filename:
            dlg.set_filename(self.filename)

        # build filters
        for dlgfilter in self._build_filters():
            dlg.add_filter(dlgfilter)

        # Show hidden files
        dlg.set_show_hidden(True)

        # Show Dialog, get response
        response = dlg.run()
        respfile = dlg.get_filename()
        dlg.destroy()
        return respfile if response == Gtk.ResponseType.OK else None


class MessageBoxes(object):

    """ A helper for simple msg dialogs. """

    def __init__(self, parent=None, title=None):
        self.parent = parent
        self.title = title or ''

    def info(self, message):
        dialog = Gtk.MessageDialog(
            self.parent,
            0,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            self.title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def error(self, message, cancel=False):
        btn = Gtk.ButtonsType.CANCEL if cancel else Gtk.ButtonsType.OK
        dialog = Gtk.MessageDialog(
            self.parent,
            0,
            Gtk.MessageType.ERROR,
            btn,
            self.title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def warn(self, message, okcancel=False):
        btns = GtkButtonsType.OK_CANCEL if okcancel else Gtk.ButtonsType.OK
        dialog = Gtk.MessageDialog(
            self.parent,
            0,
            Gtk.MessageType.WARNING,
            btns,
            self.title)
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return True if response == Gtk.ResponseType.OK else False

    def question(self, message):
        dialog = Gtk.MessageDialog(
            self.parent,
            0,
            Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.YES_NO,
            self.title)
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return True if response == Gtk.ResponseType.YES else False


def inspect_object(o):
    """ Prints a repr() and dir() for an object for debugging. """
    print('{!r}:'.format(o))
    fmt = '    {}'.format
    attrs = (fmt(a) for a in dir(o) if not a.startswith('_'))
    print('\n'.join(attrs))


def gui_main(filename=None, outputfile=None, dynamic_init=False):
    """ Main entry point for the program. """
    app = App(
        filename=filename,
        outputfile=outputfile,
        dynamic_init=dynamic_init)
    ret = Gtk.main()
    sys.exit(ret)


if __name__ == '__main__':
    # Won't hurt to run it anyway, but it should really run from glade.py.
    mainret = gui_main()
    sys.exit(mainret)
