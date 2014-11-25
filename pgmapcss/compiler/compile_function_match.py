from pkg_resources import *
import pgmapcss.db as db
from .compile_db_selects import compile_db_selects
from .compile_function_check import compile_function_check
from .compile_build_result import compile_build_result
from ..includes import include_text
import pgmapcss.eval
import pgmapcss.mode
import pgmapcss.types
from pgmapcss.misc import strip_includes

def compile_function_match(stat):
    scale_denominators = sorted(stat.all_scale_denominators(), reverse=True)

    object_checks = compile_build_result(stat)
    max_scale = None
    for min_scale in scale_denominators:
        object_checks += compile_function_check([
            v
            for v in stat['statements']
            if v['selector']['min_scale'] <= min_scale and
                (v['selector']['max_scale'] == None or v['selector']['max_scale'] >= (max_scale or 10E+10))
        ], min_scale, max_scale, stat)
        object_checks += '\n'
        max_scale = min_scale

    check_chooser  = "if render_context['scale_denominator'] is None:\n"
    check_chooser += "    check = check_0\n"

    for i in scale_denominators:
        check_chooser += "elif render_context['scale_denominator'] >= %i:\n" % i
        check_chooser += "    check = check_%s\n" % str(i).replace('.', '_')

    stat['global_data'] = {}
    # get global data from type
    for prop in stat.properties():
        prop_type = pgmapcss.types.get(prop, stat)
        d = prop_type.get_global_data()
        if d:
            stat['global_data'][prop] = d
            stat.clear_property_values_cache()

    replacement = {
      'style_id': stat['id'],
      'host': stat['args'].host,
      'password': stat['args'].password,
      'database': stat['args'].database,
      'default_lang': repr(stat['lang']),
      'user': stat['args'].user,
      'db_srs': stat['config']['db.srs'],
      'srs': stat['config']['srs'],
      'style_element_property': repr({
          k: v['value'].split(';')
          for k, v in stat['defines']['style_element_property'].items()
      }),
      'all_style_elements': repr({ k
          for k, v in stat['defines']['style_element_property'].items()
      }),
      'scale_denominators': repr(scale_denominators),
      'db_selects': compile_db_selects(stat['id'], stat),
      'db_query': db.query_functions(stat),
      'function_check': object_checks,
      'check_chooser': check_chooser,
      'eval_functions': \
resource_string(pgmapcss.eval.__name__, 'base.py').decode('utf-8') +\
pgmapcss.eval.functions().print(indent='') +\
include_text()
    }

    ret = '''\
import re
import math
import datetime
import copy
'''.format(**replacement)

    if stat['config'].get('debug.profiler', False):
        ret += 'time_start = datetime.datetime.now() # profiling\n'

    ret += '''\
global render_context

if not 'lang' in parameters:
    parameters['lang'] = {default_lang}
if not 'srs' in parameters:
    parameters['srs' ] = {srs}

if type(bbox) == list and len(bbox) == 4:
    plan = plpy.prepare('select SetSRID(MakeBox2D(ST_Point($1, $2), ST_Point($3, $4)), $5) as bounds', ['float', 'float', 'float', 'float', 'int'])
    res = plpy.execute(plan, [float(b) for b in bbox] + [ parameters['in.srs'] if 'in.srs' in parameters else parameters['srs'] ])
    _bbox = res[0]['bounds']
else:
    _bbox = bbox

plan = plpy.prepare('select ST_Transform($1, {db_srs}) as bounds', ['geometry'])
res = plpy.execute(plan, [_bbox])
render_context = {{ 'bbox': res[0]['bounds'], 'scale_denominator': scale_denominator }}
'''.format(**replacement)

    if stat['config'].get('debug.context', False):
        ret += 'plpy.warning(render_context)\n'

    ret += 'global_data = ' + repr(stat['global_data']) + '\n'

    ret += '''\
{db_query}
{eval_functions}
{function_check}
db_selects = None
{db_selects}
counter = {{ 'rendered': 0, 'total': 0 }}

{check_chooser}
combined_objects = {{}}
all_style_elements = _all_style_elements
style_element_property = {style_element_property}
for style_element in all_style_elements:
    if not style_element in style_element_property:
        style_element_property[style_element] = []

'''.format(**replacement)

    func = "objects(render_context.get('bbox'), db_selects)"
    if stat['config'].get('debug.profiler', False):
        ret += "time_qry_start = datetime.datetime.now() # profiling\n"
        ret += "src = list(" + func + ")\n"
        ret += "time_qry_stop = datetime.datetime.now() # profiling\n"
        ret += "plpy.warning('querying db objects took %.2fs' % (time_qry_stop - time_qry_start).total_seconds())\n"
    else:
        ret += "src = " + func + "\n"

    ret += '''\

def ST_Collect(geometries):
    plan = plpy.prepare('select ST_Collect($1) as r', ['geometry[]'])
    res = plpy.execute(plan, [geometries])
    return res[0]['r']

def convert_srs(geom):
    plan = plpy.prepare('select ST_Transform($1, $2) as r', ['geometry', 'integer'])
    res = plpy.execute(plan, [geom, parameters['srs']])
    return res[0]['r']

def dict_merge(dicts):
    ret = {{}}

    for d in dicts:
        for k, v in d.items():
            if k not in ret:
                ret[k] = set()

            ret[k].add(v)

    for k, vs in ret.items():
        ret[k] = ';'.join(vs)

    return ret

# Sources which still need to be processed. If a source is squeezed in (e.g.
# due to a relationship), the previous source will be pushed to the src_stack.
src_stack = [ ]
# Objects which have a request (e.g. from a relationship).
request_objects = [ ]
# Objects which are partly processed, but might still be needed at the current
# state for handling relationships.
pending_objects = {{ }}
# Minimal index of a pending object. Decides whether a request for a
# relationship will be handled right now or later (-> added to request_objects)
pending_min_index = 999999999999999

while src:
    while True:
        # get the next object from the current source.
        if type(src) == list:
            try:
                object = src.pop(0)
            except IndexError:
                break
        else:
            try:
                object = next(src)
            except StopIteration:
                break

        # check if the object is already a pending_object and the object is new
        # (no 'state') -> skip
        if object['id'] in pending_objects and not 'state' in object:
            break

        # for each object the check() function will be called. it is a
        # generator function which we either use via next() or send(). As we
        # might need it for longer, we save the reference to the function in
        # object['object_check']
        if 'object_check' in object:
            object_check = object['object_check']

        else:
            object['state'] = ( 'start', 0 )
            shown = False
            counter['total'] += 1
            object_check = check(object)
            object['object_check'] = object_check

        # get the next return value from the check() function, this can be
        # either a result or a notification about relationship: 'pending',
        # 'request', 'combine'
        while object_check:
            try:
                if len(object['state']) > 2:
                    result = object_check.send([
                        pending_objects[r['id']] if r['id'] in pending_objects else r
                        for r in object['state'][2]
                    ])
                else:
                    result = next(object_check)
            except StopIteration:
                object['state'] = ( 'finish', 999999999999999 )
                break

            if type(result) != tuple or len(result) == 0:
                plpy.warning('unknown check result: ', result)
            elif result[0] == 'result':
                # TODO: return current statement id
                object['state'] = ( 'processing', 0 )
                result = result[1]

                # create a list of all style elements where the current
                # object/pseudo_element is being shown, with a tuple of
                # [ ( style_element, index in style_element list, layer,
                # z-index ), ... ], e.g.:
                # [
                #   ( 'line', 2, 0, 5 ),
                #   ( 'line-text', 5, 103, 5 )
                # ]
                style_elements = [
                    (
                        style_element,
                        i,
                        to_float(result['properties'][style_element + '-layer'] if style_element + '-layer' in result['properties'] else (result['properties']['layer'] if 'layer' in result['properties'] else 0)),
                        to_float(result['properties'][style_element + '-z-index'] if style_element + '-z-index' in result['properties'] else (result['properties']['z-index'] if 'z-index' in result['properties'] else 0))
                    )
                    for i, style_element in enumerate(_all_style_elements)
                    if len({{
                        k
                        for k in style_element_property[style_element]
                        if k in result['properties'] and result['properties'][k]
                    }})
                ]

                # TODO: maybe not "continue", but better indent yield instead
                if len(style_elements) == 0:
                    continue
                shown = True
    '''.format(**replacement)

                # now build the return columns
    if stat['mode'] == 'database-function':
        ret += '''
                yield {{
                    'id': result['id'],
                    'types': result['types'],
                    'tags': pghstore.dumps(result['tags']),
                    'pseudo_element': result['pseudo_element'],
                    'geo': convert_srs(result['geo']),
                    'properties': pghstore.dumps(result['properties']),
                    'style_elements': [ se[0] for se in style_elements ],
                    'style_elements_index': [ se[1] for se in style_elements ],
                    'style_elements_layer': [ se[2] for se in style_elements ],
                    'style_elements_z_index': [ se[3] for se in style_elements ],
                }}
        '''.format(**replacement)

    elif stat['mode'] == 'standalone':
        ret += '''
                yield {{
                    'id': result['id'],
                    'types': result['types'],
                    'tags': result['tags'],
                    'pseudo_element': result['pseudo_element'],
                    'geo': convert_srs(result['geo']),
                    'properties': result['properties'],
                    'style_elements': [ se[0] for se in style_elements ],
                    'style_elements_index': [ se[1] for se in style_elements ],
                    'style_elements_layer': [ se[2] for se in style_elements ],
                    'style_elements_z_index': [ se[3] for se in style_elements ],
                    'object': object,
                }}
        '''.format(**replacement)

    ret += '''
            # 'request' -> function needs other objects, e.g. from
            # parent->child relation
            elif result[0] == 'request':
                object['state'] = result
                object_check = None

                # remember, that the current object has a request
                request_objects.append(object)

                if result[1] <= pending_min_index:
                    # remember to handle rest of 'src'
                    src_stack.append(src)
                    # now, process the pending objects ...
                    src = [
                        pending_objects[r['id']] if r['id'] in pending_objects else r
                        for r in result[2]
                    ]

                    # ... but only those which have not been processed (up to
                    # the current statement id)
                    src = [
                        r
                        for r in src
                        if not 'state' in r or (r['state'][0] != 'finish' and r['state'][1] < result[1])
                    ]

            # the current object might used as parent for a relationship. add
            # to pending_objects and cancel processing.
            elif result[0] == 'pending':
                object['state'] = result

                pending_objects[object['id']] = object
                object_check = None
                if result[1] < pending_min_index:
                    pending_min_index = result[1]

            elif result[0] == 'combine':
                object['state'] = ( 'processing', )

                shown = True
                if result[1] not in combined_objects:
                    combined_objects[result[1]] = {{}}
                if result[2] not in combined_objects[result[1]]:
                    combined_objects[result[1]][result[2]] = []
                combined_objects[result[1]][result[2]].append(result[3])
            else:
                plpy.warning('unknown check result: ', result)

        if shown:
            counter['rendered'] += 1
'''.format(**replacement)

    if stat['config'].get('debug.counter', False) == 'verbose':
        ret += '''
        elif object['state'][0] == 'finish':
            plpy.warning('not rendered: ' + object['id'] + ' ' + repr(object['tags']))
'''.format(**replacement)

    ret += '''

    # the current src is empty, lets see, what there is still to be done
    # 1st: check if there are any requests we can finish / continue
    if len(request_objects):
        for object in request_objects:
            if pending_min_index >= object['state'][1]:
                src.append(object)
                request_objects.remove(object)

        if len(src) == 0:
            src = None

    # 2nd: check if there's still a src in the src_stack
    if not src:
        try:
            src = src_stack.pop()
        except IndexError:
            src = None

    # 3rd: maybe object were combined to new objects
    if not src and len(combined_objects):
        src = []
        for combine_type, items in combined_objects.items():
            for combine_id, obs in items.items():
                src.append({{
                    'id': ';'.join([ ob['id'] for ob in obs ]),
                    'types': [ combine_type ],
                    'tags': dict_merge([ ob['tags'] for ob in obs ]),
                    'geo': ST_Collect([ ob['geo'] for ob in obs ])
                }})

        combined_objects = []

    # 4th: check if there are still pending_objects, process them next
    # pending_min_index always points to the next pending objects -> if it is
    # 999999999999999, there are no pending_objects any more
    if not src and pending_min_index != 999999999999999:
        src = [ ]
        for pending_id, pending in pending_objects.items():
            if pending['state'][1] == pending_min_index:
                src.append(pending)

        pending_min_index = 999999999999999

        if len(src) == 0:
            src = None

    # final: no sources left
'''.format(**replacement)

    if stat['config'].get('debug.profiler', False):
        ret += '''
time_stop = datetime.datetime.now() # profiling
plpy.warning('total run of processing (incl. querying db objects) took %.2fs' % (time_stop - time_start).total_seconds())
'''.format(**replacement)

    if stat['config'].get('debug.counter', False):
        ret += '''
if counter['total'] == 0:
    counter['perc'] = 100.0
else:
    counter['perc'] = counter['rendered'] / counter['total'] * 100.0
plpy.warning('rendered map features: {{rendered}} / {{total}}, {{perc:.2f}}%'.format(**counter))
'''.format(**replacement)

    if stat['config'].get('debug.rusage', False):
        ret += '''
import resource
plpy.warning('Resource Usage: ' + str(resource.getrusage(resource.RUSAGE_SELF)) + '\\nsee https://docs.python.org/3/library/resource.html')
'''.format(**replacement)

    indent = ''
    if stat['mode'] == 'standalone':
        indent = '    '

    header = strip_includes(resource_stream(pgmapcss.mode.__name__, stat['mode'] + '/header.inc'), stat)
    header = header.format(**replacement)

    footer = strip_includes(resource_stream(pgmapcss.mode.__name__, stat['mode'] + '/footer.inc'), stat)
    footer = footer.format(**replacement)

    ret = header + indent + ret.replace('\n', '\n' + indent) + '\n' + footer

    return ret
