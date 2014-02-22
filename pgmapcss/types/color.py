from .base import base
from pgmapcss.colors import to_color
from pgmapcss.compiler.CompileError import *

class color(base):
    def compile_check(self, value):
        return 'check_color(' + value + ')'

    def compile(self, prop):
        if not to_color(prop['value']):
            raise CompileError("Error: Unknown color '{}'".format(prop['value']))

        return repr(prop['value'])
