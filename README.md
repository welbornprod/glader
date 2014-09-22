Glader
======

Generates skeleton code from a glade file. The generated signal handler stubs
can then be filled in to provide functionality. Arguments for signal handlers
are automatically decided through introspection using Gtk.

I didn't know this before I wrote it, but this does the exact same thing that
`pyqt4uic` and `pykde4uic` do for Qt designer files. It does a little more
actually. It includes a GUI for previewing/editing, and also generates stubs
for the signal handlers. It does this by reading the glade file's XML,
parsing it, and using introspection to generate the stubs.

The glade file still needs to be present in the finished application
directory. It is used with `Gtk.Builder.add_from_file()` to generate the
widgets.

When everything is working as expected, doing
`glader input.glade output.py` will create an executable Gtk application
that can be ran and previewed by running `./output.py`.


Command Line:
-------------

If an input file name (glade), and an output file name (python) are passed to
`glader`, the code will be generated and written to the output file.

You can pass `-` as the output file name to write to stdout.


Gui Mode:
---------

When `glader` is ran with no arguments, or just an input file is given, a GUI
is loaded. In GUI mode a preview is generated, and can be edited before saving.
When an input file is given, or `--gui` is used, the preview code is
automatically generated when the program loads.

The GUI supports Python syntax highlighting using GtkSourceView. The viewer
uses GtkSourceView themes, and can be changed using the theme selector.
Themes are located in `/usr/share/gtksourceview-3.0/styles`, and can be
downloaded from various places on the internet. The most common is
[https://wiki.gnome.org/Projects/GtkSourceView/StyleScheme](https://wiki.gnome.org/Projects/GtkSourceView/StyleScheme).


Usage:
------

```

    Usage:
        glader.py -h | -v
        glader.py [FILE] [OUTFILE] [-d] [-g]

    Options:
        FILE           : Glade file to parse.
        OUTFILE        : File name for output.
                         If - is given, output will be printed to stdout.
        -d,--dynamic   : Use dynamic object initialization method.
        -g,--gui       : Force use of a GUI, even when an output file is given.
                         You still have to use the 'Save' button to apply
                         changes.
        -h,--help      : Show this help message.
        -v,--version   : Show version.
```


Dependencies:
-------------

Glader has several GTK-related dependencies. If you are already creating GTK
apps then you may have some of these installed already.

###Python modules:

Installed with [pip](https://pypi.python.org).

* **docopt** - *Handles command-line argument parsing.*

###System packages:

Installed with your package manager, like [apt](https://wiki.debian.org/apt-get).

* **gir1.2-gtk-3.0** - *Provides helpers and access to GIRepository.*
* **libgtksourceview-3.0-dev** - *Provides the `GtkSourceView` widget.*
* **python3-gi** - *Provides python bindings for gobject-introspection.*

There may be others, I will fill in the missing dependencies as they are found.
Message me or file an issue if you run into errors.


Compatibility:
--------------

Glader is designed for
[PyGTK3](http://python-gtk-3-tutorial.readthedocs.org/en/latest/install.html),
and [Python 3](https://www.python.org/downloads/).

It's possible to backport this to older versions, but no work will be done on
that unless the need is great.
File an issue if that is something you would like to see.


Contributions:
--------------

Contributions are welcome. That's what this repo is for.
File an issue, or send me a pull request if you would like to see a
feature added to Glader.


GUI Preview:
--------

![Glader](http://welbornprod.com/static/images/glader/glader-preview.png)
