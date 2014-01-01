import pg

def compile_properties(statement, stat):
    ret = ''
    prop_to_set = {}
    tags_to_set = {}

    for prop in statement['properties']:
        if prop['assignment_type'] == 'P':
            if prop['value_type'] == 'eval':
                pass

            else:
                prop_to_set[prop['key']] = prop['value']

                if not prop['key'] in stat['properties_values']:
                    stat['properties_values'][prop['key']] = set()

                stat['properties_values'][prop['key']].add(prop['value'])

        elif prop['assignment_type'] == 'T':
            if prop['value_type'] == 'eval':
                pass

            else:
                tags_to_set[prop['key']] = prop['value']

    ret += print_props_and_tags(statement['current_pseudo_element'], prop_to_set, tags_to_set)

    return ret

def print_props_and_tags(current_pseudo_element, prop_to_set, tags_to_set):
  ret = ''

  if len(prop_to_set):
      ret += 'current.styles[' + current_pseudo_element + '] = ' +\
          'current.styles[' + current_pseudo_element + '] || ' +\
          pg.format(prop_to_set) + ';\n'
      prop_to_set.clear()

  if len(tags_to_set):
      ret += 'current.tags = current.tags || ' +\
          pg.format(tags_to_set) + ';\n'
      tags_to_set.clear()

  return ret