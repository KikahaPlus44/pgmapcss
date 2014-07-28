from .ParseError import *
from ..version import *

# returns
# * the media query to include in statement (might be simplified)
# * ('media-ignore') if we can ignore the media query at parse time - if yes,
#   it will move file pointer to the end of the @media { ... } statement
def check_media_query(stat, to_parse, query):
    match = False
    for q1 in query:
        match1 = True
        negated1 = False

        if q1[0] == 'NOT':
            negated1 = True

        for q in q1[1:]:
            m1 = False

# add here all queries that are (or might be) True
            if q[0] == 'user-agent' and q[1] == 'pgmapcss':
                m1 = True
            elif q[0] == 'min-pgmapcss-version':
                m1 = True
                check_version = q[1].split('.')
                for i, v in enumerate(check_version):
                    if len(VERSION_INFO) < i or (type(VERSION_INFO[i]) == int and VERSION_INFO[i] < int(v)):
                        m1 = False
            elif q[0] == 'max-pgmapcss-version':
                m1 = True
                check_version = q[1].split('.')
                for i, v in enumerate(check_version):
                    if len(VERSION_INFO) < i or (type(VERSION_INFO[i]) == int and VERSION_INFO[i] > int(v)):
                        m1 = False

            elif q[0] == 'type':
                m1 = True

            if not m1:
                match1 = False

        if match1 and not negated1:
            match = True
        if not match1 and negated1:
            match = True

    if match:
        return ( 'media', query )

# if match is False we can ignore the whole @media { ... } statement ...
# search for closing bracket
    mode = 0
    level = 1

    while True:
        if mode == 0:
            if to_parse.match('[^\'"{}\\\\]*([\'"{}\\\\])'):

                c = to_parse.match_group(1)
                if c == '}':
                    if level == 1:
                        return ('media-ignore')
                    else:
                        level = level - 1
                elif c == '{':
                    level = level + 1
                elif c == '\\':
                    to_parse.match('.')
                elif c == '"':
                    mode = 1
                elif c == '\'':
                    mode = 2

            elif to_parse.match('.*\n'):
                pass

        elif mode in (1, 2):
            if to_parse.match('[^\'"\\\\]*([\'"\\\\])'):

                c = to_parse.match_group(1)
                if c == '\\':
                    to_parse.match('.')
                elif (mode == 1 and c == '"') or (mode == 2 and c == '\''):
                    mode = 0

            elif to_parse.match('.*\n'):
                pass

        if not to_parse.to_parse():
            raise ParseError(to_parse, '@media query not closed at')