# -*- coding: utf-8 -*-
import os.path
import platform
from tkinter import filedialog
from tkinter import font
from tkinter import messagebox
from collections import deque
from tkinter import *
from tkinter.ttk import Frame, Button, Label, Combobox, Scrollbar

from utils.recommend import *


class Editor(Text):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, kwargs)
        fnt = font.Font(family='Times', size=20, weight="bold", underline=0)
        self.config(insertbackground='red', insertwidth=4, font=fnt)
        edge_fnt = font.Font(family='Times', size=12, underline=0)
        self.tag_configure("edge", background="light grey", foreground='DimGrey', font=edge_fnt)
        self.tag_configure("recommend", background='light green')
        self.tag_configure("category", background="SkyBlue1")

        def _ignore(e): return 'break'

        # Disable the default  copy behaivour when right click.
        # For MacOS, right click is button 2, other systems are button3
        self.bind('<Button-2>', _ignore)
        self.bind('<Button-3>', _ignore)

    def _highlight_entity(self, start: str, count: int, tagname: str):
        end = f'{start}+{count}c'
        star_pos = self.get(start, end).rfind('#')
        word_start = f"{start}+2c"
        word_end = f"{start}+{star_pos}c"
        self.tag_add(tagname, word_start, word_end)
        self.tag_add("edge", start, word_start)
        self.tag_add("edge", word_end, end)

    def show_annotation_tag(self, show: bool):
        self.tag_configure('edge', elide=not show)

    def highlight_recommend(self, start: str, count: int):
        self._highlight_entity(start, count, 'recommend')

    def highlight_entity(self, start: str, count: int):
        self._highlight_entity(start, count, 'category')

    def get_text(self) -> str:
        """get text from 0 to end"""
        return self.get("1.0", "end-1c")


