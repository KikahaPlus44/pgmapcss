class config_eval_line(config_base):
    mutable = 3

def eval_line(param):
    if len(param) == 0:
        return ''

    if len(param) == 1:
        param = param[0].split(';')

    if len(param) == 1:
        param = param[0]
        plan = plpy.prepare('select ST_MakeLine($1) as r', ['geometry'])

    else:
        plan = plpy.prepare('select ST_MakeLine($1) as r', ['geometry[]'])

    try:
      res = plpy.execute(plan, [param])
    except Exception as err:
        plpy.warning('{} | Eval::line({}): Exception: {}'.format(current['object']['id'], param, err))
        return ''

    return res[0]['r']

# TESTS
# IN ['010100002031BF0D0033333333F4EE2F41E17A14DE3A8A5641', '010100002031BF0D0052B81E8583EF2F417B14AE77FC895641', '010100002031BF0D00D7A370BDA8F02F418FC2F5F8CE885641']
# OUT '010200002031BF0D000300000033333333F4EE2F41E17A14DE3A8A564152B81E8583EF2F417B14AE77FC895641D7A370BDA8F02F418FC2F5F8CE885641'
# IN ['010100002031BF0D0033333333F4EE2F41E17A14DE3A8A5641;010100002031BF0D0052B81E8583EF2F417B14AE77FC895641;010100002031BF0D00D7A370BDA8F02F418FC2F5F8CE885641']
# OUT '010200002031BF0D000300000033333333F4EE2F41E17A14DE3A8A564152B81E8583EF2F417B14AE77FC895641D7A370BDA8F02F418FC2F5F8CE885641'
