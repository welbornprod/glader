class App(Gtk.Window):
    """ Main window with all components. """

    def __init__(self):
        Gtk.Window.__init__(self)
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

        # Show the main window.
        self.{mainwindow}.show_all()

    {set_object_def}

{signaldefs}
