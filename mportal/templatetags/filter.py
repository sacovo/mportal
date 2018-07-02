from django.template import engines, Library
from django.utils.safestring import mark_safe
import re

register = Library()

@register.filter()
def render(value, arg):
    t = engines['django'].from_string(arg)
    context = {'recipient': value}
    s = t.render(context=context)
    print(arg)
    return mark_safe(s)

@register.simple_tag()
def latex(value):
    return value

@register.filter()
def latex_escape(text, arg=''):
    conv = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}',
            '<': r'\textless ',
            '>': r'\textgreater ',
            }
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)
