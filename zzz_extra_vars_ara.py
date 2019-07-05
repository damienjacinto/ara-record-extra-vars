from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
callback: extra_vars_to_ara_record
type: notification
short_description: add extra_vars to ara_record of the current playbook
description:
- Ansible callback to record extra_vars with ara_record
- The name had to start with a z because the ara callback needs to start before this callback
- You can force the type of the record with a suffix on the extra_vars key (see VALID_TYPES)
author:
- Damien Jacinto
requirements:
- "python >= 2.6"
- "ara >= 0.10.0 < 1.0.0"
'''

EXAMPLES = '''
# add the callback with the callback for ara
# call your playbook with en extra_vars or an extra_vars file
ansible-playbook -i inventory/ main.yml -e my_url='http://test.io'

# In this exemple the extra_var key is suffixed by _url so the ara record's type will be url.
# text is the default one, in the web ui _json and _dict get a pretty format, _list use the <ul><li> html.
# All your extra_vars are added to the ara_record of the playbook.

# You can ignore key that contains some values (see IGNORE_EXTRA_VARS).
# If the ara callback is not called before this callback, this callback will not do anything.
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
  VALID_TYPES = ['text', 'url', 'json', 'list', 'dict']

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

  def get_type_record(self, key):
    for typeRecord in self.VALID_TYPES:
      if key.endswith('_'+typeRecord):
        return typeRecord
    return self.VALID_TYPES[0]
  
  def v2_playbook_on_start(self, playbook):
    if HAS_ARA and current_app:
      self.playbook_id = current_app._cache['playbook']
    
  def v2_playbook_on_play_start(self, play):
    if hasattr(self, 'playbook_id'):
      self.extra_vars = play._variable_manager._extra_vars
      for extra_vars_key,extra_vars_value in self.extra_vars.items():
        if all(x not in extra_vars_key for x in self.IGNORE_EXTRA_VARS):
          typeRecord = self.get_type_record(extra_vars_key)
          self.create_or_update_key(self.playbook_id, extra_vars_key, extra_vars_value, typeRecord)
        