class Application(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.Version = "YEDDA-V1.0 Annotator"
        self.OS = platform.system().lower()
        self.fileName = ""
        self.debug = False
        self.colorAllChunk = True
        self.use_recommend = BooleanVar(self, True)
        self.history = deque(maxlen=20)
        self.currentContent = deque(maxlen=1)
        self.pressCommand = {'a': "Artifical", 'b': "Event", 'c': "Fin-Concept", 'd': "Location",
                             'e': "Organization", 'f': "Person", 'g': "Sector", 'h': "Other"}
        self.labelEntryList = []
        self.shortcutLabelList = []
        self.configListLabel = None
        self.configListBox = None
        self.file_encoding = 'utf-8'

        # default GUI display parameter
        if len(self.pressCommand) > 20:
            self.textRow = len(self.pressCommand)
        else:
            self.textRow = 20
        self.textColumn = 5
        self.tagScheme = "BMES"
        self.onlyNP = False  ## for exporting sequence 
        self.keepRecommend = True

        '''
        self.segmented: for exporting sequence, if True then split words with space, else split character without space
        for example, if your data is segmented Chinese (or English) with words separated by a space, you need to set this flag as true
        if your data is Chinese without segmentation, you need to set this flag as False
        '''
        self.segmented = True  ## False for non-segmentated Chinese, True for English or Segmented Chinese
        self.configFile = "configs/default.config"
        self.entity_regex = r'\[\@.*?\#.*?\*\](?!\#)'
        self.insideNestEntityRe = r'\[\@\[\@(?!\[\@).*?\#.*?\*\]\#'
        self.recommendRe = r'\[\$.*?\#.*?\*\](?!\#)'
        self.goldAndrecomRe = r'\[\@.*?\#.*?\*\](?!\#)'
        if self.keepRecommend:
            self.goldAndrecomRe = r'\[[\@\$)].*?\#.*?\*\](?!\#)'
        ## configure color
        self.insideNestEntityColor = "light slate blue"
        self.selectColor = 'light salmon'
        self.textFontStyle = "Times"
        self.initUI()

    def initUI(self):
        self.master.title(self.Version)
        self.pack(fill=BOTH, expand=True)

        for i in range(0, self.textColumn):
            self.columnconfigure(i, weight=2)
        # self.columnconfigure(0, weight=2)
        self.columnconfigure(self.textColumn + 2, weight=1)
        self.columnconfigure(self.textColumn + 4, weight=1)
        for i in range(0, 16):
            self.rowconfigure(i, weight=1)

        self.lbl = Label(self, text="File: no file is opened")
        self.lbl.grid(sticky=W, pady=4, padx=5)
        self.text = Editor(self, selectbackground=self.selectColor)
        self.text.grid(row=1, column=0, columnspan=self.textColumn, rowspan=self.textRow, padx=12, sticky=E + W + S + N)

        scroll = Scrollbar(self, command=self.text.yview)
        scroll.grid(row=1, column=self.textColumn, rowspan=self.textRow, padx=0, sticky=E + W + S + N)
        self.text['yscrollcommand'] = scroll.set

        abtn = Button(self, text="Open", command=self.onOpen)
        abtn.grid(row=1, column=self.textColumn + 1)

        ubtn = Button(self, text="ReMap", command=self.renewPressCommand)
        ubtn.grid(row=2, column=self.textColumn + 1, pady=4)

        ubtn = Button(self, text="NewMap", command=self.savenewPressCommand)
        ubtn.grid(row=3, column=self.textColumn + 1, pady=4)

        exportbtn = Button(self, text="Export", command=self.generateSequenceFile)
        exportbtn.grid(row=4, column=self.textColumn + 1, pady=4)

        cbtn = Button(self, text="Quit", command=self.quit)
        cbtn.grid(row=5, column=self.textColumn + 1, pady=4)

        self.cursor_index_label = Label(self, text="1:0", foreground="red", font=(self.textFontStyle, 14, "bold"))
        self.cursor_index_label.grid(row=10, column=self.textColumn + 1, pady=4)

        recommend_label = Label(self, text="Recommend: ", foreground="Blue", font=(self.textFontStyle, 14, "bold"))
        recommend_label.grid(row=12, column=self.textColumn + 1, pady=4)
        recommend_check = Checkbutton(self, command=self.toggle_use_recommend, variable=self.use_recommend)
        recommend_check.grid(row=12, column=self.textColumn + 3, pady=4)

        Label(self, text="Show Tags: ").grid(row=13, column=self.textColumn + 1)
        should_show_tags = BooleanVar(self, True)
        should_show_tags.trace_add('write', lambda _, _1, _2: self.text.show_annotation_tag(should_show_tags.get()))
        show_tags_check = Checkbutton(self, variable=should_show_tags)
        show_tags_check.grid(row=13, column=self.textColumn + 3)

        lbl_entry = Label(self, text="Command:")
        lbl_entry.grid(row=self.textRow + 1, sticky=E + W + S + N, pady=4, padx=4)
        self.entry = Entry(self)
        self.entry.grid(row=self.textRow + 1, columnspan=self.textColumn + 1, rowspan=1, sticky=E + W + S + N, pady=4,
                        padx=80)
        self.entry.bind('<Return>', self.returnEnter)

        all_keys = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for press_key in all_keys:
            self.text.bind(press_key, self.textReturnEnter, add='')
            if self.OS != "windows":
                self.text.bind(f'<Control-Key-"{press_key}">', self.keepCurrent)
                self.text.bind(f'<Command-Key-"{press_key}">', self.keepCurrent)

        self.text.bind('<Control-Key-z>', self.backToHistory)

        self.text.bind('<Double-Button-1>', self.doubleLeftClick)
        self.text.bind('<ButtonRelease-1>', self.show_cursor_pos)
        self.text.bind('<KeyRelease>', self.show_cursor_pos)

        self.show_binding_widgets()

        self.enter = Button(self, text="Enter", command=self.returnButton)
        self.enter.grid(row=self.textRow + 1, column=self.textColumn + 1)

    def show_cursor_pos(self, event):
        cursor_index = self.text.index(INSERT)
        row, col = cursor_index.split('.')
        self.cursor_index_label.config(text=f"{row}:{col}")

    ## TODO: select entity by double left click
    def doubleLeftClick(self, event):
        if self.debug:
            print("Action Track: doubleLeftClick")
        pass
        # cursor_index = self.text.index(INSERT)
        # start_index = ("%s - %sc" % (cursor_index, 5))
        # end_index = ("%s + %sc" % (cursor_index, 5))
        # self.text.tag_add('SEL', '1.0',"end-1c")

    def toggle_use_recommend(self):
        if self.use_recommend.get() == True:
            pass
        else:
            content = self.text.get_text()
            content = removeRecommendContent(content, self.recommendRe)
            self.writeFile(self.fileName, content, '1.0')

    def onOpen(self):
        filename = filedialog.askopenfilename(
            filetypes=[('all files', '.*'), ('text files', '.txt'), ('ann files', '.ann')])
        if filename != '':
            self.text.delete("1.0", END)
            text = self.readFile(filename)
            self.text.insert(END, text)
            self.setNameLabel("File: " + filename)
            self.autoLoadNewFile(self.fileName, "1.0")
            self.text.mark_set(INSERT, "1.0")
            self.setCursorLabel(self.text.index(INSERT))

    def readFile(self, filename):
        f = open(filename)
        try:
            text = f.read()
            self.file_encoding = f.encoding
        except UnicodeDecodeError:
            f = open(filename, encoding='utf-8')
            text = f.read()
        self.fileName = filename
        return text

    def setFont(self, value):
        _family = self.textFontStyle
        _size = value
        _weight = "bold"
        _underline = 0
        fnt = font.Font(family=_family, size=_size, weight=_weight, underline=_underline)
        Text(self, font=fnt)

    def setNameLabel(self, new_file):
        self.lbl.config(text=new_file)

    def setCursorLabel(self, cursor_index):
        row, col = cursor_index.split('.')
        self.cursor_index_label.config(text=f"{row}:{col}")

    def returnButton(self):
        if self.debug:
            print("Action Track: returnButton")
        self.pushToHistory()
        # self.returnEnter(event)
        content = self.entry.get()
        self.clearCommand()
        self.executeEntryCommand(content)
        return content

    def returnEnter(self, event):
        if self.debug:
            print("Action Track: returnEnter")
        self.pushToHistory()
        content = self.entry.get()
        self.clearCommand()
        self.executeEntryCommand(content)
        return content

    def textReturnEnter(self, event):
        press_key = event.char
        if self.debug:
            print("Action Track: textReturnEnter")
        self.pushToHistory()
        print("event: ", press_key)
        self.clearCommand()
        self.executeCursorCommand(press_key.lower())
        return 'break'

    def backToHistory(self, event):
        if self.debug:
            print("Action Track: backToHistory")
        if len(self.history) > 0:
            content, cursor = self.history.pop()
            self.writeFile(self.fileName, content, cursor)
        else:
            print("History is empty!")

    def keepCurrent(self, event):
        if self.debug:
            print("Action Track: keepCurrent")
        print("keep current, insert:", INSERT)
        print("before:", self.text.index(INSERT))
        self.text.insert(INSERT, 'p')
        print("after:", self.text.index(INSERT))

    def clearCommand(self):
        if self.debug:
            print("Action Track: clearCommand")
        self.entry.delete(0, 'end')

    def executeCursorCommand(self, command):
        if self.debug:
            print("Action Track: executeCursorCommand")
        print("Command:" + command)
        try:
            cursor_index = self.text.index(SEL_LAST)
            aboveHalf_content = self.text.get('1.0', SEL_FIRST)
            followHalf_content = self.text.get(SEL_FIRST, "end-1c")
            selected_string = self.text.selection_get()
            if re.match(self.entity_regex, selected_string) != None:
                ## if have selected entity
                new_string_list = selected_string.strip('[@]').rsplit('#', 1)
                new_string = new_string_list[0]
                followHalf_content = followHalf_content.replace(selected_string, new_string, 1)
                selected_string = new_string
                # cursor_index = "%s - %sc" % (cursor_index, str(len(new_string_list[1])+4))
                cursor_index = cursor_index.split('.')[0] + "." + str(
                    int(cursor_index.split('.')[1]) - len(new_string_list[1]) + 4)
            afterEntity_content = followHalf_content[len(selected_string):]

            if command == "q":
                print('q: remove entity label')
            else:
                if len(selected_string) > 0:
                    entity_content, cursor_index = self.replaceString(selected_string, selected_string, command,
                                                                      cursor_index)
            aboveHalf_content += entity_content
            content = self.addRecommendContent(aboveHalf_content, afterEntity_content, self.use_recommend.get())
            content = content
            self.writeFile(self.fileName, content, cursor_index)
        except TclError:
            ## not select text
            cursor_index = self.text.index(INSERT)
            [line_id, column_id] = cursor_index.split('.')
            aboveLine_content = self.text.get('1.0', str(int(line_id) - 1) + '.end')
            belowLine_content = self.text.get(str(int(line_id) + 1) + '.0', "end-1c")
            line = self.text.get(line_id + '.0', line_id + '.end')
            matched_span = (-1, -1)
            detected_entity = -1  ## detected entity type:－1 not detected, 1 detected gold, 2 detected recommend
            for match in re.finditer(self.entity_regex, line):
                if match.span()[0] <= int(column_id) & int(column_id) <= match.span()[1]:
                    matched_span = match.span()
                    detected_entity = 1
                    break
            if detected_entity == -1:
                for match in re.finditer(self.recommendRe, line):
                    if match.span()[0] <= int(column_id) & int(column_id) <= match.span()[1]:
                        matched_span = match.span()
                        detected_entity = 2
                        break
            line_before_entity = line
            line_after_entity = ""
            if matched_span[1] > 0:
                selected_string = line[matched_span[0]:matched_span[1]]
                if detected_entity == 1:
                    new_string, old_entity_type = selected_string.strip('[@*]').rsplit('#', 1)
                elif detected_entity == 2:
                    new_string, old_entity_type = selected_string.strip('[$*]').rsplit('#', 1)
                line_before_entity = line[:matched_span[0]]
                line_after_entity = line[matched_span[1]:]
                selected_string = new_string
                entity_content = selected_string
                cursor_index = line_id + '.' + str(int(matched_span[1]) - (len(old_entity_type) + 4))
                if command == "q":
                    print('q: remove entity label')
                elif command == 'y':
                    print("y: comfirm recommend label")
                    old_key = next(key for key, etype in self.pressCommand.items() if etype == old_entity_type)
                    entity_content, cursor_index = self.replaceString(selected_string, selected_string, old_key,
                                                                      cursor_index)
                else:
                    if len(selected_string) > 0:
                        if command in self.pressCommand:
                            entity_content, cursor_index = self.replaceString(selected_string, selected_string, command,
                                                                              cursor_index)
                        else:
                            return
                line_before_entity += entity_content
            if aboveLine_content != '':
                aboveHalf_content = aboveLine_content + '\n' + line_before_entity
            else:
                aboveHalf_content = line_before_entity

            if belowLine_content != '':
                followHalf_content = line_after_entity + '\n' + belowLine_content
            else:
                followHalf_content = line_after_entity

            content = self.addRecommendContent(aboveHalf_content, followHalf_content, self.use_recommend.get())
            content = content
            self.writeFile(self.fileName, content, cursor_index)

    def executeEntryCommand(self, command):
        if self.debug:
            print("Action Track: executeEntryCommand")
        if len(command) == 0:
            currentCursor = self.text.index(INSERT)
            newCurrentCursor = str(int(currentCursor.split('.')[0]) + 1) + ".0"
            self.text.mark_set(INSERT, newCurrentCursor)
            self.setCursorLabel(newCurrentCursor)
        else:
            command_list = decompositCommand(command)
            for idx in range(0, len(command_list)):
                command = command_list[idx]
                if len(command) == 2:
                    select_num = int(command[0])
                    command = command[1]
                    content = self.text.get_text()
                    cursor_index = self.text.index(INSERT)
                    newcursor_index = cursor_index.split('.')[0] + "." + str(
                        int(cursor_index.split('.')[1]) + select_num)
                    # print "new cursor position: ", select_num, " with ", newcursor_index, "with ", newcursor_index
                    selected_string = self.text.get(cursor_index, newcursor_index)
                    aboveHalf_content = self.text.get('1.0', cursor_index)
                    followHalf_content = self.text.get(cursor_index, "end-1c")
                    if command in self.pressCommand:
                        if len(selected_string) > 0:
                            # print "insert index: ", self.text.index(INSERT) 
                            followHalf_content, newcursor_index = self.replaceString(followHalf_content,
                                                                                     selected_string, command,
                                                                                     newcursor_index)
                            content = self.addRecommendContent(aboveHalf_content, followHalf_content,
                                                               self.use_recommend.get())
                            # content = aboveHalf_content + followHalf_content
                    self.writeFile(self.fileName, content, newcursor_index)

    def replaceString(self, content, string, replaceType, cursor_index):
        if replaceType in self.pressCommand:
            new_string = "[@" + string + "#" + self.pressCommand[replaceType] + "*]"
            row, col = cursor_index.split('.')
            newcursor_index = f"{row}.{int(col) + len(self.pressCommand[replaceType]) + 5}"
        else:
            print("Invaild command!")
            print("cursor index: ", self.text.index(INSERT))
            return content, cursor_index
        content = content.replace(string, new_string, 1)
        return content, newcursor_index

    def writeFile(self, fileName, content, newcursor_index):
        if self.debug:
            print("Action track: writeFile")

        if len(fileName) > 0:
            if ".ann" in fileName:
                new_name = fileName
                ann_file = open(new_name, 'w', encoding=self.file_encoding)
                ann_file.write(content)
                ann_file.close()
            else:
                new_name = fileName + '.ann'
                ann_file = open(new_name, 'w', encoding=self.file_encoding)
                ann_file.write(content)
                ann_file.close()
            # print "Writed to new file: ", new_name
            self.autoLoadNewFile(new_name, newcursor_index)
            # self.generateSequenceFile()
        else:
            print("Don't write to empty file!")

    def addRecommendContent(self, train_data, decode_data, recommendMode):
        if not recommendMode:
            content = train_data + decode_data
        else:
            if self.debug:
                print("Action Track: addRecommendContent, start Recommend entity")
            content = maximum_matching(train_data, decode_data)
        return content

    def autoLoadNewFile(self, fileName, newcursor_index):
        if self.debug:
            print("Action Track: autoLoadNewFile")
        if len(fileName) > 0:
            self.text.delete("1.0", END)
            text = self.readFile(fileName)
            self.text.insert("end-1c", text)
            self.setNameLabel("File: " + fileName)
            self.text.mark_set(INSERT, newcursor_index)
            self.text.see(newcursor_index)
            self.setCursorLabel(newcursor_index)
            self.setColorDisplay()

    def setColorDisplay(self):
        countVar = StringVar()
        cursor_row, _ = self.text.index(INSERT).split('.')
        lineStart = cursor_row + '.0'
        lineEnd = cursor_row + '.end'

        if self.colorAllChunk:
            self.text.mark_set("matchStart", "1.0")
            self.text.mark_set("matchEnd", "1.0")
            self.text.mark_set("searchLimit", 'end-1c')
            self.text.mark_set("recommend_matchStart", "1.0")
            self.text.mark_set("recommend_matchEnd", "1.0")
            self.text.mark_set("recommend_searchLimit", 'end-1c')
        else:
            self.text.mark_set("matchStart", lineStart)
            self.text.mark_set("matchEnd", lineStart)
            self.text.mark_set("searchLimit", lineEnd)
            self.text.mark_set("recommend_matchStart", lineStart)
            self.text.mark_set("recommend_matchEnd", lineStart)
            self.text.mark_set("recommend_searchLimit", lineEnd)
        while True:
            pos = self.text.search(self.entity_regex, "matchEnd", "searchLimit", count=countVar, regexp=True)
            if pos == "":
                break
            self.text.mark_set("matchStart", pos)
            self.text.mark_set("matchEnd", f"{pos}+{countVar.get()}c")
            self.text.highlight_entity(pos, int(countVar.get()))
        ## color recommend type
        while True:
            recommend_pos = self.text.search(self.recommendRe, "recommend_matchEnd", "recommend_searchLimit",
                                             count=countVar, regexp=True)
            if recommend_pos == "":
                break
            self.text.mark_set("recommend_matchStart", recommend_pos)
            self.text.mark_set("recommend_matchEnd", f"{recommend_pos}+{countVar.get()}c")
            self.text.highlight_recommend(recommend_pos, int(countVar.get()))

        ## color the most inside span for nested span, scan from begin to end again
        if self.colorAllChunk:
            self.text.mark_set("matchStart", "1.0")
            self.text.mark_set("matchEnd", "1.0")
            self.text.mark_set("searchLimit", 'end-1c')
        else:
            self.text.mark_set("matchStart", lineStart)
            self.text.mark_set("matchEnd", lineStart)
            self.text.mark_set("searchLimit", lineEnd)
        while True:
            self.text.tag_configure("insideEntityColor", background=self.insideNestEntityColor)
            pos = self.text.search(self.insideNestEntityRe, "matchEnd", "searchLimit", count=countVar, regexp=True)
            if pos == "":
                break
            self.text.mark_set("matchStart", pos)
            self.text.mark_set("matchEnd", "%s+%sc" % (pos, countVar.get()))
            ledge_low = f"{pos} + 2c"
            redge_high = f"{pos} + {int(countVar.get()) - 1}c"
            self.text.tag_add("insideEntityColor", ledge_low, redge_high)

    def pushToHistory(self):
        self.history.append((self.text.get_text(), self.text.index(INSERT)))

    ## update shortcut map
    def renewPressCommand(self):
        if self.debug:
            print("Action Track: renewPressCommand")
        seq = 0
        new_dict = {}
        listLength = len(self.labelEntryList)
        delete_num = 0
        for key in sorted(self.pressCommand):
            label = self.labelEntryList[seq].get()
            if len(label) > 0:
                new_dict[key] = label
            else:
                delete_num += 1
            seq += 1
        self.pressCommand = new_dict
        for idx in range(1, delete_num + 1):
            self.labelEntryList[listLength - idx].delete(0, END)
            self.shortcutLabelList[listLength - idx].config(text="NON= ")
        with open(self.configFile, 'w') as fp:
            fp.write(str(self.pressCommand))
        self.show_binding_widgets()
        messagebox.showinfo("Remap Notification",
                            "Shortcut map has been updated!\n\n" +
                            "Configure file has been saved in File:" + self.configFile)

    ## save as new shortcut map
    def savenewPressCommand(self):
        if self.debug:
            print("Action Track: savenewPressCommand")
        seq = 0
        new_dict = {}
        listLength = len(self.labelEntryList)
        delete_num = 0
        for key in sorted(self.pressCommand):
            label = self.labelEntryList[seq].get()
            if len(label) > 0:
                new_dict[key] = label
            else:
                delete_num += 1
            seq += 1
        self.pressCommand = new_dict
        for idx in range(1, delete_num + 1):
            self.labelEntryList[listLength - idx].delete(0, END)
            self.shortcutLabelList[listLength - idx].config(text="NON= ")
        # prompt to ask configFile name
        self.configFile = filedialog.asksaveasfilename(
            initialdir="./configs/",
            title="Save New Config",
            filetypes=(("YEDDA configs", "*.config"), ("all files", "*.*")))
        # change to relative path following self.init()
        self.configFile = os.path.relpath(self.configFile)
        # make sure ending with ".config"
        if not self.configFile.endswith(".config"):
            self.configFile += ".config"
        with open(self.configFile, 'w') as fp:
            fp.write(str(self.pressCommand))
        self.show_binding_widgets()
        messagebox.showinfo("Save New Map Notification",
                            "Shortcut map has been saved and updated!\n\n"
                            + "Configure file has been saved in File:" + self.configFile)

    ## show shortcut map
    def show_binding_widgets(self):
        if os.path.isfile(self.configFile):
            with open(self.configFile, 'r') as fp:
                self.pressCommand = eval(fp.read())

        mapLabel = Label(self, text="Shortcuts map Labels", foreground="blue", font=(self.textFontStyle, 14, "bold"))
        mapLabel.grid(row=0, column=self.textColumn + 2, columnspan=2, sticky=W)

        # destroy all previous widgets before switching shortcut maps
        if self.labelEntryList is not None and isinstance(self.labelEntryList, list):
            for x in self.labelEntryList:
                x.destroy()
        if self.shortcutLabelList is not None and isinstance(self.shortcutLabelList, list):
            for x in self.shortcutLabelList:
                x.destroy()
        self.labelEntryList = []
        self.shortcutLabelList = []

        row = 0
        for key in sorted(self.pressCommand):
            row += 1
            symbolLabel = Label(self, text=key.upper() + ": ", font=(self.textFontStyle, 14, "bold"), width=4)
            symbolLabel.grid(row=row, column=self.textColumn + 2)
            self.shortcutLabelList.append(symbolLabel)

            labelEntry = Entry(self, font=(self.textFontStyle, 14))
            labelEntry.insert(0, self.pressCommand[key])
            labelEntry.grid(row=row, column=self.textColumn + 3, columnspan=1, rowspan=1)
            self.labelEntryList.append(labelEntry)

        if self.configListLabel is not None:
            self.configListLabel.destroy()
        if self.configListBox is not None:
            self.configListBox.destroy()
        self.configListLabel = Label(self, text="Map Templates", foreground="blue",
                                     font=(self.textFontStyle, 14, "bold"))
        self.configListLabel.grid(row=row + 1, column=self.textColumn + 2, columnspan=2, rowspan=1, padx=10)
        self.configListBox = Combobox(self, values=getConfigList(), state='readonly')
        self.configListBox.grid(row=row + 2, column=self.textColumn + 2, columnspan=2, rowspan=1, padx=6)
        # select current config file
        self.configListBox.set(self.configFile.split(os.sep)[-1])
        self.configListBox.bind('<<ComboboxSelected>>', self.on_select_configfile)

    def on_select_configfile(self, event=None):
        if event and self.debug:
            print("Change shortcut map to: ", event.widget.get())
        self.configFile = os.path.join("configs", event.widget.get())
        self.show_binding_widgets()

    def getCursorIndex(self):
        return self.text.index(INSERT)

    def generateSequenceFile(self):
        if (".ann" not in self.fileName) and (".txt" not in self.fileName):
            out_error = "Export only works on filename ended in .ann or .txt!\nPlease rename file."
            print(out_error)
            messagebox.showerror("Export error!", out_error)

            return -1
        fileLines = open(self.fileName, 'r').readlines()
        lineNum = len(fileLines)
        new_filename = self.fileName.split('.ann')[0] + '.anns'
        seqFile = open(new_filename, 'w')
        for line in fileLines:
            if len(line) <= 2:
                seqFile.write('\n')
                continue
            else:
                if not self.keepRecommend:
                    line = removeRecommendContent(line, self.recommendRe)
                wordTagPairs = getWordTagPairs(line, self.segmented, self.tagScheme, self.onlyNP, self.goldAndrecomRe)
                for wordTag in wordTagPairs:
                    seqFile.write(wordTag)
                ## use null line to seperate sentences
                seqFile.write('\n')
        seqFile.close()
        print("Exported file into sequence style in file: ", new_filename)
        print("Line number:", lineNum)
        showMessage = "Exported file successfully!\n\n"
        showMessage += "Tag scheme: " + self.tagScheme + "\n\n"
        showMessage += "Keep Recom: " + str(self.keepRecommend) + "\n\n"
        showMessage += "Text Seged: " + str(self.segmented) + "\n\n"
        showMessage += "Line Number: " + str(lineNum) + "\n\n"
        showMessage += "Saved to File: " + new_filename
        messagebox.showinfo("Export Message", showMessage)


def getConfigList():
    fileNames = os.listdir("./configs")
    filteredFileNames = sorted(filter(lambda x: (not x.startswith(".")) and (x.endswith(".config")), fileNames))
    return list(filteredFileNames)


def getWordTagPairs(tagedSentence, seged=True, tagScheme="BMES", onlyNP=False, entityRe=r'\[\@.*?\#.*?\*\]'):
    newSent = tagedSentence.strip('\n')
    filterList = re.findall(entityRe, newSent)
    newSentLength = len(newSent)
    chunk_list = []
    start_pos = 0
    end_pos = 0
    if len(filterList) == 0:
        singleChunkList = []
        singleChunkList.append(newSent)
        singleChunkList.append(0)
        singleChunkList.append(len(newSent))
        singleChunkList.append(False)
        chunk_list.append(singleChunkList)
        # print singleChunkList
        singleChunkList = []
    else:
        for pattern in filterList:
            # print pattern
            singleChunkList = []
            start_pos = end_pos + newSent[end_pos:].find(pattern)
            end_pos = start_pos + len(pattern)
            singleChunkList.append(pattern)
            singleChunkList.append(start_pos)
            singleChunkList.append(end_pos)
            singleChunkList.append(True)
            chunk_list.append(singleChunkList)
            singleChunkList = []
    ## chunk_list format:
    full_list = []
    for idx in range(0, len(chunk_list)):
        if idx == 0:
            if chunk_list[idx][1] > 0:
                full_list.append([newSent[0:chunk_list[idx][1]], 0, chunk_list[idx][1], False])
                full_list.append(chunk_list[idx])
            else:
                full_list.append(chunk_list[idx])
        else:
            if chunk_list[idx][1] == chunk_list[idx - 1][2]:
                full_list.append(chunk_list[idx])
            elif chunk_list[idx][1] < chunk_list[idx - 1][2]:
                print("ERROR: found pattern has overlap!", chunk_list[idx][1], ' with ', chunk_list[idx - 1][2])
            else:
                full_list.append(
                    [newSent[chunk_list[idx - 1][2]:chunk_list[idx][1]], chunk_list[idx - 1][2], chunk_list[idx][1],
                     False])
                full_list.append(chunk_list[idx])

        if idx == len(chunk_list) - 1:
            if chunk_list[idx][2] > newSentLength:
                print("ERROR: found pattern position larger than sentence length!")
            elif chunk_list[idx][2] < newSentLength:
                full_list.append([newSent[chunk_list[idx][2]:newSentLength], chunk_list[idx][2], newSentLength, False])
            else:
                continue
    return turnFullListToOutputPair(full_list, seged, tagScheme, onlyNP)


def turnFullListToOutputPair(fullList, segmented=True, tagScheme="BMES", onlyNP=False):
    pairList = []
    for eachList in fullList:
        if eachList[3]:
            contLabelList = eachList[0].strip('[@$]').rsplit('#', 1)
            if len(contLabelList) != 2:
                print("Error: sentence format error!")
            label = contLabelList[1].strip('*')
            if segmented:
                contLabelList[0] = contLabelList[0].split()
            if onlyNP:
                label = "NP"
            outList = outputWithTagScheme(contLabelList[0], label, tagScheme)
            for eachItem in outList:
                pairList.append(eachItem)
        else:
            if segmented:
                eachList[0] = eachList[0].split()
            for idx in range(0, len(eachList[0])):
                basicContent = eachList[0][idx]
                if basicContent == ' ':
                    continue
                pair = basicContent + ' ' + 'O\n'
                pairList.append(pair)
    return pairList


def outputWithTagScheme(input_list, label, tagScheme="BMES"):
    output_list = []
    list_length = len(input_list)
    if tagScheme == "BMES":
        if list_length == 1:
            pair = input_list[0] + ' ' + 'S-' + label + '\n'
            output_list.append(pair)
        else:
            for idx in range(list_length):
                if idx == 0:
                    pair = input_list[idx] + ' ' + 'B-' + label + '\n'
                elif idx == list_length - 1:
                    pair = input_list[idx] + ' ' + 'E-' + label + '\n'
                else:
                    pair = input_list[idx] + ' ' + 'M-' + label + '\n'
                output_list.append(pair)
    else:
        for idx in range(list_length):
            if idx == 0:
                pair = input_list[idx] + ' ' + 'B-' + label + '\n'
            else:
                pair = input_list[idx] + ' ' + 'I-' + label + '\n'
            output_list.append(pair)
    return output_list


def removeRecommendContent(content, recommendRe=r'\[\$.*?\#.*?\*\](?!\#)'):
    output_content = ""
    last_match_end = 0
    for match in re.finditer(recommendRe, content):
        matched = content[match.span()[0]:match.span()[1]]
        words = matched.strip('[$]').split("#")[0]
        output_content += content[last_match_end:match.span()[0]] + words
        last_match_end = match.span()[1]
    output_content += content[last_match_end:]
    return output_content


def decompositCommand(command_string):
    command_list = []
    each_command = []
    num_select = ''
    for idx in range(0, len(command_string)):
        if command_string[idx].isdigit():
            num_select += command_string[idx]
        else:
            each_command.append(num_select)
            each_command.append(command_string[idx])
            command_list.append(each_command)
            each_command = []
            num_select = ''
    return command_list


def main():
    print("SUTDAnnotator launched!")
    print("OS:", platform.system())
    root = Tk()
    root.geometry("1300x700+200+200")
    app = Application(root)
    app.setFont(17)
    root.mainloop()


if __name__ == '__main__':
    main()
