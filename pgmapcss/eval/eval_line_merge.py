def eval_line_merge(param):
    if len(param) == 0:
        return ''

    if len(param) == 1:
        param = param[0].split(';');

    if len(param) == 1:
        plan = plpy.prepare('select ST_LineMerge($1) as r', ['geometry'])
        res = plpy.execute(plan, [param[0]])

    else:
        plan = plpy.prepare('select ST_LineMerge(ST_Collect($1)) as r', ['geometry[]'])
        res = plpy.execute(plan, [param])

    return res[0]['r']

# TESTS
# IN ['010500002031BF0D000200000001020000000400000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB456410102000000030000003D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641']
# OUT '010200002031BF0D000600000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641'
# IN ['010200002031BF0D000400000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB45641', '010200002031BF0D00030000003D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641']
# OUT '010200002031BF0D000600000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641'
# IN ['010200002031BF0D000400000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB45641;010200002031BF0D00030000003D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641']
# OUT '010200002031BF0D000600000014AE47E133393A411F85EBE15FB456418FC2F5A841393A41D7A3707D60B456410AD7A3F00B3A3A419A99997969B456413D0AD7631D3A3A41D7A3702D6AB45641295C8F82293A3A4185EB51B86AB45641B81E856BC63A3A418FC2F55876B45641'