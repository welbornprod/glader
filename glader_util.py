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
# Class def for sibling window classes.
template_cls_sub = get_template('cls_sub').rstrip()
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
        self.app_win = None
        self.parse_file(filepath)

    def __bool__(self):
        """ bool(GladeFile) is based on object count.
            No objects = False
        """
        return bool(self.objects)

    def __repr__(self):
        """ Return a repr() for this GladeFile for debugging purposes. """
        return '\n'.join((
            f'{self.filepath}:',
            self.app_win.repr_fmt(indent=4),
        ))

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
        class_defs = '\n\n\n'.join((
            self.app_win.get_class_content(
                dynamic_init=self.dynamic_init,
            ),
            self.app_win.get_classes_content(
                dynamic_init=self.dynamic_init,
            ),
        ))
        if lib_mode:
            return '\n\n'.join((
                template_header.format(
                    requires=self.init_requires(),
                    date=datetime.today().strftime('%m-%d-%Y')
                ),
                class_defs,
            ))
        return '\n\n'.join((
            template_header.format(
                requires=self.init_requires(),
                date=datetime.today().strftime('%m-%d-%Y')
            ),
            template_body.format(class_def=class_defs),
        )).replace('\n\n\n\n', '\n\n')

    def get_object(self, name, default=None):
        """ Retrieve an ObjectInfo by object name. """
        for o in self.objects:
            if o.name == name:
                return o
        return default

    def get_app_window(self):
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
                        self.filepath,
                    )

        # Can't find a 'main' window. Return the first one.
        return ObjectApp.from_object_info(windows[0], self.filepath)

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
            self.app_win = self.get_app_window()

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
    init_args = (
        'name',
        'widget',
        'objects',
        'signals',
        'siblings',
        'tree',
    )
    # Classes that can be promoted to ObjectClass, to generate class defs.
    win_classes = [
        f'Gtk{name}'
        for name in dir(Gtk)
        if name.endswith(('Window', 'Dialog', 'Assistant'))
    ]

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

    def __hash__(self):
        return hash(f'{self.widget}{self.name}{self.tree}')

    def __repr__(self):
        """ Return a repr() for this object and it's signal handlers. """
        return self.repr_fmt()

    def __str__(self):
        return self.name

    @classmethod
    def from_element(cls, element):
        objinfo = cls()
        return objinfo.parse_element(element)

    def parse_element(self, element):
        """ Builds an ObjectInfo from an object's lxml element.
            Returns None if an id/name can't be found.
        """
        # User's name for the widget.
        objname = element.get('id', None)
        if not objname:
            # Element has no id, we don't need it to generate code.
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
        signals = list(SignalHandler.map_elements(signalelems))

        self.name = objname
        self.widget = widget
        self.objects = children_objs
        self.signals = signals
        self.tree = element

        return self

    def init_code(self, indent=0, self_init=False):
        """ Return string to initialize this object.
            Example: self.winMain = self.builder.get_object('winMain')
        """
        spaces = ' ' * indent
        n = self.name
        return f'{spaces}self.{n} = self.builder.get_object(\'{n}\')'

    def init_codes(self, indent=0, objects=None):
        """ Return a string to initialize all child objects. """
        return '\n'.join(sorted(
            o.init_code(indent=indent, self_init=(o.name == self.name))
            for o in objects or self.objects
        ))

    def is_class(self, objinfo):
        """ Returns True of `objinfo` is a sibling of this ObjectInfo. """
        return isinstance(objinfo, ObjectClass) and (objinfo in self.siblings)

    def is_ignored(self):
        """ Returns True if this object should be ignored when generating
            init code, for Separators and GtkBoxes.
        """
        ignored_classes = ('GtkBox', )
        return (
            self.name.startswith('<') or
            (self.widget in ignored_classes)
        )

    def kwargs(self):
        return {k: getattr(self, k) for k in self.init_args}

    @classmethod
    def map_elements(cls, elements, ignore=None):
        ignore_hashes = set(hash(o) for o in (ignore or []))
        for elem in elements:
            o = cls.from_element(elem)
            if (not o) or o.is_ignored():
                continue
            if hash(o) in ignore_hashes:
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

        return list(ObjectInfo.map_elements(objectelems, ignore=(self,)))

    def repr_fmt(self, indent=0):
        return '\n'.join(self.repr_lines(indent=indent))

    def repr_lines(self, indent=0):
        spaces = ' ' * indent
        typename = type(self).__name__
        reportedsignals = set()
        has_children = bool(self.signals) or bool(self.objects)
        colon = ':' if has_children else ''
        lines = [
            f'{spaces}{self.name} ({typename}: {self.widget}){colon}',
        ]
        # Signals
        for x in self.signals:
            if x in reportedsignals:
                continue
            lines.append(f'{spaces}{x.repr_fmt(indent=indent)}')
            reportedsignals.add(x)
        # Objects
        lines.extend((
            f'{spaces}{o.repr_fmt(indent=indent)}'
            for o in self.objects
        ))
        return lines

    def signal_defs(self, indent=4):
        """ Return concatenated function definitions for all signal handlers,
            or if no signal handlers are present then return ''.
            Definitions are sorted by handler name.
        """
        # Signal definitions, no dupes. First one wins.
        signaldefs = {}
        for signal in reversed(self.signals):
            signaldef = signal.signal_def(indent=indent)
            if not signaldef.strip():
                debug(f'No signal def for: {signal!r}')
                continue
            signaldefs[signal.handler] = signaldef
        # Sort them.= by handler name.
        return '\n\n'.join(signaldefs[k] for k in sorted(signaldefs))


