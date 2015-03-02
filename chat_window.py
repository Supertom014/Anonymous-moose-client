# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


import tkinter
from tkinter import ttk
import enchant
from enchant import tokenize
import time
from policy_loader import SubMenuConstructor
import logging

logger = logging.getLogger(__name__)


class ChatWindow(tkinter.Toplevel):
    def __init__(self, root, outgoing_msg_func, closing_window_func, chat_in_progress, policy_list_list, options):
        super().__init__()
        self.root = root
        self.outgoing_msg_func = outgoing_msg_func
        self.closing_window_func = closing_window_func
        self.chat_in_progress = chat_in_progress
        self.options = options
        # self.title('User '+str(user_id))
        self.title('Caller')
        self.protocol('WM_DELETE_WINDOW', self.x_clicked)
        self.minsize(width=500, height=300)

        # Chat state
        chat_state_frame = tkinter.Frame(self)
        #tkinter.Label(chat_state_frame, text="User is").pack(side="left")
        self.chat_state_var = tkinter.StringVar()
        self.chat_state_var.set('')
        tkinter.Label(chat_state_frame, textvariable=self.chat_state_var).pack()#side="left")
        chat_state_frame.pack(fill="x")

        # Message log
        self.msg_history_frame = ttk.Frame(self)
        self.msg_history_scroll = ttk.Scrollbar(self.msg_history_frame)
        self.msg_history_scroll.pack(side="right", fill="y", expand=False)
        self.msg_history = tkinter.Text(self.msg_history_frame, width=50, height=5,
                                        yscrollcommand=self.msg_history_scroll.set, wrap='word')
        self.msg_history.pack(side="left", fill="both", expand=True)
        self.msg_history.tag_configure('nightline', foreground='red')
        self.msg_history.tag_configure('user', foreground='blue')
        self.msg_history.config(font='sans 12 normal')
        self.msg_history_scroll.config(command=self.msg_history.yview)
        self.msg_history_frame.pack(expand=True, fill="both")
        
        # Reply box
        reply_frame = ttk.Frame(self)
        reply_text_scroll = ttk.Scrollbar(reply_frame)
        reply_text_box = tkinter.Text(reply_frame, width=45, height=5,
                                      yscrollcommand=reply_text_scroll.set, wrap='word', maxundo=10, undo=True)
        reply_text_box.pack(side="left", fill="both", expand=True)
        reply_text_box.config(font='sans 12 normal')
        reply_text_scroll.pack(side="left", fill="y", expand=False)
        reply_text_scroll.config(command=reply_text_box.yview)
        self.reply_text_box = reply_text_box
        self.reply_text_box.bind('<Return>', self.send_msg_btn)  # <Return>
        button = ttk.Button(reply_frame, text='Send', command=self.send_msg_btn)
        button.pack(side="left", fill="both", expand=False)
        reply_frame.pack(expand=False, fill="x")
        self.update()
        
        # Right click menus
        self.history_box_menu = tkinter.Menu(root, tearoff=0)
        self.history_box_menu.add_command(label="Copy", command=lambda: self.copy_to_clipboard(self.msg_history))
        self.msg_history.bind("<Button-3>", self.history_box_right_click_menu)
        
        self.send_box_menu = tkinter.Menu(root, tearoff=0)
        self.send_box_menu.add_command(label="Copy", command=lambda: self.copy_to_clipboard(self.reply_text_box))
        self.send_box_menu.add_command(label="Paste", command=lambda: self.paste_from_clipboard(self.reply_text_box))
        self.send_box_menu_enabled = True
        self.bind("<Button-1>", lambda x: self.enable_normal_context_menu())
        
        
        self.reply_text_box.bind("<Button-3>", self.send_box_context_menu)
        self.reply_text_box.bind('<Control-Key-z>', lambda event: self.text_undo_redo(self.reply_text_box, 'undo'))
        self.reply_text_box.bind('<Control-Key-y>', lambda event: self.text_undo_redo(self.reply_text_box, 'redo'))
        
        #Spell check
        self.reply_text_box.bind("<Key>", lambda event: root.after(1, 
                                            lambda event=event: self.spellcheck(event, self.reply_text_box, 
                                                self.reply_text_box.get(1.0, "end")[:-1])))
        #self.reply_text_box.bind("<Command-Return>", self.return_key_bindings)
        self.spell_checker = enchant.Dict('en_BG')
        self.word_spliter = tokenize.get_tokenizer('en_GB')
        
        # Menu bar
        self.menu = tkinter.Menu(self)
        for policy_list in policy_list_list:
            SubMenuConstructor(self.menu, self.reply_text_box, policy_list).add_to_menu()
        self.config(menu=self.menu)

        # Welcome message
        self.start_msg_ignore_count = 0
        self.send_msg(self.options['messages']['welcome_message'])
    
    def return_key_bindings(self, event):
        print('pop')
        self.spellcheck(event, self.reply_text_box, self.reply_text_box.get(1.0, "end")[:-1])
        self.save_state(event)
        
    def save_state(self, event):
        self.reply_text_box.edit_separator()
        
    def text_undo_redo(self, textbox, action):
        if action == 'undo':
            try:
                textbox.edit_undo()
            except:
                pass
        else:
            try:
                textbox.edit_redo()
            except:
                pass
    
    def spellcheck(self, event, textbox, text):
        if not textbox.edit_modified():
            return
        textbox.edit_modified(False)
        for tag in textbox.tag_names():
            textbox.tag_delete(tag)
        for word, pos in self.word_spliter(text):
            index_start = pos
            index_end = pos + len(word)
            if not self.spell_checker.check(word):
                textbox.tag_add(word, '1.0 + '+str(index_start)+' chars', '1.0 + '+str(index_end)+' chars')
                textbox.tag_bind(word, '<Button-3>', lambda event, word=word, index_start=index_start, index_end=index_end:
                                                        self.spellcheck_contex_menu(event, textbox, (index_start, index_end, word)))
                textbox.tag_configure(word, underline=1, foreground = "#D41919")
    
    def spellcheck_contex_menu(self, event, textbox, word_info):
        index_start, index_end, word = word_info
        sug_list = self.spell_checker.suggest(word)
        temp_menu = tkinter.Menu(self.root, tearoff=0)
        for sug in sug_list:
            temp_menu.add_command(label=sug, command=lambda new_word=sug: self.replace_word(temp_menu, textbox, index_start, index_end, new_word))
        temp_menu.add_separator()
        temp_menu.add_command(label="Copy", command=lambda: self.copy_to_clipboard(self.reply_text_box))
        temp_menu.add_command(label="Paste", command=lambda: self.paste_from_clipboard(self.reply_text_box))
        self.send_box_menu_enabled = False  # Disable normal context menu
        temp_menu.post(event.x_root, event.y_root)
        
    def enable_normal_context_menu(self):
        self.send_box_menu_enabled = True
    
    def replace_word(self, menu, textbox, index_start, index_end, new_word):
        textbox.delete('1.0 + '+str(index_start)+' chars', '1.0 + '+str(index_end)+' chars')
        textbox.insert('1.0 + '+str(index_start)+' chars', new_word)
        self.spellcheck(None, textbox, textbox.get(1.0, "end")[:-1])
        menu.unpost()
        self.root.after(1,  self.enable_normal_context_menu)
    
    
    def copy_to_clipboard(self, text_handle):
        text = ''
        try:
            text = text_handle.selection_get()
        except:  # TODO Narrow exception
            logger.info('Nothing to copy to clipboard')
        if text == '':
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.after(1,  self.enable_normal_context_menu)
        
    def paste_from_clipboard(self, text_handle):
        self.save_state(None)
        text = self.root.selection_get(selection="CLIPBOARD")
        try:
            text = text_handle.selection_get()
            text_handle.delete("SEL_FIRST", "SEL_LAST")
            text_handle.insert("insert", text)
        except:
            text_handle.insert("insert", text)
        self.root.after(1,  self.enable_normal_context_menu)
    
    def x_clicked(self):
        self.chat_in_progress.clear()
        self.destroy()
        self.closing_window_func()
        
    def send_msg_btn(self, *args):
        msg = self.reply_text_box.get(1.0, tkinter.END)[:-1]
        if len(msg) > 0:
            self.send_msg(msg)
            # The bound key will be added the the text box after the function exits
            # Therefore any delay whatsoever will insert the delayed_delete function after the text box key event.
            self.root.after(1, self.delayed_delete)

    def delayed_delete(self, *args):
        self.reply_text_box.delete(1.0, tkinter.END)

    def send_msg(self, msg):
        self.outgoing_msg_func(msg)
        self.add_text_to_msg_history(True, msg)

    def chat_state(self, state):
        label = "User is %s" % state
        if state == 'no_state':
            label = 'Chat state not avalibile.'
        self.chat_state_var.set(label)

    def add_text_to_msg_history(self, we_sent, msg):
        if msg[-17:] == 'Send Y to Accept.':
            self.outgoing_msg_func('Y')
            self.start_msg_ignore_count = 1
            return
        if self.start_msg_ignore_count > 0:
            self.start_msg_ignore_count -= 1
            if self.start_msg_ignore_count == 0:
                # self.send_msg(self.options['messages']['welcome_message'])
                self.outgoing_msg_func(self.options['messages']['welcome_message'])
            return

        current_time = time.ctime().split()[3]
        msg += '\n'
        if we_sent:
            msg_meta = '('+current_time+') NL: '
            self.msg_history.config(state="normal")
            self.msg_history.insert("end", msg_meta, 'nightline')
        else:
            msg_meta = '('+current_time+') User: '
            self.msg_history.config(state="normal")
            self.msg_history.insert("end", msg_meta, 'user')
        self.msg_history.insert("end", msg)
        self.msg_history.config(state="disabled")
        self.msg_history.yview_pickplace("end")
        
    def history_box_right_click_menu(self, event):
        self.history_box_menu.post(event.x_root, event.y_root)
        
    def send_box_context_menu(self, event):
        if self.send_box_menu_enabled:
            self.send_box_menu.post(event.x_root, event.y_root)
        self.send_box_menu_enabled = True
        
    def reappear(self):
        self.deiconify()
        # self.send_welcome_message()

if __name__ == '__main__':
    import multiprocessing
    chat_in_progress = multiprocessing.Event()
    root = tkinter.Tk()
    root.withdraw()
    policy_list_list = [['Place holder', {'name': 'name', 'text': 'text place holder'}]]

    def outgoing_msg_func(msg):
        print(msg)

    def close_window_func():
        print('Window closing')
        root.destroy()
        
    x = ChatWindow(root, outgoing_msg_func, close_window_func, chat_in_progress, policy_list_list,
                   {'messages': {'welcome_message': 'Welcome message.'}})
    x.chat_state('idle')
    root.mainloop()
    raise SystemExit