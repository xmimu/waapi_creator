#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File:        waapi_creator.py
@Author:      lgx
@Contact:     1101588023@qq.com
@Time:        2023/09/16 10:49
@Description: 批量创建 Wwise 空对象
"""
import sys

import PySimpleGUI as sg
from Socket_Singleton import Socket_Singleton

from waapi_support import WaapiClientX, CannotConnectToWaapiException
from waapi_support import WaapiObject
from waapi_support import WAAPI_URI as URI


class WaapiCreator:

    def __init__(self):
        self.client: WaapiClientX | None = None
        self.selected_name = ''
        self.selected_type = ''
        self.selected_id = ''
        self.create_type = ''
        self.create_window()
        self.run()

    def connect(self):
        try:
            self.client = WaapiClientX(allow_exception=True)
            selected_result = self.client.call(URI.ak_wwise_ui_getselectedobjects,
                                               args={'return': ['id', 'name', 'type']})
            if selected_result and selected_result['objects']:
                self.selected_id = selected_result['objects'][0]['id']
                self.selected_name = selected_result['objects'][0]['name']
                self.selected_type = selected_result['objects'][0]['type']
            self.client.subscribe(URI.ak_wwise_ui_selectionchanged, self.update_selected_object)
        except  Exception as e:
            sg.popup_error(str(e), keep_on_top=True)

    def disconnect(self):
        if self.client is not None:
            self.client.disconnect()
            self.client = None

    def update_selected_object(self, objects):
        if getattr(self, 'window') and len(objects) == 1:
            self.selected_id = objects[0]['id']
            self.selected_name = objects[0]['name']
            self.selected_type = objects[0]['type']
            self.window['-SELECTED_PATH-'].update(f'{self.selected_name} | {self.selected_type}')

    def create_window(self):
        self.type_list = [i for i in WaapiObject.__dict__.values() if isinstance(i, str) and not i.startswith('__')]
        self.type_list.remove('waapi_support.waapi_object')

        # menu_def = [['&Help', ['&About']]]

        layout = [
            # [sg.Menu(menu_def)],
            [sg.Text('Wapi Creator', font=('Helvetica', 16)),
             sg.Checkbox('Pin', default=True, key='-PIN-', enable_events=True),
             sg.Button('Connect to WAAPI', key='-CONNECT-'),],
            [sg.Text('Parent from selected: ', size=(15, 1)),
             sg.Text(f'{self.selected_name} | {self.selected_type}', key='-SELECTED_PATH-'), ],
            [sg.Text('Type to create: ', size=(15, 1)), sg.Text('Search'),
             sg.Input(tooltip='Search type', size=(10, 1), key='-SEARCH_TYPE-', enable_events=True),
             sg.Combo(self.type_list, default_value=self.type_list[0],
                      key='-TYPE_LIST-', readonly=True, enable_events=True)],
            [sg.Checkbox('Is voice', key='-IS_VOICE-', visible=False),
             sg.Checkbox('Is Random', default=True, key='-IS_RANDOM-', visible=False)],
            [sg.Button('Create', key='-CREATE-', size=(10, 1)), ],
            [
                sg.Frame(title='Input:', layout=[[sg.Multiline(size=(40, 20), key='-INPUT-')]]),
                sg.Frame(title='Output:', layout=[[sg.Output(size=(40, 20), key='-OUTPUT-', echo_stdout_stderr=True)]])
            ],
        ]
        self.window = sg.Window('WAAPI Creator', layout, keep_on_top=True, finalize=True)

    def run(self):
        def checkbox_show(value: str):
            if value == 'Sound':
                self.window['-IS_VOICE-'].update(visible=True)
            else:
                self.window['-IS_VOICE-'].update(visible=False)
            if value == 'RandomSequenceContainer':
                self.window['-IS_RANDOM-'].update(visible=True)
            else:
                self.window['-IS_RANDOM-'].update(visible=False)

        # ==================== Main Loop ====================
        while True:
            event, values = self.window.read()
            # print(event, values)
            if event in (sg.WIN_CLOSED, 'Exit'):
                break

            if event == '-PIN-':
                self.window.TKroot.wm_attributes('-topmost', values['-PIN-'])
            if event == '-CONNECT-':
                self.window['-CONNECT-'].update(disabled=True)
                self.connect()
                if self.client is None:
                    self.window['-CONNECT-'].update(disabled=False)
                else:
                    print('Connected to Wwise')
                    self.window['-SELECTED_PATH-'].update(f'{self.selected_name} | {self.selected_type}')
            if event == '-SEARCH_TYPE-':
                result = [i for i in self.type_list if i.lower().startswith(values['-SEARCH_TYPE-'].lower())]
                if result:
                    self.window['-TYPE_LIST-'].update(result[0])
                    checkbox_show(result[0])
                else:
                    self.window['-TYPE_LIST-'].update('')
                    checkbox_show('')
            if event == '-TYPE_LIST-':
                self.window['-SEARCH_TYPE-'].update(values['-TYPE_LIST-'])
                checkbox_show(values['-TYPE_LIST-'])
            if event == '-CREATE-':
                self.window['-CREATE-'].update(disabled=True)
                if self.client is None:
                    sg.popup_error('Cannot connect to Wwise', keep_on_top=True)
                else:
                    name_list = [i.strip() for i in values['-INPUT-'].split('\n') if i.strip()]
                    parent_id = self.selected_id
                    create_type = values['-TYPE_LIST-']
                    is_voice = values['-IS_VOICE-']
                    is_random = values['-IS_RANDOM-']
                    try:
                        self.waapi_create_objects(name_list, parent_id, create_type, is_voice, is_random)
                    except Exception as e:
                        sg.popup_error(e.kwargs['message'], keep_on_top=True)
                self.window['-CREATE-'].update(disabled=False)

        self.window.close()
        self.__del__()

    def __del__(self):
        self.disconnect()

    def waapi_create_objects(self, name_list, parent_id, create_type, is_voice, is_random):
        if self.client is None:
            print('Cannot connect to Wwise')
            return
        if not parent_id:
            print('Please select a object')
            return
        if not name_list:
            print('Please input a name')
            return

        args = {
            'parent': parent_id,
            'type': create_type,
        }

        for name in name_list:
            args['name'] = name

            if create_type == 'Sound':
                args['@IsVoice'] = is_voice
            if create_type == 'RandomSequenceContainer':
                args['@RandomOrSequence'] = is_random

            self.client.call(URI.ak_wwise_core_object_create, args=args)
            print(f'Create {name} successfully')



if __name__ == '__main__':
    Socket_Singleton()
    WaapiCreator()
