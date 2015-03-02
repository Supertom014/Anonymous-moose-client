# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


import tkinter
import logging
logger = logging.getLogger(__name__)


class LoadPolicy(object):
    def __init__(self, text, filename):
        try:
            text = text.split('\r\n\r\n')
        except:  # TODO Narrow exception
            logger.warning('A Incorrect formating in %s', filename)
        self.policy_list = []
        try:
            self.menu_name = text[0]
            self.policy_list.append(self.menu_name)
            for x in text[1:]:
                x = x.split('\r\n', 1)
                self.policy_list.append({'name': x[0], 'text': x[1]})
        except:  # TODO Narrow exception
            logger.warning('A Incorrect formating in %s', filename)
        
    def get_policy_list(self):
        if len(self.policy_list) == 0:
            return False
        return self.policy_list


class SubMenuConstructor(tkinter.Menu):
    def __init__(self, menu, text_handle, policy_list):
        super().__init__(menu, tearoff=0)
        self.menu = menu
        self.text_handle = text_handle
        self.sub_menu_name = policy_list[0]
        for policy in policy_list[1:]:
            self.add_command(label=policy['name'], command=lambda policy=policy: self.put_text(policy['text']))

    def put_text(self, text):
        self.text_handle.delete(1.0, 'end')
        self.text_handle.insert("end", text, 'user')

    def add_to_menu(self):
        # menu.config(menu=self)
        self.menu.add_cascade(label=self.sub_menu_name, menu=self)


if __name__ == '__main__':
    import tkinter
    root = tkinter.Tk()
    text = tkinter.Text(root)
    text.pack()
    import zipfile
    settings_zip_object = zipfile.ZipFile('settings.zip')
    namelist = settings_zip_object.namelist()
    policy_list_list = []
    for name in namelist:
        policy = settings_zip_object.open(name, mode='r', pwd=bytes('thomas', encoding='utf-8')).read()
        policy = policy.decode(encoding='utf-8')
        policy_list_list.append(LoadPolicy(root, policy, name).get_policy_list())
    menu = tkinter.Menu(root)
    for policy_list in policy_list_list:
        SubMenuConstructor(menu, text, policy_list).add_to_menu()
    root.config(menu=menu)
    root.mainloop()
    exit()