#!/usr/bin/env python3
""" Glader - Utilities
    Helper classes for parsing glade files and generating skeleton code.
    -Christopher Welborn 09-14-14
"""
import os.path
import stat
import sys
from datetime import datetime

from glader_templates import get_template

NAME = 'Glader'
__version__ = '0.2.2'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)

# Set with -D,--debug command-line options.
DEBUG = ('-D' in sys.argv) or ('--debug' in sys.argv)


def import_fail(err):
    """ Fail with a friendlier message when imports fail. """
    msglines = (
        '\n{namever} requires some third-party libraries.',
        'Please install requirements using \'pip\' or your package manager.',
        'The import error was:',
        '    {err}\n'
    )
    print(
        '\n'.join(msglines).format(namever=VERSIONSTR, err=err),
        file=sys.stderr,
    )
    sys.exit(1)


try:
    from easysettings import EasySettings
    from gi import require_version as gi_require_version
    gi_require_version('Gtk', '3.0')
    from gi.repository import Gtk
    from lxml import etree
    from lxml.cssselect import CSSSelector
except ImportError as eximp:
    import_fail(eximp)

CONFIGFILE = os.path.join(sys.path[0], 'glader.conf')
settings = EasySettings(CONFIGFILE)
settings.name = NAME
settings.version = __version__

# Template for shebang/imports.
template_header = get_template('header').rstrip()
# Template for the executable section.
template_body = get_template('body')
# Class def for top level classes.
template_cls = get_template('cls').rstrip()
# Function definition for set_object() when dynamic init is used.
template_set_object = get_template('set_object', indent=4).rstrip()

# Xpath to find all <object> elements in a glade file.
xpath_object = CSSSelector('object').path
# Xpath to find all <requires> elements.
xpath_requires = CSSSelector('requires').path
# Xpath to find all <signal> elements.
xpath_signal = CSSSelector('signal').path


class GladeFile(object):

    """ Parses a glade file and generates a python source file based on
        objects and signal handlers found in the xml.
        Signal handler arguments are looked up by inspecting the Gtk
        widgets and their ArgInfo.
        Holds a collection of ObjectInfos with helper methods.

    """

    def __init__(self, filepath=None, dynamic_init=False):
        """ Create a GladeFile to generate code from.
            Arguments:
                filepath      : File to parse.
                dynamic_init  : If true, generated code will dynamically
                                create objects:
                                    objects = ('obj1', 'obj2')
                                    for objname in objects:
                                        self.set_object(objname)

                                Otherwise, the normal method will be used:
                                    self.obj = self.builder.get_object('obj')

                                Both achieve the same end result.
        """
        self.filepath = filepath
        self.dynamic_init = dynamic_init

        self.tree = None
        self.top_levels = []
        self.objects = []
        self.requires = []
        self.main_win = None
        self.parse_file(filepath)

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
        return (
            '{filepath}: {objects} objects with {handlers} handlers'.format(
                filepath=self.filepath,
                objects=len(self.objects),
                handlers=sum((len(o.signals) for o in self.objects))
            )
        )

    def extra_requires(self):
        """ Returns any extra Requires (not Gtk, and not empty). """
        return [r for r in self.requires if r.lib and (r.lib != 'gtk+')]

    def extra_requires_msg(self):
        """ Returns a warning message about extra Requires if any are found,
            otherwise returns an empty string.
        """
        reqs = self.extra_requires()
        if not reqs:
            return ''
        return '\n'.join((
            'This file depends on extra libraries:',
            '\n'.join(f'    {r.init_code()}' for r in reqs),
            '\nYou may need to register them with:',
            '    GObject.type_register(<widget class>)',
            '\nYou may also need to use a different name in the',
            'gi_require_version() call.',
        ))

    def get_content(self, lib_mode=False):
        """ Renders the main template with current GladeFile info.
            Returns a string that can be written to file.
        """
        if lib_mode:
            return '\n\n'.join((
                template_header.format(
                    requires=self.init_requires(),
                    date=datetime.today().strftime('%m-%d-%Y')
                ),
                self.main_win.get_class_content(
                    dynamic_init=self.dynamic_init,
                ),
            ))
        return '\n\n'.join((
            template_header.format(
                requires=self.init_requires(),
                date=datetime.today().strftime('%m-%d-%Y')
            ),
            template_body.format(
                class_def=self.main_win.get_class_content(
                    dynamic_init=self.dynamic_init,
                ),
            ),
        ))

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
        windows = [
            o
            for o in self.objects
            if ('win' in o.name.lower()) or ('Window' in o.widget)
        ]
        if not windows:
            return ObjectApp(name='?MainWindow?')

        if len(windows) > 1:
            # Search for any 'main' window.
            for win in windows:
                if 'main' in win.name.lower():
                    return ObjectApp.from_object_info(
                        win,
                        filepath=self.filepath,
                    )

        # Can't find a 'main' window. Return the first one.
        return ObjectApp.from_object_info(windows[0], filepath=self.filepath)

    def init_requires(self):
        """ Returns init code for all extra Requires. """
        return '\n'.join(r.init_code() for r in self.extra_requires())

    def make_executable(self, filepath=None):
        """ Make a file executable, by setting mode 774. """
        filepath = filepath or self.filepath
        # chmod 774
        mode774 = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH
        os.chmod(filepath, mode774)

    def names(self):
        """ Return a list of all object names. """
        return sorted([o.name for o in self.objects])

    def parse_file(self, filepath=None):
        self.filepath = filepath
        self.tree = None
        if filepath:
            self.tree = etree.parse(filepath)
            self.top_levels = self.objects_top_level()
            self.objects = self.objects_all()
            self.requires = self.objects_requires()
            self.main_win = self.get_main_window()

    def objects_all(self):
        """ This will return ALL objects, without any hierarchy. """
        if self.tree is None:
            return []
        objectelems = self.tree.xpath(xpath_object)
        if not objectelems:
            raise ValueError('No objects found.')

        # Remove separator/ignored objects.
        return ObjectInfo.map_elements(objectelems)

    def objects_requires(self):
        """ Returns all Require()s found in the tree. """
        if self.tree is None:
            return []
        requireselems = self.tree.xpath(xpath_requires)
        if not requireselems:
            return []
        return [Requires.from_element(e) for e in requireselems]

    def objects_top_level(self):
        """ Returns only top-level ObjectInfo()s. """
        if self.tree is None:
            return []
        objectelems = self.tree.findall('object')
        objects = [ObjectInfo.from_element(e) for e in objectelems]
        # Remove separator objects.
        return [o for o in objects if o and not o.is_ignored()]

    def write_file(self, filepath=None):
        """ Write parsed info to a file. """
        filepath = filepath or self.filepath
        content = self.get_content()
        with open(filepath, 'w') as f:
            f.write(content)

        self.make_executable(filepath)
        return filepath


