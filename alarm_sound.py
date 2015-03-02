# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#

from threading import Thread
import multiprocessing


class AlarmManager(object):
    """Manages the threads"""
    def __init__(self, soundfilename, wait_time):
        self.sound_kill_event = multiprocessing.Event()
        self.start_sound(soundfilename, wait_time)
        self.sound_thread = None  # Thread handle

    def start_sound(self, soundfilename, wait_time):
        self.sound_kill_event.clear()
        self.sound_thread = AlarmThread(self.sound_kill_event, soundfilename, wait_time)
        self.sound_thread.daemon = True
        self.sound_thread.start()

    def kill_sound(self):
        self.sound_kill_event.set()


class AlarmThread(Thread):
    def __init__(self, kill_event, soundfilename, wait_time):
        super().__init__()
        self.kill_event = kill_event
        self.soundfilename = soundfilename
        self.wait_time = wait_time
        
    def run(self):
        import winsound
        import time
        while True:
            time.sleep(self.wait_time)
            if self.kill_event.is_set():
                # print('Sound thread ending')
                break
            winsound.PlaySound(self.soundfilename, winsound.SND_FILENAME)
            # print('enter sleep')
        return
        
if __name__ == '__main__':
    import tkinter
    from tkinter import messagebox
    root = tkinter.Tk()
    root.withdraw()
    x = AlarmManager('resource/analog-alarm-clock.wav', 6)
    messagebox.askyesno('Accept?')
    x.kill_sound()