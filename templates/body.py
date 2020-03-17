# Lines with '# ignore' at the end are not part of the template. # ignore
# Template placeholders and other globals are set to None so this # ignore
# can be linted while editing. # ignore
class_def = None  # ignore
Gtk = None  # ignore
sys = None  # ignore

NAME = 'GtkApp'
__version__ = '0.0.1'
VERSIONSTR = '{{}} v. {{}}'.format(NAME, __version__)


{class_def}


def main():
    """ Main entry point for the program. """
    app = App()  # noqa
    return Gtk.main()


if __name__ == '__main__':
    mainret = main()
    sys.exit(mainret)