class ObjectClass(ObjectInfo):
    """ Holds information about an ObjectInfo that should generate a separate
        class definition.
    """
    use_class_name = None
    init_args = (
        'filepath',
        'name',
        'widget',
        'objects',
        'signals',
        'siblings',
        'tree',
    )

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
            for n in sorted(names)
        ))

    @classmethod
    def from_object_info(cls, objinfo, filepath):
        """ Promote an ObjectInfo to a ObjectApp.
            This is simply changing the class from ObjectInfo to ObjectApp,
            to take advantage of it's helper methods for the main window.
        """
        kwargs = objinfo.kwargs()
        kwargs['filepath'] = filepath
        return cls(**kwargs)

    def get_class_content(
            self, dynamic_init=False, objects=None, extra_classes=None):
        """ Renders the class template with current GladeFile info.
            Returns a string that can be written to file.
        """
        if not objects:
            objects = [self]
            objects.extend(self.objects_all())

        if dynamic_init:
            template = """
        for obj in self.builder.get_objects():
            self.set_object(Gtk.Buildable.get_name(obj))"""
            object_inits = template.format(
                self.format_tuple_names(
                    (o.name for o in objects),
                    indent=12
                )
            )

            setobj_def = f'\n{template_set_object}\n'
        else:
            # Regular init.
            object_inits = self.init_codes(
                indent=8,
                objects=objects,
            ).lstrip()
            setobj_def = ''

        clsname = ''.join((self.name[0].upper(), self.name[1:]))
        return template_cls_sub.format(
            classname=self.use_class_name or clsname,
            filepath=self.filepath,
            widget=self.widget.replace('Gtk', ''),
            objnames=self.format_tuple_names(
                (o.name for o in objects if not self.is_class(o)),
                indent=20,
            ),
            objects=object_inits,
            init_end='',
            set_object_def=setobj_def,
            signal_defs=self.signal_defs(indent=4).rstrip(),
        ).replace('\n        \n', '\n')

    def get_classes(self):
        return [o for o in self.siblings if isinstance(o, ObjectClass)]

    def init_code(self, indent=0, self_init=False):
        """ Return string to initialize this object.
            Example: self.winTest = WinTest()
        """
        if self_init:
            return ObjectInfo.init_code(self, indent=indent)
        spaces = ' ' * indent
        attrname = ''.join((self.name[0].lower(), self.name[1:]))
        clsname = ''.join((self.name[0].upper(), self.name[1:]))
        return f'{spaces}self.{attrname} = {clsname}()'


