# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


import tkinter
import tkinter.scrolledtext
import multiprocessing
from threading_manager import CommunicationThreadingManager
from chat_window import ChatWindow
from message_box import MessageBox, InformationBox
from tkinter import messagebox
from alarm_sound import AlarmManager

from ctypes.wintypes import HWND, UINT, DWORD
import ctypes


class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", UINT),
        ("hwnd", HWND),
        ("dwFlags", DWORD),
        ("uCount", UINT),
        ("dwTimeout", DWORD)
    ]

from ctypes import Structure, windll, c_uint, sizeof, byref


class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]


def get_idle_duration():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

import logging
import os
import json
import time
from load_config import LoadConfig
import logging.config
logging.getLogger("sleekxmpp").setLevel(60)  # Disable sleekxmpp logging


def setup_logging(default_path=r'resource\logging.json', default_level=logging.INFO):
    """Setup logging configuration"""
    if not os.path.isdir('logging'):
        os.mkdir('logging')
    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

setup_logging()
logger = logging.getLogger(__name__)
logger.info('Client started.')


class MainWindow(object):
    def __init__(self, root):
        multiprocessing.freeze_support()
        self.root = root
        self.role_accept_flag = multiprocessing.Event()
        self.role_accept_flag.clear()
        self.block_flag = multiprocessing.Event()
        self.gui_call_queue = multiprocessing.Queue()
        self.outgoing_queue = multiprocessing.Queue()
        lc = LoadConfig()
        self.options = lc.get_options()
        self.policy_list_list = lc.get_policy_list_list()
        self.com_thread_man = CommunicationThreadingManager(self.gui_call_queue,
                                                            self.outgoing_queue, self.options)
        # Create a toplevel menu
        menubar = tkinter.Menu(root)
        root.config(menu=menubar)
        root.title('NightLine anonymous chat client')
        root.protocol('WM_DELETE_WINDOW', self.x_clicked)
        root.minsize(width=310, height=100)
        
        # Menu bar
        self.menu = tkinter.Menu(root)
        self.submenu = tkinter.Menu(self.menu, tearoff=0)
        self.submenu.add_command(label = 'Help', command = self.help_window)
        self.submenu.add_command(label = 'Quit', command = self.quit)
        self.menu.add_cascade(label='Menu', menu=self.submenu)
        root.config(menu=self.menu)

        # Connection data GUI
        self.connection_frame = tkinter.Frame(root)
        self.connection_frame.pack(anchor='center')
        self.status_text = tkinter.StringVar()
        self.status_text.set('Connecting...')
        tkinter.Label(self.connection_frame, textvariable=self.status_text).pack()

        # self.gui_statuss = {}
        # self.row_num = 0

        self.warning_window_open = multiprocessing.Event()

        self.chat_in_progress = multiprocessing.Event()
        self.chat_in_progress.clear()
        self.ring_queue = []
        self.chat_window_handle = None
        self.ring_message_box = MessageBox
        self.ring_accept = []
        self.periodic_call()

    def periodic_call(self):
        self.root.after(100, self.periodic_call)
        # Queue will be a ('name', (args)) for one of the following
        # self.message, self.chat_state, self.update_status, self.ring, self.ring_result, self.connection_problems
        raw_msg = ''
        if len(self.ring_queue) > 0 and not self.chat_in_progress.is_set() and not len(self.ring_accept) > 0:
            self.ring(self.ring_queue.pop(0), 'queue')
        try:
            raw_msg = self.gui_call_queue.get_nowait()
        except:
            return
        try:
            function, args = raw_msg
        except ValueError:
            logger.warning('Invalid message put in gui_call_queue: %s', str(raw_msg))
            return
        getattr(self, function)(*args)

    def connection_problems(self, *args):
        logger.info("Connection problem: %s", args[0])
        if args[0] == 'inter_com_down':
            # self.remove_status()
            # root, callback, ID, title='', button1_text='OK', text=''
            if not self.warning_window_open.is_set():
                self.status_text.set("Connection to inter_com lost\n"
                                     "The internet probably hiccuped\n"
                                     "It'll come back...")
                #self.warning_window_open.set()
                #WarningBox(self.root, self.warning_msg_callback, 'warn', title='Connection problem...',
                #           text='Connection to inter_com lost!\n'
                #                'Please ensure machine has a internet connection\n'
                #                'Attempting to reconnect...')

        elif args[0] == 'server_down':
            # self.remove_status()
            if not self.warning_window_open.is_set():
                self.status_text.set("Connection to server lost\n"
                                     "It might come back up.\n"
                                     "If it doesn't then please have\n"
                                     "a look at the help menu.")
                #self.warning_window_open.set()
                #WarningBox(self.root, self.warning_msg_callback, 'warn', title='Connection problem...',
                #           text='Connection to NL chat server lost!\n'
                #                            'Server maybe offline.\n'
                #                            'Attempting to reconnect...')

    def warning_msg_callback(self, *args):
        self.warning_window_open.clear()

    # def remove_status(self):
    #     self.connection_frame.destroy()
    #     self.connection_frame = tkinter.Frame(root)
    #     self.connection_frame.pack(anchor='center')

    def update_status(self, status):
        logger.debug(status['services'])
        temp_string = ''
        for service in status['services']:  # Build string
            temp_string += service['name']+': '+service['status']+'\n'
        self.status_text.set(temp_string)
        return

        # for service in status['services']:
        #     try:
        #         self.gui_statuss[service['name']].set(service['status'])
        #     except KeyError:
        #         tkinter.Label(self.connection_frame, text=service['name']).grid(row=self.row_num, column=0)
        #         text_var = tkinter.StringVar()
        #         text_var.set(service['status'])
        #         tkinter.Label(self.connection_frame, textvariable=text_var).grid(row=self.row_num, column=1)
        #         self.gui_statuss.update({service['name']: text_var})
        #         self.row_num += 1
        #         self.connection_frame.update()


    def chat_state(self, msg):
        self.chat_window_handle.chat_state(msg['state'])

    def message(self, msg):
        text = ''
        for piece in msg['msg']:
            text += piece
            print(text)
        if self.chat_in_progress.is_set():
            self.chat_window_handle.add_text_to_msg_history(False, text)
            # TODO Copy functionality of code below with a thread
            #if get_idle_duration() > 60:  # Check if an User alert is needed
            #    alarm = AlarmManager('resource/analog-alarm-clock.wav', 6)
            #    while True:  # This wont affect UI experience. # Oh yes it will!
            #        if get_idle_duration() < 10:
            #            break
            #    alarm.kill_sound()
        else:
            logger.warning('Chat msg received, but no chat window open')

    def ring_result(self, msg, uuid):
        if self.ring_message_box.ID == msg['ID']:
            self.ring_message_box.kill_box()
            self.chat_in_progress.clear()
        for x in range(0, len(self.ring_queue)):
            if self.ring_queue[x]['ID'] == msg['ID']:
                self.ring_queue.pop(x)
        if msg['UUID'] == uuid:
            self.chat_window_handle = self.spawn_chat()
        else:
            if msg['ID'] in self.ring_accept:
                messagebox.showinfo('Sorry', 'Call taken by another user.')
        if msg['ID'] in self.ring_accept:
                self.ring_accept.remove(msg['ID'])

    def ring(self, msg, origin):  # Function responsible for acting on ring commands
        if int(float(msg['time']) - time.time()) <= 0:
            return  # Item will be forgotten
        if not self.chat_in_progress.is_set():
            logger.debug('Showing alert for ring %s', msg['ID'])
            self.chat_in_progress.set()  # Stop other ring boxes appearing
            seconds = int(float(msg['time']) - time.time())
            if seconds > 5:
                self.ring_message_box = MessageBox(root, callback=self.ring_message_callback, ID=msg['ID'],
                                                   title="Ring ring...", text='Accept call?', seconds=seconds)
        else:
            logger.debug('Adding ring %s to the queue', msg['ID'])
            self.ring_queue.append({'ID': msg['ID'], 'time': msg['time']})

    def ring_message_callback(self, arg, ID):
        self.chat_in_progress.clear()  # Allow other ring boxes to appear again
        if arg == 'Yes':
            self.ring_accept.append(ID)
            self.com_thread_man.inter_com_handle.pickup_ring(True, ID)

    def spawn_chat(self):
        msg_func = self.com_thread_man.inter_com_handle.send_message
        disassociate_func = self.com_thread_man.inter_com_handle.disassociate_from_client
        chat_window = ChatWindow(self.root, msg_func, disassociate_func, self.chat_in_progress, self.policy_list_list, self.options)
        self.chat_in_progress.set()
        chat_window.attributes("-topmost", 1)
        return chat_window
    
    def flash_window(self, window_handle):
        # print(window_handle.wm_frame())
        flashinfo = FLASHWINFO(ctypes.sizeof(FLASHWINFO), int(window_handle.wm_frame(),16), int('F',16), 100, 0)#C03
        ctypes.windll.user32.FlashWindowEx(ctypes.pointer(flashinfo))
    
    def x_clicked(self):
        root.iconify()

    def help_window(self):
        InformationBox(root=self.root, title='Help', text='Hi developer here. If the sever (black window) or\n'
                                                          'this client crashes then please take a screenshot if you can\n'
                                                          'try to note the time as well and post it to NL group work on facebook.\n\n'
                                                          'Just telling us that something crashed can be a huge help.', width=500)

    def quit(self):
        if messagebox.askyesno(title='Quit?', message='Are you sure?'):
            root.destroy()
            self.com_thread_man.inter_com_handle.disconnect_client()
            self.com_thread_man.kill_all()


root = tkinter.Tk()
x = MainWindow(root)
root.iconbitmap(default='resource/icon.ico')
root.mainloop()
raise SystemExit