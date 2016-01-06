# coding=utf-8
import inspect

__author__ = 'zephor'


def iter_sub_classes(module, o):
        """Return an iterator over all sub-classes of the base-obj given defined in
        the given module that can be instantiated (ie. which have name)
        """
        for obj in vars(module).itervalues():
            if inspect.isclass(obj) and issubclass(obj, o)\
                    and obj.__module__ == module.__name__:
                yield obj
