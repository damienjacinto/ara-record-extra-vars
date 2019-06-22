from ansible.plugins.callback import CallbackBase
import logging
from pprint import pprint
from ansible import context

try:
  from ara import models
  from ara.models import db
  from ara.webapp import create_app
  from flask import current_app
  HAS_ARA = True
except ImportError:
  HAS_ARA = False

class CallbackModule(CallbackBase):
  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE = 'notification'
  CALLBACK_NAME = 'sncf_jenkins'

  def __init__(self):
    super(CallbackModule, self).__init__()
    logging.basicConfig(filename='example.log', filemode='w', format='%(asctime)s %(message)s', level=logging.DEBUG)
    if context.CLIARGS:
      logging.debug('Cli ok')
      self.extra_vars = context.CLIARGS['extra_vars']
    else:
      logging.debug('cli non ok')

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
    logging.debug('Play started')
    if self.playbook_id:
      self.extra_vars = play._variable_manager._extra_vars
      for extra_vars_key,extra_vars_value in self.extra_vars.items():
        self.create_or_update_key(self.playbook_id, extra_vars_key, extra_vars_value, 'text')
        