class ObjectApp(ObjectClass):
    """ Holds information about the main App class, which in turn contains
        possible children with separate classes.
    """
    use_class_name = 'App'

    @classmethod
    def from_object_info(cls, objinfo, filepath):
        kwargs = objinfo.kwargs()
        kwargs['filepath'] = filepath
        app = cls(**kwargs)
        # Get siblings.

        # Siblings
        sibling_elems = [
            e
            for e in objinfo.tree.getparent().findall('object')
            if e.get('id', None) != app.name
        ]
        app.siblings = list(ObjectInfo.map_elements(sibling_elems))
        # Promote siblings to ObjectClass where needed.
        for i, sibling in enumerate(app.siblings[:]):
            if sibling.widget in cls.win_classes:
                siblingargs = sibling.kwargs()
                siblingargs['filepath'] = filepath
                app.siblings[i] = ObjectClass(**siblingargs)
        return app

    def get_class_content(self, dynamic_init=False, objects=None):
        if not objects:
            # Use object_all() and siblings for the App class.
            objects = [self]
            objects.extend(self.objects_all())
            # Sibling init code should be 'self.thing = Thing()',
            # ....not builder.get_object('thing')
            # Also, the classes need to be generated.
            objects.extend(self.siblings)

        if dynamic_init:
            template = """
        for obj in self.builder.get_objects():
            self.set_object(Gtk.Buildable.get_name(obj))"""
            object_inits = '\n\n'.join((
                template.format(
                    self.format_tuple_names(
                        (o.name for o in objects),
                        indent=12
                    )
                ),
                self.init_codes(indent=8, objects=self.get_classes()),
            ))
            setobj_def = f'\n{template_set_object}\n'
        else:
            # Regular init.
            object_inits = self.init_codes(
                indent=8,
                objects=objects,
            ).lstrip()
            setobj_def = ''

        clsname = ''.join((self.name[0].upper(), self.name[1:]))
        use_template = template_cls_sub if self.siblings else template_cls
        return use_template.format(
            classname=self.use_class_name or clsname,
            filepath=self.filepath,
            widget=self.widget.replace('Gtk', ''),
            objnames=self.format_tuple_names(
                (o.name for o in objects if not self.is_class(o)),
                indent=20,
            ),
            objects=object_inits,
            init_end=f'self.{self.name}.show_all()',
            set_object_def=setobj_def,
            signal_defs=self.signal_defs(indent=4).rstrip(),
        ).replace('\n        \n', '\n')

    def get_classes_content(self, dynamic_init=False):
        return '\n\n\n'.join(
            o.get_class_content(dynamic_init=dynamic_init)
            for o in self.get_classes()
        )

    def init_code(self, indent=0, self_init=False):
        return ObjectInfo.init_code(self, indent=indent)

    def repr_fmt(self, indent=0):
        return '\n'.join(self.repr_lines(indent=indent))

    def repr_lines(self, indent=0):
        spaces = ' ' * indent
        lines = super().repr_lines(indent=indent)
        lines.extend(o.repr_fmt(indent) for o in self.objects_all())
        siblings = [o.repr_fmt(indent) for o in self.get_classes()]
        if siblings:
            lines.append(f'{spaces}Siblings:')
            lines.extend(siblings)
        return lines


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

    def __init__(
            self, name=None, handler=None, widget=None, widgettype=None,
            element=None):
        # The signal name (pressed, clicked, move-cursor)
        self.name = name
        # The handler's name (mybutton_clicked_cb)
        self.handler = handler
        # This is a computed widget name. (would be mybutton, from above.)
        self.widget = widget
        # This is a Gtk widget type (GtkButton, or just Button)
        self.widgettype = widgettype
        # This is the event name for Gtk events.
        self.event = ''.join((
            'do_',
            self.name.replace('-', '_')
        ))
        self.element = element

    def __repr__(self):
        """ Return a repr() for this signal handler. """
        return self.repr_fmt()

    @classmethod
    def from_element(cls, element, widgettype=None):
        """ Build a SignalHandler from an lxml element.
            Arguments:
                element  : An lxml element for a <signal>.
                widget   : A known Gtk widget type.
        """
        eventname = element.get('name', None)
        handlername = element.get('handler', '')
        parentelem = element.getparent()
        widgettype = widgettype or parentelem.get('class', None)

        widgetid = parentelem.get('id', None)
        if handlername.lower().startswith('gtk'):
            debug('Ignoring GTK signal handler for: {!r}'.format(element))
            return None

        return cls(
            name=eventname,
            handler=handlername,
            widget=widgetid or handlername.split('_')[0],
            widgettype=widgettype,
            element=element,
        )

    def full_widget(self):
        if self.element is None:
            return self.widget

        e = self.element
        wid = e.get('id', None)
        ids = [wid] if wid else []
        while True:
            try:
                e = e.getparent()
                if not e:
                    break
            except AttributeError:
                # End of the line.
                break
            wid = e.get('id', None)
            if wid:
                ids.append(wid)
        return ids[-1]

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
        if widget is None:
            debug(f'No widget named: {gtkname}')
        # Find the event handler function info for the widget.
        # 'move-cursor' becomes Gtk.WidgetThing.do_move_cursor
        widgetevent = getattr(widget, self.event, None)
        if widget and (widgetevent is None):
            debug(f'No event function found for: {gtkname}:{self.name}')
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
        if widget and widgetevent:
            debug(f'Unable to get_arguments() for: {gtkname}:{widgetevent}')
        return defaultargs

    def is_dupe(self, other):
        if not isinstance(other, SignalHandler):
            return False
        return (self.name == other.name) and (self.handler == other.handler)

    def key_value(self, use_id=False):
        widgetid = f'self.{self.full_widget()}' if use_id else 'self'
        return (f'\'{self.handler}\'', f'{widgetid}.{self.handler}')

    @classmethod
    def map_elements(cls, elements):
        for elem in elements:
            h = cls.from_element(elem)
            if h is not None:
                yield h

    def repr_fmt(self, indent=0):
        return '\n'.join(self.repr_lines(indent=indent))

    def repr_lines(self, indent=0):
        spaces = ' ' * indent
        t = type(self).__name__
        return [f'{spaces}{self.widget}.{self.name} ({t}: {self.widgettype})']

    def signal_def(self, indent=4):
        """ Returns the function definition for this handler,
            including known arguments to this event if found.
            Arguments:
                indent   : Amount of space before the definition.
                with_id  : Add the widget id, to make it more unique.
        """
        template = '\n'.join((
            '{space}def {handler}({eventargs}):',
            '{space2}{docs}',
            '{space2}{content}'
        ))
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
