{# If master failed to authenticate, remove accepted key #}
{# Note: You have to restart minion manually if master failed to auth it #}

{% if not data['result'] %}
minion.key.remove:
  wheel.key.delete:
    - match: {{ data['id'] }}
{% endif %}

{# If you want minion key auto accepted, change this accordingly #}
{% if 0 %}

{% if 'act' in data and data['act'] == 'pend' %}
minion.key.accept:
  wheel.key.accept:
    - match: {{ data['id'] }}
{% endif %}

{% endif %}
