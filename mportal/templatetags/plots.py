import re
from django.template import engines, Library
from django.utils.safestring import mark_safe
from plotly.offline import plot
from mportal.models import MailGunMessage

import plotly.graph_objs as go

import numpy as np


register = Library()

@register.simple_tag
def plot_data(N=500):
    N = 500
    x = np.linspace(0, 1, N)
    y = np.random.randn(N)
    trace = go.Scatter(
            x = x,
            y = y
        )
    data = [trace]
    s = plot([trace], output_type="div", include_plotlyjs=False, show_link=False)
    plot_id = re.search('(?<=div id=\")[0-9A-Fa-f,-]*', s).group(0)
    s += """
<script>
    window.addEventListener('resize', function() {{ Plotly.Plots.resize("{plot_id}"); }});
</script>
    """.format(plot_id=plot_id)

    return mark_safe(s)

@register.simple_tag
def plot_overview(pk):
    mg = MailGunMessage.objects.get(pk=pk)
    data = [go.Bar(
            x=['Versendet', 'Empfangen', 'Gelesen'],
            y=[mg.recipient_count(), mg.delivered().count(), mg.read_count()]
    )]
    layout = go.Layout(
            title=mg.subject + mg.created.strftime(' %Y-%m-%d'),
    )
    fig = go.Figure(data=data, layout=layout)
    s = plot(fig, output_type="div", include_plotlyjs=False, show_link=False)
    plot_id = re.search('(?<=div id=\")[0-9A-Fa-f,-]*', s).group(0)
    s += """
<script>
    window.addEventListener('resize', function() {{ Plotly.Plots.resize("{plot_id}"); }});
    Plotly.Plots.resize("{plot_id}");
</script>
    """.format(plot_id=plot_id)

    return mark_safe(s)

@register.simple_tag
def plot_url_clicks(pk):
    mg = MailGunMessage.objects.get(pk=pk)
    data = []
    for url in mg.urls():
        events = mg.mailgunevent_set.filter(url=url).order_by('timestamp')
        t = [mg.created]
        c = [0]
        for event in events:
            t.append(event.timestamp)
            c.append(c[-1]+1)
        data.append(go.Scatter(x=t, y=c, name=url))
    if len(data)==0:
        return ''


    layout = dict(
        title="Klickverlauf",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1h',
                         step='hour',
                         stepmode='backward'),
                    dict(count=1,
                         label='1d',
                         step='day',
                         stepmode='backward'),
                    dict(count=1,
                         label='1w',
                         step='week',
                         stepmode='backward'),
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(step='all')
                ])
            ),
            rangeslider=dict(),
            type='date'
        )
    )
    fig = go.Figure(data=data, layout=layout)
    s = plot(fig, output_type="div", include_plotlyjs=False, show_link=False)
    plot_id = re.search('(?<=div id=\")[0-9A-Fa-f,-]*', s).group(0)
    s += """
<script>
    window.addEventListener('resize', function() {{ Plotly.Plots.resize("{plot_id}"); }});
    Plotly.Plots.resize("{plot_id}");
</script>
    """.format(plot_id=plot_id)

    return mark_safe(s)

@register.simple_tag
def click_count(pk, url):
    return MailGunMessage.objects.get(pk=pk).click_count_for(url)

@register.simple_tag
def click_count_unique(pk, url):
    return MailGunMessage.objects.get(pk=pk).unique_click_count_for(url)
