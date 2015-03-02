# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


from threading import Thread
from inter_com_xmpp import InterComXMPP
from timeout_threads import TimeoutThreadLock, RepeatWhileTrue
import time
from threading import Lock
import multiprocessing
import uuid
import base64
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import json
import logging
logger = logging.getLogger(__name__)


class CommunicationThreadingManager(object):
    """Manages the communication threads"""
    def __init__(self, gui_call_queue, outgoing_queue, options):
        import multiprocessing
        self.outgoing_queue = outgoing_queue
        self.options = options
        self.kill_event = multiprocessing.Event()
        self.inter_com_handle = InterCommunication(self.kill_event, gui_call_queue,
                                                            self.outgoing_queue, self.options)
        self.start_communication_threads()

    def kill_all(self):
        """Stop all running communication threads"""
        self.kill_event.set()  # Send kill signal to threads
        self.inter_com_handle.join()

    def start_communication_threads(self):
        """Starts the communication thread"""
        self.inter_com_handle.daemon = True
        self.inter_com_handle.start()

class InterCommunication(Thread):
    def __init__(self, kill_event, gui_call_queue, outgoing_queue, options):
        super().__init__()
        self.kill_event = kill_event
        self.gui_call_queue = gui_call_queue
        self.outgoing_queue = outgoing_queue
        self.username = options['accounts']['inter_com']['username']
        self.password = options['accounts']['inter_com']['password']
        self.uuid = ''
        self.inter_com = None #InterComXMPP
        self.bobs_keys = RSA
        self.bobs_cipher = PKCS1_OAEP
        try:
            alices_key = RSA.importKey(options['alices_public_key'])
            self.alices_cipher = PKCS1_OAEP.new(alices_key)
        except:
            pass
        server_timeout_lock = Lock()
        timeout = TimeoutThreadLock(server_timeout_lock, 60, self.server_timed_out, '')
        timeout.daemon = True
        timeout.start()
        self.server_timeout = {'lock': server_timeout_lock, 'timeout': timeout}
        self.probing_for_server = multiprocessing.Event()
        self.probing_for_server.set()

    def restart_server_timeout_thread(self):
        self.server_timeout['lock'].acquire_lock()
        self.server_timeout['timeout'].disable()
        self.server_timeout['lock'].release_lock()
        server_timeout_lock = Lock()
        timeout = TimeoutThreadLock(server_timeout_lock, 60, self.server_timed_out, '')
        timeout.daemon = True
        timeout.start()
        self.server_timeout = {'lock': server_timeout_lock, 'timeout': timeout}


    def server_timed_out(self, arg):
        logger.info('Server timed out')
        self.gui_call_queue.put(('connection_problems', ('server_down',)))
        self.probing_for_server.clear()
        time.sleep(2)
        self.probing_for_server.set()
        thread = RepeatWhileTrue(self.probing_for_server, 10, self.client_init)
        thread.daemon = True
        thread.start()

    def look_for_server(self):
        self.probing_for_server.set()
        thread = RepeatWhileTrue(self.probing_for_server, 8, self.client_init)
        thread.daemon = True
        thread.start()

    def update_server_timer(self):
        self.server_timeout['lock'].acquire_lock()
        self.server_timeout['timeout'].set_time(20)
        self.server_timeout['lock'].release_lock()

    def connection_problems(self):
        self.gui_call_queue.put(('connection_problems', ('inter_com_down',)))

    def pickup_ring(self, accept, ID):
        if accept:
            self.encrypt_and_send({'type': 'ringACK', 'ID': ID, 'UUID': self.uuid})

    def send_message(self, text):
        self.encrypt_and_send({'type': 'msg', 'msg': text, 'I/O': 'out', 'UUID': self.uuid})

    def disassociate_from_client(self):
        self.encrypt_and_send({'type': 'disassociate', 'UUID': self.uuid})

    def disconnect_client(self):
        self.encrypt_and_send({'type': 'disconnect', 'UUID': self.uuid})

    def client_init(self):
        logger.debug('key command sent')
        self.encrypt_and_send({'type': 'key', 'UUID': self.uuid,
                               'key': self.bobs_keys.publickey().exportKey('PEM').decode('utf')})

    def encrypt_and_send(self, msg):
        uuid = msg['UUID']
        msg = json.dumps(msg)
        messages = []
        chars = len(msg)
        x = 0
        while True:
            if chars > 214:
                messages.append(
                    base64.standard_b64encode(
                        self.alices_cipher.encrypt(bytes(msg[214*x:214*(x+1)],encoding='utf'))
                    ).decode('utf')
                )
                x += 1
                chars -= 214
            else:
                messages.append(
                    base64.standard_b64encode(
                        self.alices_cipher.encrypt(bytes(msg[214*x:len(msg)], encoding='utf'))
                    ).decode('utf')
                )
                break
        message = json.dumps({'messages': messages, 'UUID': uuid, 'to': 'alice'})
        # If the client never gives the server a chance to probe it then
        # the client will not receive any messages to refresh it's timer.
        self.update_server_timer()
        self.inter_com.reply_message(message)

    def decrypt_reconstruct(self, msg):
        # {'messages': messages, 'UUID': uuid, 'to': 'alice/bob'}
        # messages is a list of base64 encoded byte arrays.
        # They are individually encrypted blocks that combine into a json message.
        try:
            message = b''
            for part in msg['messages']:
                message += self.bobs_cipher.decrypt(base64.b64decode(part))
            return json.loads(message.decode('utf'))
        except Exception as error:
            logger.warning('Could not decrypt incoming message')
            return False
    def inter_com_update(self, arg):
        self.connection_problems()

    def incoming_function(self, msg):
        if "inter_com_update" in msg.keys():
            self.inter_com_update("inter_com_update")
        # {'messages': messages, 'UUID': uuid}
        if msg['UUID'] != self.uuid or msg['to'] != 'bob':  # Is message for me?
            return
        msg = self.decrypt_reconstruct(msg)
        if not msg:  # Not encrypted or junk
            try:
                logger.info('Got message: %s', 'server_online')
                if msg['type'] == 'server_online':
                    self.client_init()
            except KeyError:
                pass  # Got junk
            return
        # Back to original msg form
        self.update_server_timer()
        if msg['type'] == 'probe':
            logger.debug('Got probe')
            self.encrypt_and_send({'type': 'probeACK', 'UUID': self.uuid})
            return
        logger.info('Got message: %s', msg['type'])
        if msg['type'] == 'msg':
            if msg['UUID'] == self.uuid and msg['I/O'] == 'in':
                self.gui_call_queue.put(('message', (msg,)))
                # self.gui_message(msg)
        elif msg['type'] == 'status':
            self.probing_for_server.clear() # This incoming command signals the end of probing_for_a_server
            self.gui_call_queue.put(('update_status', (msg,)))
            self.restart_server_timeout_thread()
        elif msg['type'] == 'ring':
            self.gui_call_queue.put(('ring', (msg, 'fresh')))
        elif msg['type'] == 'ringACKACK':
            self.gui_call_queue.put(('ring_result', (msg, self.uuid)))

        elif msg['type'] == 'chat_state':
            self.gui_call_queue.put(('chat_state', (msg,)))
            # self.incoming_chat_state(msg)


    def run(self):
        self.bobs_keys = RSA.generate(2048)
        self.bobs_cipher = PKCS1_OAEP.new(self.bobs_keys)
        self.uuid = str(uuid.uuid4())
        logger.info('UUID: %s', self.uuid)
        self.inter_com = InterComXMPP(self.username+'/'+self.uuid, self.password,
                                      self.incoming_function, self.connection_problems)
        if self.inter_com.connect():
            self.inter_com.process()
            logger.info('Connected to: %s', 'inter_com')
        else:
            logger.info('Unable to connect to: %s', 'inter_com')
        self.client_init()
        self.look_for_server()
        while True:  # main thread loop
            msg_to_process = False
            try:
                user_id, msg, state = self.outgoing_queue.get(timeout=0.5)
                msg_to_process = True
            except:  # TODO Narrow exception
                pass
            if msg_to_process:
                pass
            if self.kill_event.is_set():
                self.inter_com.disconnect()
                logger.info('%s thread ending', 'inter_com')
                break
        return