import re
import pgmapcss.eval
eval_param = ', current' #, object, current, render_context'

def valid_func_name(func):
    if re.match('[a-zA-Z_0-9]+$', func):
        return func

    else:
        raise Exception('Illegal eval function name: ' + func)

# returns a tuple:
# body, a string containing the compiled function
# eval_options, options like requirements
def compile_eval(value, prop, stat):
    global eval_param

    eval_functions = pgmapcss.eval.functions().list()

    possible_values, mutable, eval_options = pgmapcss.eval.possible_values(value, prop, stat)

    # if the eval function returns only one possible value and mutability is 3,
    # we can just take it for granted
    if mutable == 3 and len(possible_values) == 1:
        possible_values = possible_values.pop()
        if type(possible_values) == str:
            return repr(possible_values), eval_options

    if type(value) == str:
        if value[0:2] == 'v:':
            return repr(value[2:]), eval_options

        elif value[0:2] == 'f:':
            func = value[2:]
            if not func in eval_functions:
                if func in pgmapcss.eval.functions().aliases:
                    func = pgmapcss.eval.functions().aliases[func]
                else:
                    raise Exception('Unknown eval function: ' + func)

            return eval_functions[func].compiler([], eval_param, stat), eval_options

        else:
            raise Exception('compiling eval: ' + repr(value))

    if len(value) == 0:
        return '', eval_options

    if not value[0][0:2] in ('f:', 'o:', 'u:'):
        ret, o = compile_eval(value[0], prop, stat)
        return ret, pgmapcss.eval.merge_options(eval_options, o)

    results = [ compile_eval(i, prop, stat) for i in value[1:] ]
    param = [ r[0] for r in results ]
    for r in results:
        eval_options = pgmapcss.eval.merge_options(eval_options, r[1])

    if value[0][0:2] == 'o:':
        func = [ k for k, v in eval_functions.items() if value[0][2:] in v.op and not v.unary ][0]

    elif value[0][0:2] == 'u:':
        func = [ k for k, v in eval_functions.items() if value[0][2:] in v.op and v.unary ][0]

    elif value[0][0:2] == 'f:':
        func = value[0][2:]

    if not func in eval_functions:
        if func in pgmapcss.eval.functions().aliases:
            func = pgmapcss.eval.functions().aliases[func]
        else:
            raise Exception('Unknown eval function: ' + func)

    return eval_functions[func].compiler(param, eval_param, stat), eval_options
