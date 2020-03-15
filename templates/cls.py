# Lines with '# ignore' at the end are not part of the template. # ignore
# Template placeholders and other globals are set to None so this # ignore
# can be linted while editing. # ignore
classname = None  # ignore
Gtk = None  # ignore
os = None  # ignore
sys = None  # ignore
objects = None  # ignore
set_object_def = None  # ignore
signaldefs = None  # ignore


class {classname}(Gtk.{widget}):
    """ Main window with all components. """

    def __init__(self):
        Gtk.{widget}.__init__(self)
        self.builder = Gtk.Builder()
        gladefile = '{filepath}'
        if not os.path.exists(gladefile):
            # Look for glade file in this project's directory.
            gladefile = os.path.join(sys.path[0], gladefile)

        try:
            self.builder.add_from_file(gladefile)
        except Exception as ex:
            print('\\nError building main window!\\n{{}}'.format(ex))
            sys.exit(1)

        # Get gui objects
        {objects}

        # Connect all signals.
        self.builder.connect_signals(self)

        {init_end}
{set_object_def}
{signaldefs}
