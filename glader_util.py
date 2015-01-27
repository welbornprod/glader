#!/usr/bin/env python3
""" Glader - Utilities
    Helper classes for parsing glade files and generating skeleton code.
    -Christopher Welborn 09-14-14
"""
NAME = 'Glader'
__version__ = '0.0.1-4'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)


def import_fail(err):
    """ Fail with a friendlier message when imports fail. """
    msglines = (
        '\n{namever} requires some third-party libraries.',
        'Please install requirements using \'pip\' or your package manager.',
        'The import error was:',
        '    {err}\n'
    )
    print('\n'.join(msglines).format(namever=VERSIONSTR, err=err))
    sys.exit(1)

import os.path
import stat
import sys
from datetime import datetime

try:
    from easysettings import EasySettings
    from gi.repository import Gtk
    from lxml import etree
    from lxml.cssselect import CSSSelector
except ImportError as eximp:
    import_fail(eximp)

CONFIGFILE = os.path.join(sys.path[0], 'glader.conf')
settings = EasySettings(CONFIGFILE)
settings.name = NAME
settings.version = __version__


class GladeFile(object):

    """ Parses a glade file and generates a python source file based on
        objects and signal handlers found in the xml.
        Signal handler arguments are looked up by inspecting the Gtk
        widgets and their ArgInfo.
        Holds a collection of ObjectInfos with helper methods.

    """
    # Xpath to find all <object> elements in a glade file.
    xpath_object = CSSSelector('object').path

    # Main template for output file.
    template = """#!/usr/bin/env python3
\"\"\"
        ...
        {date}
\"\"\"

import os
import sys
from gi.repository import Gtk

NAME = 'GtkApp'
__version__ = '0.0.1'
VERSIONSTR = '{{}} v. {{}}'.format(NAME, __version__)

class App(Gtk.Window):
    \"\"\" Main window with all components. \"\"\"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.builder = Gtk.Builder()
        try:
            gladefile = '{filename}'
            self.builder.add_from_file(gladefile)
        except Exception as ex:
            print('\\nError building main window!\\n{{}}'.format(ex))
            sys.exit(1)

        # Get gui objects
{objects}

        # Connect all signals.
        self.builder.connect_signals(self)

        # Show the main window.
        self.{mainwindow}.show_all()

{set_object_def}{signaldefs}


def main():
    \"\"\" Main entry point for the program. \"\"\"
    app = App()
    ret = Gtk.main()
    sys.exit(ret)


if __name__ == '__main__':
    mainret = main()
    sys.exit(mainret)
"""

    # Function definition for set_object() when dynamic init is used.
    set_object_def = """
    def set_object(self, objname):
        \"\"\" Try building an object by it's name. \"\"\"

        if objname:
            obj = self.builder.get_object(objname)
            if obj:
                setattr(self, objname, obj)
            else:
                print('\\nError setting object!: {{}}'.format(objname))

"""

    def __init__(self, filename=None, dynamic_init=False):
        """ Create a GladeFile to generate code from.
            Arguments:
                filename      : File to parse.
                dynamic_init  : If true, generated code will dynamically
                                create objects:
                                    objects = ('obj1', 'obj2')
                                    for objname in objects:
                                        self.set_object(objname)

                                Otherwise, the traditional method will be used:
                                    self.obj = self.builder.get_object('obj')

                                Both achieve the same end result.
        """
        self.filename = filename
        self.dynamic_init = dynamic_init

        if filename:
            self.objects = GladeFile.objects_from_glade(filename)
        else:
            self.objects = []

    def __bool__(self):
        """ bool(GladeFile) is based on object count.
            No objects = False
        """
        return bool(self.objects)

    def __repr__(self):
        """ Return a repr() for this GladeFile for debugging purposes. """
        return '\n'.join((repr(o) for o in self.objects))

    def __str__(self):
        """ Return a str() for this GladeFile. """
        return '{filename}: {objects} objects with {handlers} handlers'.format(
            filename=self.filename,
            objects=len(self.objects),
            handlers=sum((len(o.signals) for o in self.objects))
        )

    def format_tuple_names(self, indent=12):
        """ Format object names as if they were inside a tuple definition. """
        fmtname = '{space}\'{{name}}\','.format(space=' ' * indent)
        return '\n'.join((fmtname.format(name=n) for n in self.names()))

    def get_content(self):
        """ Renders the main template with current GladeFile info.
            Returns a string that can be written to file.
        """
        if self.dynamic_init:
            template = """        guinames = (
{}
        )
        for objname in guinames:
            self.set_object(objname)"""

            objects = template.format(self.format_tuple_names(indent=12))
            setobj_def = GladeFile.set_object_def
        else:
            # Regular init.
            objects = self.init_codes(indent=8)
            setobj_def = ''

        return GladeFile.template.format(
            date=datetime.today().strftime('%m-%d-%Y'),
            filename=self.filename,
            objects=objects,
            set_object_def=setobj_def,
            signaldefs=self.signal_defs(indent=4),
            mainwindow=self.get_main_window()
        )

    def get_object(self, name, default=None):
        """ Retrieve an ObjectInfo by object name. """
        for o in self.objects:
            if o.name == name:
                return o
        return default

    def get_main_window(self):
        """ Inspect all objects, return the name for the first one that
            looks like the main window object.
            Returns '?MainWindow?' on failure, so any generated code
            will immediately raise an exception when ran.
        """
        windows = [o.name for o in self.objects if 'win' in o.name.lower()]
        if not windows:
            return '?MainWindow?'
        if len(windows) == 1:
            # Only one win object.
            return windows[0]
        # Search for any 'main' window.
        for winname in windows:
            if 'main' in winname.lower():
                return winname

        # Can't find a 'main' window. Return the first one.
        return windows[0]

    def init_codes(self, indent=12):
        """ Returns concatenated init code for all objects. """
        spacing = ' ' * indent
        joiner = '\n{}'.format(spacing).join
        # Sorts the initialization code based on object name.
        initcodes = []
        for objname in self.names():
            obj = self.get_object(objname)
            initcodes.append(obj.init_code())

        return '{}{}'.format(
            spacing,
            joiner(initcodes))

    def make_executable(self, filename=None):
        """ Make a file executable, by setting mode 774. """
        filename = filename or self.filename
        # chmod 774
        mode774 = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH
        os.chmod(filename, mode774)

    def names(self):
        """ Return a list of all object names. """
        return sorted([o.name for o in self.objects])

    @classmethod
    def objects_from_glade(cls, filename):
        """ Returns a list of ObjectInfo parsed from a glade file.
            Possibly raises errors from etree.parse(),
            or ValueError when no objects are found.
        """
        tree = etree.parse(filename)
        objectelems = tree.xpath(cls.xpath_object)
        if not objectelems:
            raise ValueError('No objects found.')

        return [ObjectInfo.from_element(e) for e in objectelems]

    def signal_defs(self, indent=4):
        """ Returns concatenated signal definitions for all objects. """
        # Sort the signal defs by object name.
        signaldefs = []
        for objname in self.names():
            o = self.get_object(objname)
            signaldef = o.signal_defs(indent=indent)
            if signaldef.strip():
                signaldefs.append(signaldef)
        return '\n\n'.join(signaldefs)

    def write_file(self, filename=None):
        """ Write parsed info to a file. """
        filename = filename or self.filename
        content = self.get_content()
        with open(filename, 'w') as f:
            f.write(content)

        self.make_executable(filename)
        return filename


