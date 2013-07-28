drop type if exists pgmapcss_selector_return cascade;
create type pgmapcss_selector_return as (
  conditions            text[], /* conditional expressions */
  pseudo_classes        text[], /* :closed, ... */
  layer                 text,
  text_length           int
);

drop function pgmapcss_parse_selector(text);
create or replace function pgmapcss_parse_selector (
  text
)
returns setof pgmapcss_selector_return
as $$
#variable_conflict use_variable
declare
  ret pgmapcss_selector_return;
  m text;
  m1 text;
  t text;
  selector text;
  max_scale_denominator float := 3.93216e+08;
begin
  selector:=$1;
  ret.conditions=Array[]::text[];
  ret.pseudo_classes=Array[]::text[];

  -- parse object class (way, node, canvas, ...)
  m := substring(selector from '^\s*(\*|node|way|relation|area|meta|canvas)(\|.*|\[.*|:.*|\s)');
  if m is not null then
    ret.conditions=array_append(ret.conditions, ''''||m||'''=ANY(type)');
  else
    raise notice 'can''t parse object class at "%..."', substring(selector, 0, 40);
  end if;
  selector := substring(selector from '^\s*(?:\*|node|way|relation|area|meta|canvas)(\|.*|\[.*|:.*|\s)');

  -- parse zoom level
  m := substring(selector from '^\|z([0-9\-]+)(\[.*|:.*|\s)');
  if m is not null then
    -- zN
    m1 := substring(m from '^([0-9]+)$');
    if m1 is not null then
      ret.conditions=array_append(ret.conditions,
        'scale_denominator >= ' ||
        cast((max_scale_denominator / 2 ^ cast(m as int)) as text) ||
        ' and scale_denominator < ' ||
        cast((max_scale_denominator / 2 ^ (cast(m as int) - 1)) as text)
      );
    end if;

    -- zN-
    m1 := substring(m from '^([0-9]+)\-$');
    if m1 is not null then
      ret.conditions=array_append(ret.conditions,
        'scale_denominator < ' ||
        cast((max_scale_denominator / 2 ^ (cast(m1 as int) - 1)) as text)
      );
    end if;

    -- z-N
    m1 := substring(m from '^\-([0-9]+)$');
    if m1 is not null then
      ret.conditions=array_append(ret.conditions,
        'scale_denominator >= ' ||
        cast((max_scale_denominator / 2 ^ cast(m1 as int)) as text)
      );
    end if;

    -- zN-N
    m1 := substring(m from '^(?:[0-9]+)\-([0-9]+)$');
    if m1 is not null then
      t=
        'scale_denominator >= ' ||
        cast((max_scale_denominator / 2 ^ cast(m1 as int)) as text);

      m1 := substring(m from '^([0-9]+)\-(?:[0-9]+)$');
      t=t||
        ' and scale_denominator < ' ||
        cast((max_scale_denominator / 2 ^ (cast(m1 as int) - 1)) as text);

      ret.conditions=array_append(ret.conditions, t);
    end if;

    selector := substring(selector from '^\|(?:z[0-9\-]+)(\[.*|:.*|\s)');
  end if;

  -- parse condition selector(s)
  while selector ~ '^\[[^\]]+\]' loop
    m := substring(selector from '^\[([^\]]+)\]');
    ret.conditions=array_append(ret.conditions, pgmapcss_condition(m));
    selector := substring(selector from '^\[[^\]]+\](.*)$');
  end loop;

  -- parse pseudo classes
  while selector ~ '^:([a-zA-Z0-9_]+)' loop
    m := substring(selector from '^:([a-zA-Z0-9_]+)');
    ret.pseudo_classes=array_append(ret.pseudo_classes, m);
    selector := substring(selector from '^:[a-zA-Z0-9_]+(.*)$');
  end loop;

  -- parse layer
  if selector ~ '^::([a-zA-Z0-9_]+)' then
    m := substring(selector from '^::([a-zA-Z0-9_]+)');
    ret.layer=m;
    selector := substring(selector from '^::[a-zA-Z0-9_]+(.*)$');
  end if;

  ret.text_length=strpos($1, selector);

  return next ret;
  return;
end;
$$ language 'plpgsql' immutable;