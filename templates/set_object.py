# Lines with '# ignore' at the end are not part of the template. # ignore
# Template placeholders and other globals are set to None so this # ignore
# can be linted while editing. # ignore
sys = None  # ignore


def set_object(self, objname):
    """ Try building an object by it's name. """

    if objname:
        obj = self.builder.get_object(objname)
        if obj:
            setattr(self, objname, obj)
        else:
            print(
                '\\nError setting object!: {{}}'.format(objname),
                file=sys.stderr,
            )