class ObjectInfo(object):
    """ Holds information about a widget/object and it's signals, with helper
        methods.
    """
    def __init__(
            self, name=None, widget=None, objects=None, signals=None,
            siblings=None, tree=None):
        self.name = name
        self.is_separator = self.name and self.name.startswith('<')
        self.widget = widget
        self.signals = signals or []
        self.tree = None if tree is None else tree
        # Child objects.
        self.objects = objects or []
        # Sibling objects.
        self.siblings = siblings or []

    def __repr__(self):
        """ Return a repr() for this object and it's signal handlers. """
        return self.repr_fmt()

    @classmethod
    def from_element(cls, element):
        """ Builds an ObjectInfo from an object's lxml element.
            Returns None if an id/name can't be found.
        """
        # User's name for the widget.
        objname = element.get('id', None)
        if not objname:
            debug('Element has no id: {!r}'.format(element))
            return None
        # Widget type.
        widget = element.get('class', None)

        # Children.
        children_objs = []
        for childelem in element.findall('child'):
            children_objs.extend(
                ObjectInfo.map_elements(childelem.findall('object'))
            )

        # Signal handlers.
        signalelems = element.xpath(xpath_signal)
        if signalelems:
            signals = []
            for sigelem in signalelems:
                handler = SignalHandler.from_element(
                    sigelem,
                    widgettype=widget
                )

                if handler is not None:
                    # from_element() returns None for 'gtk_' signals.
                    signals.append(handler)
        else:
            signals = []

        # Siblings
        sibling_elems = [
            e
            for e in element.getparent().findall('object')
            if e.get('id', None) != objname
        ]
        siblings = ObjectInfo.map_elements(sibling_elems)
        objinfo = cls(
            name=objname,
            widget=widget,
            objects=children_objs,
            signals=signals,
            siblings=siblings,
            tree=element,
        )
        return objinfo

    def get_signal(self, name, default=None):
        """ Get signal handler by handler (signal.handler). """
        for h in self.signals:
            if h.handler == name:
                return h
        return default

    def has_children(self):
        return bool(self.objects)

    def init_code(self, indent=0):
        """ Return string to initialize this object.
            Example: self.winMain = self.builder.get_object('winMain')
        """
        template = '{spaces}self.{name} = self.builder.get_object(\'{name}\')'
        return template.format(spaces=' ' * indent, name=self.name)

    def init_codes(self, indent=0, objects=None):
        """ Return a string to initialize all child objects. """
        return '\n'.join(sorted(
            o.init_code(indent=indent)
            for o in objects or self.objects
        ))

    def is_ignored(self):
        """ Returns True if this object should be ignored when generating
            init code, for Separators and GtkBoxes.
        """
        ignored_classes = ('GtkBox', )
        return self.name.startswith('<') or (self.widget in ignored_classes)

    @classmethod
    def map_elements(cls, elements):
        for elem in elements:
            o = cls.from_element(elem)
            if (not o) or o.is_ignored():
                continue
            yield o

    def names(self, all_objects=False):
        """ Return a list of all object names. """
        return sorted([
            o.name
            for o in (self.objects_all() if all_objects else self.objects)
        ])

    def objects_all(self):
        """ This will return ALL objects, without any hierarchy. """
        if self.tree is None:
            return []
        objectelems = self.tree.xpath(xpath_object)
        if not objectelems:
            return []

        return list(ObjectInfo.map_elements(objectelems))

    def repr_fmt(self, indent=0):
        return '\n'.join(self.repr_lines(indent=indent))

    def repr_lines(self, indent=0):
        spaces = ' ' * indent
        lines = [
            f'{spaces}{self.name} ({self.widget}):',
        ]
        lines.extend((
            f'{spaces}    {x!r}'
            for x in self.signals
        ))
        lines.extend((
            f'{spaces}    {o.repr_fmt(indent=indent+4)}'
            for o in self.objects
        ))
        return lines

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