class ObjectInfo(object):

    """ Holds information about a widget/object and it's signals, with helper
        methods.
    """

    def __init__(self, name=None, widget=None, signals=None):
        self.name = name
        self.widget = widget
        self.signals = signals or []

    def __repr__(self):
        """ Return a repr() for this object and it's signal handlers. """
        lines = ['{} ({}):'.format(self.name, self.widget)]
        handlerfmt = '    {}'.format
        lines.extend((handlerfmt(repr(x)) for x in self.signals))
        return '\n'.join(lines)

    @classmethod
    def from_element(cls, element):
        """ Builds an ObjectInfo from an object's lxml element.
            Returns None if an id/name can't be found.
        """
        # User's name for the widget.
        objname = element.get('id', None)
        if not objname:
            return None
        # Widget type.
        widget = element.get('class', None)

        # Signal handlers.
        signalelems = element.findall('signal')
        if signalelems:
            signals = []
            for sigelem in signalelems:
                handler = SignalHandler.from_element(
                    sigelem,
                    widgettype=widget)

                if handler is not None:
                    # from_element() returns None for 'gtk_' signals.
                    signals.append(handler)
        else:
            signals = []
        return cls(name=objname, widget=widget, signals=signals)

    def get_signal(self, name, default=None):
        """ Get signal handler by handler (signal.handler). """
        for h in self.signals:
            if h.handler == name:
                return h
        return default

    def init_code(self):
        """ Return string to initialize this object.
            Example: self.winMain = self.builder.get_object('winMain')
        """
        template = 'self.{name} = self.builder.get_object(\'{name}\')'
        return template.format(name=self.name)

    def signal_defs(self, indent=4):
        """ Return concatenated function definitions for all signal handlers,
            or if no signal handlers are present then return ''.
            Definitions are sorted by handler name.
        """
        # Sort the signal definitions by handler name.
        signaldefs = []
        for handlername in self.signal_handlers():
            signal = self.get_signal(handlername)
            signaldef = signal.signal_def(indent=indent)
            if signaldef.strip():
                signaldefs.append(signaldef)
        return '\n\n'.join(signaldefs)

    def signal_handlers(self):
        """ Return a sorted list of signal handler names. """
        return sorted((x.handler for x in self.signals))


