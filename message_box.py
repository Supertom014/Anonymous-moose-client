# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


from tkinter import ttk
import tkinter
from alarm_sound import AlarmManager


class MessageBox(tkinter.Toplevel):
    def __init__(self, root, callback, ID, title='', button1_text='Yes', button2_text='No', text='', seconds=60):
        super().__init__()
        self.seconds = seconds
        self.callback = callback
        self.ID = ID
        self.button1_text = button1_text
        self.button2_text = button2_text
        self.protocol('WM_DELETE_WINDOW', lambda: 0)
        title_bar = root.winfo_screenheight()/25
        width = 200
        height = 100
        x = (root.winfo_screenwidth()/2)-width/2
        y = (root.winfo_screenheight()/2)-height/2-title_bar
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))
        self.resizable(width=False, height=False)
        self.timeout = TimeoutThread(seconds, self.timeout_func)
        self.timeout.daemon = True
        self.timeout.start()
        self.attributes("-topmost", 1)
        self.title(title)
        ttk.Label(self, text=text).pack(pady=10)
        ttk.Button(self, text=button1_text, command=self.button1).pack(side='left', padx=10)
        ttk.Button(self, text=button2_text, command=self.button2).pack(side='left', padx=10)
        self.alarm = AlarmManager("resource/analog-alarm-clock.wav", 6)

    def button1(self):
        self.kill_box()
        self.callback(self.button1_text, self.ID)

    def button2(self):
        self.kill_box()
        self.callback(self.button2_text, self.ID)

    def timeout_func(self):
        self.kill_box()
        self.callback('timeout', self.ID)

    def kill_box(self):
        self.timeout.disable()
        self.alarm.kill_sound()
        self.destroy()

from threading import Thread
class TimeoutThread(Thread):
    def __init__(self, seconds, callback):
        super().__init__()
        self.seconds = seconds
        self.callback = callback

    def disable(self):
        self.callback = lambda: 0

    def run(self):
        import time
        time.sleep(self.seconds)
        self.callback()

class InformationBox(tkinter.Toplevel):
    def __init__(self, root, height=140, width=250, callback=None, ID=0, title='', text='', button1_text='OK'):
        super().__init__()
        self.callback = callback
        self.ID = ID
        self.button1_text = button1_text
        self.protocol('WM_DELETE_WINDOW', lambda: 0)
        title_bar = root.winfo_screenheight()/25
        x = (root.winfo_screenwidth()/2)-width/2
        y = (root.winfo_screenheight()/2)-height/2-title_bar
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))
        self.resizable(width=False, height=False)
        self.attributes("-topmost", 1)
        self.title(title)
        ttk.Label(self, text=text).pack(pady=10)
        ttk.Button(self, text=button1_text, command=self.button1).pack(side='bottom', padx=10, pady=10,anchor='center')

    def button1(self):
        self.kill_box()
        if self.callback != None:
            self.callback(self.button1_text, self.ID)

    def kill_box(self):
        self.destroy()

if __name__ == '__main__':
    root = tkinter.Tk()
    root.withdraw()
    def callback(arg, id):
        print(arg, id)
        #root.destroy()
    MessageBox(root, callback, 'ID', text='Accept call', title='Ring ring...', seconds=10)
    InformationBox(root=root, callback=callback, ID='ID', text='Super bad connection problem', title='Connection problem')
    root.mainloop()