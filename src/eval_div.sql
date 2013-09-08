insert into eval_operators values ('/', 'div');
create or replace function eval_div(param text[],
  object pgmapcss_object, current pgmapcss_current, render_context pgmapcss_render_context)
returns text
as $$
#variable_conflict use_variable
declare
  ret float := 1;
  i text;
  t text;
begin
  foreach i in array param loop
    t := eval_number(Array[i], object, current, render_context);

    if t = '' then
      return '';
    end if;

    if ret is null then
      ret := cast(t as float);
    else
      if t = '0' then
	return '';
      end if;

      ret := ret / cast(t as float);
    end if;
  end loop;

  return ret;
end;
$$ language 'plpgsql' immutable;