class SignalHandler(object):

    """ Holds information and helper methods for a single signal handler. """

    def __init__(self, name=None, handler=None, widget=None, widgettype=None):
        # The signal name (pressed, clicked, move-cursor)
        self.name = name
        # The handler's name (mybutton_clicked_cb)
        self.handler = handler
        # This is a computed widget name. (would be mybutton, from above.)
        self.widget = widget
        # This is a Gtk widget type (GtkButton, or just Button)
        self.widgettype = widgettype

    def __repr__(self):
        """ Return a repr() for this signal handler. """
        return '{}.{}'.format(self.widget, self.handler)

    @classmethod
    def from_element(cls, element, widgettype=None):
        """ Build a SignalHandler from an lxml element.
            Arguments:
                element  : An lxml element for a <signal>.
                widget   : A known Gtk widget type.
        """
        eventname = element.get('name', None)
        handlername = element.get('handler', '')
        if handlername.lower().startswith('gtk'):
            return None
        widgetname = handlername.split('_')[0]
        return cls(
            name=eventname,
            handler=handlername,
            widget=widgetname,
            widgettype=widgettype)

    def get_args(self):
        """ Get known arguments for an object/widget and this signal.
            Returns an tuple of default args if none are found.
        """
        defaultargs = ('self', 'widget', 'user_data=None')
        if not self.widgettype:
            return defaultargs

        if self.widgettype.startswith('Gtk'):
            # Actual classes do not start with 'Gtk'.
            gtkname = self.widgettype[3:]
        else:
            gtkname = self.widgettype

         # Find the widget class in Gtk.
        widget = getattr(Gtk, gtkname, None)

        # Find the event handler function info for the widget.
        # 'move-cursor' becomes Gtk.WidgetThing.do_move_cursor
        eventfunc = 'do_{}'.format(self.name.replace('-', '_'))
        widgetevent = getattr(widget, eventfunc, None)
        # Get argument info.
        if hasattr(widgetevent, 'get_arguments'):
            # Return default and known args.
            knownargs = (ai.get_name() for ai in widgetevent.get_arguments())
            formattedargs = ['self', 'widget']
            if knownargs:
                formattedargs.extend(knownargs)
            formattedargs.append('user_data=None')
            return tuple(formattedargs)

        # No argument info for this widget/event.
        return defaultargs

    def signal_def(self, indent=4):
        """ Returns the function definition for this handler,
            including known arguments to this event if found.
            Arguments:
                indent : Amount of space before the definition.
        """
        template = '\n'.join((
            '{space}def {handler}({eventargs}):',
            '{space2}{docs}',
            '{space2}{content}'))
        doctemplate = '""" Handler for {widgetname}.{eventname}. """'
        # Use the user's widget name, the intial Gtk widgetname, or 'widget'.
        widgetname = self.widget or (self.widgettype or 'widget')
        docs = doctemplate.format(widgetname=widgetname, eventname=self.name)
        # Get known arguments for this handler/widget combo.
        eventargs = ', '.join(self.get_args())

        if ('win' in self.widget) and (self.name == 'destroy'):
            # Automatically handle win_destroy.
            # This could backfire if there is more than one win_destroy,
            # and the user forgets to write their own handlers.
            content = 'Gtk.main_quit()'
        else:
            content = 'pass'

        spacing = ' ' * indent
        return template.format(
            space=spacing,
            space2=spacing * 2,
            handler=self.handler,
            docs=docs,
            eventargs=eventargs,
            content=content)
