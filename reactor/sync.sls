{# Sync custom modules, states etc. to minions #}

master.sync.all:
  local.saltutil.sync_all:
    - tgt: {{ data['id'] }}
