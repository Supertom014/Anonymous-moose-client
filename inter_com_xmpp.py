# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


import sleekxmpp
import json
import traceback
import logging
logger = logging.getLogger(__name__)


class InterComXMPP(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, incoming_function, connection_problems):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.jid = jid
        self.incoming_function = incoming_function
        self.connection_problems = connection_problems
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.process_message)
        self.add_event_handler("session_end", lambda: self.status_report("session_end"))
        self.add_event_handler("disconnected", lambda: self.status_report("disconnected"))
        self.add_event_handler("connected", lambda: self.status_report("connected"))

        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0004')  # Data Forms
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0199')  # XMPP Ping
        self.register_plugin('xep_0085')  # Chat State Notifications

    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.status_report("session_start")
    
    def status_report(self, arg):
        output = json.loads(msg['body'])
        if arg == 'disconnected' or arg == 'session_end':
            self.connection_problems()
            if self.connect():
                self.process()

    def process_message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            output = ''
            try:
                output = json.loads(msg['body'])
                # logger.debug('inter_com: valid message received')
            except Exception as error:
                logger.info('inter_com: invalid message received')
            try:
                self.incoming_function(output)
            except Exception as error:
                logger.info('Message processing failed, but no specific exception handling caught it')

    def reply_message(self, text):
            msg = self.make_message(mto='NL_lancaster1@twattle.net/alice', mbody=text, mtype='chat', mfrom=self.jid)
            msg.send()