class ObjectClass(ObjectInfo):
    """ Holds information about an ObjectInfo that should generate a separate
        class definition.
    """
    use_class_name = None

    def __init__(
            self, filepath=None, name=None, widget=None, objects=None,
            signals=None, siblings=None, tree=None):
        super().__init__(
            name=name,
            widget=widget,
            objects=objects,
            signals=signals,
            siblings=siblings,
            tree=tree,
        )
        self.filepath = filepath or None

    def format_tuple_names(self, names, indent=12):
        """ Format object names as if they were inside a tuple definition. """
        spaces = ' ' * indent
        return '\n'.join((
            f'{spaces}\'{n}\','
            for n in names
        ))

    @classmethod
    def from_object_info(cls, objinfo, filepath=None):
        """ Promote an ObjectInfo to a ObjectApp.
            This is simply changing the class from ObjectInfo to ObjectApp,
            to take advantage of it's helper methods for the main window.
        """
        return cls(
            filepath=filepath,
            name=objinfo.name,
            widget=objinfo.widget,
            objects=objinfo.objects,
            siblings=objinfo.siblings,
            signals=objinfo.signals,
            tree=objinfo.tree,
        )

    def get_class_content(self, dynamic_init=False, objects=None):
        """ Renders the app template with current GladeFile info.
            Returns a string that can be written to file.
        """
        if dynamic_init:
            template = """guinames = (
{}
        )
        for objname in guinames:
            self.set_object(objname)"""
            objects = template.format(
                self.format_tuple_names(
                    objects or self.objects_all(),
                    indent=12
                )
            )
            setobj_def = f'\n{template_set_object}\n'
        else:
            # Regular init.
            objects = self.init_codes(
                indent=8,
                objects=objects or self.objects_all(),
            ).lstrip()
            setobj_def = ''

        return template_cls.format(
            classname=self.use_class_name or self.name.title(),
            filepath=self.filepath,
            widget=self.widget.replace('Gtk', ''),
            objects=objects,
            set_object_def=setobj_def,
            init_end=self.init_end() or '',
            signaldefs=self.signal_defs(indent=4).rstrip(),
        )

    def init_end(self):
        return None


class ObjectApp(ObjectClass):
    """ Holds information about the main App class, which in turn contains
        possible children with separate classes.
    """
    use_class_name = 'App'

    def get_class_content(self, dynamic_init=False, objects=None):
        if not objects:
            # Use object_all() and siblings for the App class.
            objects = self.objects_all()
            # Sibling init code should be 'self.thing = Thing()',
            # ....not builder.get_object('thing')
            # Also, the classes need to be generated.
            objects.extend(self.siblings)
        return super().get_class_content(
            dynamic_init=dynamic_init,
            objects=objects,
        )

    def init_end(self):
        return f'self.{self.name}.show_all()'


class Requires(object):
    """ Holds ifnormation and helper methods for a <requires> element. """
    def __init__(self, lib=None, version=None):
        self.lib = lib or ''
        self.version = version or ''

    def __bool__(self):
        return self.lib or self.version

    def __repr__(self):
        return f'{type(self).__name__}: {self.lib!r} v. {self.version!r}'

    @classmethod
    def from_element(cls, element):
        lib = element.get('lib', None)
        ver = element.get('version', None)
        libmap = {
            'gtksourceview': 'GtkSource',
        }
        return cls(lib=libmap.get(lib, lib), version=ver)

    def init_code(self):
        if (not self.lib) or self.lib.startswith('gtk+'):
            return None
        return f'gi_require_version(\'{self.lib}\', \'{self.version}\')'


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
            debug('Ignoring GTK signal handler for: {!r}'.format(element))
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


def debug(*args, **kwargs):
    if not DEBUG:
        return None
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)
