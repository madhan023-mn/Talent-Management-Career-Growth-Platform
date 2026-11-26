import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""

@register.filter(name='jsonify')
def jsonify(object):
    return mark_safe(json.dumps(object, default=str))

@register.filter(name='score_stars')
def score_stars(score):
    try:
        val = float(score)
        full_stars = int(val)
        return "★" * full_stars + "☆" * (5 - full_stars)
    except Exception:
        return "★★★☆☆"

@register.filter(name='round_val')
def round_val(value, decimals=1):
    try:
        return round(float(value), decimals)
    except Exception:
        return value

@register.filter(name='skill_name')
def skill_name_filter(s):
    if isinstance(s, dict):
        return s.get("name") or s.get("skill_name") or ""
    return str(s)

@register.filter(name='skill_proficiency')
def skill_proficiency_filter(s):
    if isinstance(s, dict):
        return s.get("proficiency") or s.get("proficiency_level") or "Intermediate"
    return "Intermediate"

@register.filter(name='skill_years')
def skill_years_filter(s):
    if isinstance(s, dict):
        return s.get("years") or s.get("years_exp") or "1.0"
    return "1.0"

@register.filter(name='skill_id')
def skill_id_filter(s):
    if isinstance(s, dict):
        return s.get("id") or s.get("name") or s.get("skill_name") or ""
    return str(s)
