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
