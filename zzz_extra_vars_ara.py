from ansible.plugins.callback import CallbackBase
from ansible import context

DOCUMENTATION = '''
callback: extra_vars_to_ara_record
type: notification
short_description: add extra_vars to ara_record of the current playbook
description:
- Ansible callback to record extra_vars with ara_record
- The name had to start with a z because the ara callback needs to start before this callback
author:
- Damien Jacinto
requirements:
- "python >= 2.6"
- "ara >= 0.10.0 < 1.0.0"
'''

try:
  from ara import models
  from ara.models import db
  from flask import current_app
  HAS_ARA = True
except ImportError:
  HAS_ARA = False

class CallbackModule(CallbackBase):
  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE = 'notification'
  CALLBACK_NAME = 'extra_vars_to_ara_record'
  IGNORE_EXTRA_VARS = frozenset(('pass', 'mdp'))

  def __init__(self):
    super(CallbackModule, self).__init__()
    if context.CLIARGS:
      self.extra_vars = context.CLIARGS['extra_vars']

  def create_or_update_key(self, playbook_id, key, value, type):
    try:
      data = (models.Data.query
            .filter_by(key=key)
            .filter_by(playbook_id=playbook_id)
            .one())
      data.value = value
      data.type = type
    except models.NoResultFound:
      data = models.Data(playbook_id=playbook_id,
                        key=key,
                        value=value,
                        type=type)
    db.session.add(data)
    db.session.commit()
    return data
  
  def v2_playbook_on_start(self, playbook):
    if HAS_ARA and current_app:
      self.playbook_id = current_app._cache['playbook']
    
  def v2_playbook_on_play_start(self, play):
    if self.playbook_id:
      self.extra_vars = play._variable_manager._extra_vars
      for extra_vars_key,extra_vars_value in self.extra_vars.items():
        if all(x not in extra_vars_key for x in self.IGNORE_EXTRA_VARS):
          self.create_or_update_key(self.playbook_id, extra_vars_key, extra_vars_value, 'text')
        