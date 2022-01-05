import configparser
import os
import subprocess
import sys
from os.path import isfile, join
from os import listdir
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from MainWindow import Ui_MainWindow
from ConfigWindow import Ui_Form
from win32comext.shell import shell, shellcon

inipath = os.path.join(os.getcwd(), "config.ini")
from toollog import logger

qmut_1 = QMutex()

"""
高亮
"""
class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HighlightDelegate, self).__init__(parent)
        self._filters = []
        self._wordwrap = False
        self.doc = QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        self.doc.setPlainText(options.text)
        self.apply_highlight()

        if self._wordwrap:
            self.doc.setTextWidth(options.rect.width())
        options.text = ""

        style = QApplication.style() if options.widget is None else options.widget.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, options, painter)

        if self._wordwrap:
            painter.translate(options.rect.left(), options.rect.top())
            clip = QRectF(QPointF(), QSizeF(options.rect.size()))
            self.doc.drawContents(painter, clip)
        else:
            ctx = QAbstractTextDocumentLayout.PaintContext()
            if option.state & QtWidgets.QStyle.State_Selected:
                ctx.palette.setColor(QPalette.Text, option.palette.color(
                    QPalette.Active, QPalette.HighlightedText))
            else:
                ctx.palette.setColor(QPalette.Text, option.palette.color(
                    QPalette.Active, QPalette.Text))
            textRect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, options, None)
            if index.column() != 0:
                textRect.adjust(5, 0, 0, 0)
            constant = 4
            margin = (option.rect.height() - options.fontMetrics.height()) // 2
            margin = margin - constant
            textRect.setTop(textRect.top() + margin)
            painter.translate(textRect.topLeft())
            painter.setClipRect(textRect.translated(-textRect.topLeft()))
            self.doc.documentLayout().draw(painter, ctx)

        painter.restore()
        s = QSize(int(self.doc.idealWidth()), int(self.doc.size().height()))
        index.model().setData(index, s, Qt.SizeHintRole)

    def apply_highlight(self):
        cursor = QTextCursor(self.doc)
        cursor.beginEditBlock()
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.red)
        for f in self.filters():
            highlightCursor = QTextCursor(self.doc)
            while not highlightCursor.isNull() and not highlightCursor.atEnd():
                highlightCursor = self.doc.find(f, highlightCursor)
                if not highlightCursor.isNull():
                    highlightCursor.mergeCharFormat(fmt)
        cursor.endEditBlock()

    @pyqtSlot(list)
    def setFilters(self, filters):
        if self._filters == filters: return
        self._filters = filters
        self.parent().viewport().update()

    def filters(self):
        return self._filters

    def setWordWrap(self, on):
        self._wordwrap = on
        mode = QTextOption.WrapAnywhere if on else QTextOption.WrapAtWordBoundaryOrAnywhere
        textOption = QTextOption(self.doc.defaultTextOption())
        textOption.setWrapMode(mode)
        self.doc.setDefaultTextOption(textOption)
        self.parent().viewport().update()

class MkvMixMain(QMainWindow,Ui_MainWindow):
    def __init__(self):
        super(MkvMixMain, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("MkvMix")
        self.setProp()

    def setProp(self):
        # 以下代码将下拉框空间文本居中设置
        self.filepathrexBox.lineEdit().setAlignment(Qt.AlignCenter)
        self.subpathrexBox.lineEdit().setAlignment(Qt.AlignCenter)
        self.audiopathrexBox.lineEdit().setAlignment(Qt.AlignCenter)
        self.seasonBox.lineEdit().setAlignment(Qt.AlignCenter)
        self.audioorderBox.lineEdit().setAlignment(Qt.AlignCenter)

        config = configparser.ConfigParser()
        config.read(inipath, encoding="utf-8")
        self.keywordlist = config["mkvmix"]["keyword"].split(',')
        self.mkvpath = '"' + config["mkvmix"]["mkvpath"] + '"'
        filepathrex = config["mkvmix"]["filepathrex"].split(',')
        subpathrex = config["mkvmix"]["subpathrex"].split(',')
        audiopathrex = config["mkvmix"]["audiopathrex"].split(',')

        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.startButton.setEnabled(False)
        self.confirmButton.setEnabled(False)
        self.deleButton.setEnabled(False)
        self.tableWidget_2.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget_2.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget_2.verticalHeader().setVisible(False)
        self.tableWidget_2.insertRow(0)
        self.tableWidget_2.setColumnWidth(0, 50)
        self.tableWidget_2.setColumnWidth(3, 60)
        self.tableWidget_2.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        item_6 = QTableWidgetItem('其他')
        item_6.setTextAlignment(Qt.AlignCenter)
        item_6.setFlags(Qt.ItemIsEnabled)
        item_7 = QTableWidgetItem('[$]')
        item_7.setTextAlignment(Qt.AlignCenter)
        self.tableWidget_2.setItem(0, 0, item_6)
        self.tableWidget_2.setItem(0, 3, item_7)
        self.tableWidget_2.cellClicked.connect(self.changeDelButton)    # 改变删除行
        self.insertButton.clicked.connect(self.instert)                 # 插入
        self.deleButton.clicked.connect(self.tableDelete)
        self.checkButton.clicked.connect(self.check)
        self.startButton.clicked.connect(self.run)
        self.confirmButton.clicked.connect(self.confirmChange)
        self.renameEpisodeCheckBox.clicked.connect(self.showLine)
        self.delCheckBox.clicked.connect(self.changeRenameButton)
        self.deleButton_2.clicked.connect(self.tableDelete1)
        self.initepisodeEdit.setText('0')
        self.filepathrexBox.addItems(filepathrex)
        self.subpathrexBox.addItems(subpathrex)
        self.audiopathrexBox.addItems(audiopathrex)
        font = QFont("宋体")
        # font.setPointSize(9)
        pointsize = font.pointSize()
        font.setPixelSize(int(pointsize * 78 / 67))
        self.centralwidget.setFont(font)
        QFontDialog(font, self.centralwidget)

    """
    显示提示，取消删除和重命名CheckBox
    """
    def showLine(self):
        if self.renameEpisodeCheckBox.isChecked():
            self.delCheckBox.setChecked(False)
            self.CMDBrowser.append("请在字幕路径中输入剧名...")

    """
    取消重命名CheckBox
    """
    def changeRenameButton(self):
        if self.delCheckBox.isChecked():
            self.renameEpisodeCheckBox.setChecked(False)

    """
    other command选中第一行时不允许使用删除按钮
    """
    def changeDelButton(self, row):
        if row == 0:
            self.deleButton.setEnabled(False)
        else:
            self.deleButton.setEnabled(True)

    """
    other command插入行
    """
    def instert(self):
        row = self.tableWidget_2.rowCount()
        self.tableWidget_2.insertRow(row)
        item = QTableWidgetItem('其他')
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsEnabled)
        item_1 = QTableWidgetItem('[$]')
        item_1.setTextAlignment(Qt.AlignCenter)
        item_2 = QTableWidgetItem(' ')
        self.tableWidget_2.setItem(row, 0, item)
        self.tableWidget_2.setItem(row, 3, item_1)
        self.tableWidget_2.setItem(row, 1, item_2)

    def otherComd(self, reslist):
        self.errflag = False
        otherlist = []
        self.row = self.tableWidget_2.rowCount()

        otherdict = {'filepath': '',
                     'filepathrex': '',
                     'command': '',
                     }
        for i in range(self.row):
            for j in range(1, 4):
                if self.tableWidget_2.item(i, j) is None:
                    self.errflag = True
                    break
        if not self.errflag:
            for i in range(self.row):
                for j in range(1, 3):
                    if self.tableWidget_2.item(i, j).text() == '':
                        self.errflag = True
        if not self.errflag:
            for i in range(self.row):
                otherdict.update({'filepath': self.tableWidget_2.item(i, 1).text(),
                                  'filepathrex': self.tableWidget_2.item(i, 3).text(),
                                  'command': self.tableWidget_2.item(i, 2).text()})
                otherlist.append(otherdict.copy())
                self.otherfilepath = otherdict['filepath']
                self.otherfilerex = otherdict['filepathrex']
                self.othercommand = otherdict['command']
                logger.info('otherComd: "otherfilepath":{}'.format(self.otherfilepath))
                if not os.path.isdir(self.otherfilepath):
                    self.errflag = True
            logger.info('otherComd: "otherlist":{}'.format(otherlist))
        if not self.errflag:
            for i, otherdict in enumerate(otherlist):
                otherfilelist = self.filter(self.path2list(otherdict['filepath'], '.mkv'), self.keywordlist)
                reslist = self.gettogether(reslist, otherfilelist, 'otherfile' + str(i), otherdict['filepath'], self.filerex,
                                           self.otherfilerex, self.filetype)
            for filedict in reslist:
                for i, otherdict in enumerate(otherlist):
                    filedict.update({'othercommand' + str(i): otherdict['command']})

            logger.info('otherComd: "reslist":{}'.format(reslist))
            return reslist
        else:
            self.CMDBrowser.append("请输入其他表格中空白")
            self.errflag = True

    def subComd(self, reslist):
        self.errflag = False
        logger.info('subComd: "filelist":{}'.format(reslist))
        self.subpath = self.subpathEdit.text()
        if os.path.isdir(self.subpath):
            self.subpathrex = self.subpathrexBox.currentText()
            self.subfiletype = self.subfiletypeBox.currentText()
            sublist = self.filter(self.path2list(self.subpath, self.subfiletype), self.keywordlist)
            if len(sublist) == 0:
                self.CMDBrowser.append("未找到{}格式文件".format(self.subfiletype))
            else:
                reslist = self.gettogether(reslist, sublist, 'subname', self.subpath, self.filerex,
                                           self.subpathrex, self.filetype)
                logger.info('subComd: "reslist":{}'.format(reslist))
            if len(reslist) != 0 and not self.errflag:
                for filedict in reslist:
                    filedict.update({'subcommand': "--language 0:zh --default-track 0:yes"})
                logger.info('subComd: "reslist":{}'.format(reslist))
                return reslist
        else:
            self.CMDBrowser.append("输入字幕文件路径为空或非文件夹")
            self.errflag = True

    def audioComd(self, reslist):
        self.errflag = False
        self.audiopath = self.audiopathEdit.text()
        self.audiorex = self.audiopathrexBox.currentText()
        self.audioorder = self.audioorderBox.currentText()
        self.audiofiletype = self.audiofiletypeBox.currentText()
        if os.path.isdir(self.audiopath):
            logger.info('audioComd: "filelist":{}'.format(reslist))
            audiolist = self.filter(self.path2list(self.audiopath, '.'+self.audiofiletype), self.keywordlist)
            logger.info('audioComd: "audiolist":{}'.format(audiolist))
            if len(audiolist) == 0:
                self.errflag = True
                self.CMDBrowser.append("未找到{}格式音轨".format(self.audiofiletype))
            else:
                reslist = self.gettogether(reslist, audiolist, 'audioname', self.audiopath,
                                           self.filerex, self.audiorex, self.filetype)
            if len(reslist) != 0 and not self.errflag:
                for filedict in reslist:
                    filedict.update({"audiocommand": "--audio-tracks {} --no-video --no-subtitles --no-chapters --language 1:en".format(str(self.audioorder))})
                logger.info('audioComd: "reslist":{}'.format(reslist))
                return reslist
        else:
            self.CMDBrowser.append("输入音轨文件路径为空或非文件夹")
            self.errflag = True

    def fileFilter(self):
        self.filepath = self.filepathEdit.text()
        self.filerex = self.filepathrexBox.currentText()
        self.filetype = self.filetypeBox.currentText()
        if os.path.isdir(self.filepath):
            filelist = self.filter(self.path2list(self.filepath, '.' + self.filetype), self.keywordlist)
            if len(filelist) == 0:
                self.errflag = True
                self.CMDBrowser.append("未找到{}格式视频".format(self.filetype))
            else:
                reslist = self.gettogether_2(filelist, self.filerex)
                logger.info('fileFilter: "reslist":{}'.format(reslist))
                if len(reslist) == 0:
                    print(1111)
                    self.errflag = True
                    self.CMDBrowser.append("未发现视频源，请检查匹配格式是否正确...")
                    return []
                else:
                    # logger.info('fileFilter: "reslist":{}'.format(reslist))
                    return reslist

        else:
            self.CMDBrowser.append("输入源文件路径为空或非文件夹")
            return []

    def commandCombin(self):
        self.CMDBrowser.clear()
        self.errflag = False
        self.delmode = -1
        command = [self.mkvpath, "--ui-language zh_CN", "--output"]
        commandalllist = []
        if self.subCheckBox.isChecked() and self.audioCheckBox.isChecked() and self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.subComd(reslist)
                if not self.errflag:
                    reslist = self.audioComd(reslist)
                    if not self.errflag:
                        reslist = self.otherComd(reslist)
                        if not self.errflag:
                            for filedict in reslist:
                                othercommand = []
                                otherstr = ''
                                for i in range(self.row):
                                    othercommand = othercommand + [filedict['othercommand' + str(i)],
                                                                   filedict['otherfile' + str(i) + 'path']]
                                    otherstr = otherstr + '-->' + "other:" + filedict['otherfile' + str(i)]
                                commandlist = command + [filedict['outputpathname'], filedict['filepathname'],
                                                         filedict['subcommand'] +
                                                         filedict['subnamepath'], filedict['audiocommand'],
                                                         filedict['audionamepath']] + \
                                              othercommand
                                commandalllist.append(commandlist)
                                # self.CMDBrowser.append(
                                #     "source:{}--> sub:{}-->audio:{}{}".format(filedict['filename'],
                                #                                               filedict['subname'],
                                #                                               filedict['audioname'], otherstr))
                            logger.info('commandCombin: sub&audio&other: "commandstrlist":{}'.format(commandalllist))
                            return commandalllist

        elif self.subCheckBox.isChecked() and self.audioCheckBox.isChecked() and not self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.subComd(reslist)
                if not self.errflag:
                    reslist = self.audioComd(reslist)
                    if not self.errflag:
                        for filedict in reslist:
                            commandlist = command + [filedict['outputpathname'],
                                                     filedict['filepathname'], filedict['subcommand'],
                                                     filedict['subnamepath'], filedict['audiocommand'],
                                                     filedict['audionamepath']]
                            # self.CMDBrowser.append(
                            #     "source:{}--> sub:{}-->audio:{}".format(filedict['filename'],
                            #                                             filedict['subname'],
                            #                                             filedict['audioname']))
                            commandalllist.append(commandlist)
                        logger.info('commandCombin: sub&audio: "commandstrlist":{}'.format(commandalllist))
                        return commandalllist

        elif self.subCheckBox.isChecked() and not self.audioCheckBox.isChecked() and not self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.subComd(reslist)
                if not self.errflag:
                    for filedict in reslist:
                        commandlist = command + [filedict['outputpathname'],
                                                 filedict['filepathname'], filedict['subcommand'],
                                                 filedict['subnamepath']]
                        # self.CMDBrowser.append(
                        #     "source:{}--> sub:{}".format(filedict['filename'], filedict['subname'], ))
                        commandalllist.append(commandlist)
                    logger.info('commandCombin: sub: "commandstrlist":{}'.format(commandalllist))
                    return commandalllist

        elif self.subCheckBox.isChecked() and not self.audioCheckBox.isChecked() and self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.subComd(reslist)
                if not self.errflag:
                    reslist = self.otherComd(reslist)
                    if not self.errflag:
                        self.CMDBrowser.clear()
                        for filedict in reslist:
                            othercommand = []
                            otherstr = ''
                            for i in range(self.row):
                                othercommand = othercommand + [filedict['othercommand' + str(i)],
                                                               filedict['otherfile' + str(i) + 'path']]
                                otherstr = otherstr + '-->' + "other:" + filedict['otherfile' + str(i)]
                            commandlist = command + [filedict['outputpathname'], filedict['filepathname'],
                                                     filedict['subcommand'] +
                                                     filedict['subnamepath']] + othercommand
                            commandalllist.append(commandlist)
                            # self.CMDBrowser.append(
                            #     "source:{}--> sub:{}{}".format(filedict['filename'],
                            #                                    filedict['subname'], otherstr))
                        logger.info('commandCombin: sub&other: "commandstrlist":{}'.format(commandalllist))
                        return commandalllist

        elif not self.subCheckBox.isChecked() and self.audioCheckBox.isChecked() and self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.audioComd(reslist)
                if not self.errflag:
                    reslist = self.otherComd(reslist)
                    if not self.errflag:
                        for filedict in reslist:
                            othercommand = []
                            otherstr = ''
                            for i in range(self.row):
                                othercommand = othercommand + [filedict['othercommand' + str(i)],
                                                               filedict['otherfile' + str(i) + 'path']]
                                otherstr = otherstr + '-->' + "other:" + filedict['otherfile' + str(i)]
                            commandlist = command + [filedict['outputpathname'], filedict['filepathname'],
                                                     filedict['audiocommand'],
                                                     filedict['audionamepath']] + othercommand
                            commandalllist.append(commandlist)
                            # self.CMDBrowser.append(
                            #     "source:{}-->audio:{}{}".format(filedict['filename'],
                            #                                     filedict['audioname'], otherstr))
                        logger.info('commandCombin: audio&other: "commandstrlist":{}'.format(commandalllist))
                        return commandalllist

        elif not self.subCheckBox.isChecked() and not self.audioCheckBox.isChecked() and self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.otherComd(reslist)
                if not self.errflag:
                    for filedict in reslist:
                        othercommand = []
                        otherstr = ''
                        for i in range(self.row):
                            othercommand = othercommand + [filedict['othercommand' + str(i)],
                                                           filedict['otherfile' + str(i) + 'path']]
                            otherstr = otherstr + '-->' + "other:" + filedict['otherfile' + str(i)]
                        commandlist = command + othercommand
                        commandalllist.append(commandlist)
                        self.CMDBrowser.append("source:{}{}".format(filedict['filename'], otherstr))
                    logger.info('commandCombin: other: "commandstrlist":{}'.format(commandalllist))
                    return commandalllist

        elif not self.subCheckBox.isChecked() and self.audioCheckBox.isChecked() and not self.otherCheckBox.isChecked():
            reslist = self.fileFilter()
            if not self.errflag:
                reslist = self.audioComd(reslist)
                if not self.errflag:
                    for filedict in reslist:
                        commandlist = command + [filedict['outputpathname'], filedict['filepathname'],
                                                 filedict['audiocommand'], filedict['audionamepath']]
                        commandalllist.append(commandlist)
                        # self.CMDBrowser.append(
                        #     "source:{}--> audio:{}".format(filedict['filename'], filedict['audioname']))
                    logger.info('commandCombin: audio: "commandstrlist":{}'.format(commandalllist))
                    return commandalllist
        else:
            if self.delCheckBox.isChecked():
                self.onlydel = True
            else:
                self.errflag = True
            return []

    def showCommand(self, commandstrlist):
        logger.info('showCommand: commandstrlist:{}'.format(commandstrlist))
        self.tableWidget.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self._delegate = HighlightDelegate(self.tableWidget)
        self.tableWidget.setItemDelegate(self._delegate)
        tablerow = len(commandstrlist)
        tablecol = len(commandstrlist[0])
        self.tableWidget.setColumnCount(tablecol)
        self.tableWidget.setRowCount(tablerow)
        QMetaObject.connectSlotsByName(self.searchEdit)
        for i, commandstr in enumerate(commandstrlist[0]):
            if len(commandstr) <= 40:
                self.tableWidget.setColumnWidth(i, int(1/len(commandstr)*100)+len(commandstr)*6)
            else:
                self.tableWidget.setColumnWidth(i, 350)
        self._delegate = HighlightDelegate(self.tableWidget)
        self.tableWidget.setItemDelegate(self._delegate)
        self.searchEdit.textChanged.connect(self.on_textChanged)
        words_in_columns = []
        for num in range(self.initepisode, self.initepisode + tablerow+2):
            number = str(num).rjust(2, '0')
            number1 = self.filerex.replace('$', number)
            words_in_columns.append(number1)
            if self.subCheckBox.isChecked():
                number2 = self.subpathrex.replace('$', number)
                words_in_columns.append(number2)
            if self.audioCheckBox.isChecked():
                number3 = self.audiorex.replace('$', number)
                words_in_columns.append(number3)
        words_in_columns = list(set(words_in_columns))
        words_in_columns.sort()
        search_list = [word for word in words_in_columns]
        list_c_str = ' '.join(search_list)
        self.searchEdit.setText(list_c_str)
        for row, commandstr in enumerate(commandstrlist):
            for col, command in enumerate(commandstr):
                self.tableWidget.setItem(row, col, QTableWidgetItem(command))
        self._delegate.setWordWrap(True)
        self._delegate.setFilters(search_list)

    def showEpisodeInfo(self):
        self.errflag = False
        self.filepath = self.filepathEdit.text()
        self.filerex = self.filepathrexBox.currentText()
        self.season = self.seasonBox.currentText()
        logger.info('showEpisodeInfo: season: {}'.format(self.season))
        self.episodename = self.subpathEdit.text()
        reslist = self.fileFilter()
        if not self.errflag:
            eposodlen = len(reslist)
            episodelist = []
            episodealllist = []
            rex = self.filepathrexBox.currentText()
            for num in range(self.initepisode, self.initepisode + eposodlen + 1):
                number = str(num).rjust(2, '0')
                number_1 = rex.replace('$', number)
                for filedict in reslist:
                    if number_1 in filedict['filename'].upper():
                        filedict.update({'episode': number,
                                        'season': self.season})
                        break
            logger.info('showEpisodeInfo: reslist: {}'.format(reslist))
            rstlist = [item for item in reslist if 'season' in item]
            logger.info('showCommand: showEpisodeInfo:{}'.format(rstlist))

            for resdict in rstlist:
                episodelist.append([self.episodename, resdict['filepathname'], str(resdict['season']), str(resdict['episode'])])
            logger.info('showEpisodeInfo: episodelist:{}'.format(episodelist))
            for i in episodelist:
                showstr = i[0] + ' - ' + 'S' + i[2] + 'E' + i[3]+' - ' + i[1]
                self.CMDBrowser.append(showstr)

            return episodelist

    def on_textChanged(self, text):
        self._delegate.setFilters(list(set(text.split())))

    def confirmChange(self):
        self.CMDBrowser.clear()
        commandstrlist = []
        col = self.tableWidget.columnCount()
        row = self.tableWidget.rowCount()
        self.errflag = False
        for i in range(row):
            for j in range(col):
                if self.tableWidget.item(i, j) is None:
                    self.CMDBrowser.append("表格为空，请确认表格")
                    self.errflag = True
                    break
        if not self.errflag:
            for i in range(row):
                for j in range(col):
                    if self.tableWidget.item(i, j).text() == '':
                        self.CMDBrowser.append("表格为空，请确认表格")
                        self.errflag = True
        if not self.errflag:
            for i in range(row):
                commandlist = []
                for j in range(col):
                    commandlist.append(self.tableWidget.item(i, j).text())
                commandstrlist.append(commandlist)
            self.CMDBrowser.append("确认修改成功!")
            if self.renameEpisodeCheckBox.isChecked():
                for i in commandstrlist:
                    showstr = i[0] + ' - ' + 'S' + i[2] + 'E' + i[3]+' - ' + i[1]
                    self.CMDBrowser.append(showstr)

            else:
                showstralllist = []
                for i in commandstrlist:
                    showstrlist = []
                    for j in i:
                        if '.mkv' in j or '.ass' in j:
                            j1 = j.split('\\')[-1]
                            showstrlist.append(j1)
                    showstralllist.append(showstrlist)
                for i in showstralllist:
                    str = ''
                    for j in i:
                        j = " --> " + j
                        str = str + j
                    self.CMDBrowser.append(str)
            self.confirmflag = True
            self.commandstrlist = commandstrlist
        else:
            self.errflag = False
            # self.commandstrlist = []
    """
    :删除other行
    """
    def tableDelete(self):
        r = self.tableWidget_2.selectionModel().selectedRows()
        if r:  # 下面删除时，选中多行中的最后一行，会被删掉；不选中，则默认第一行删掉
            index = self.tableWidget_2.currentIndex()
            self.tableWidget_2.removeRow(index.row())

    def tableDelete1(self):
        r = self.tableWidget.selectionModel().selectedRows()
        if r:  # 下面删除时，选中多行中的最后一行，会被删掉；不选中，则默认第一行删掉
            index = self.tableWidget.currentIndex()
            self.tableWidget.removeRow(index.row())
            row = self.tableWidget.rowCount()
            if row == 0:
                self.confirmButton.setEnabled(False)
            else:
                self.confirmButton.setEnabled(True)

    def commandSplicing(self, cmdlist):
        str1 = ''
        for i in cmdlist:
            str1 = str1 + ' ' + i
            str1 = str1.strip()
        return str1

    def renameSub(self):
        self.errflag = False
        reslist = self.fileFilter()
        remansublist = []
        if not self.errflag:
            reslist = self.subComd(reslist)
            for filedict in reslist:
                filename = filedict['filename']
                subrename = filename.replace(self.filetype, self.subfiletype)
                subpath = os.path.dirname(filedict['subnamepath'].strip('"'))
                subrenamepath = os.path.join(subpath, subrename)
                remansublist.append([filedict['subnamepath'].strip('"'), subrenamepath])
                logger.info('renameSub: remansublist:{}'.format(remansublist))
            self.showCommand(remansublist)
            return remansublist

    def check(self):
        self.initepisode = int(self.initepisodeEdit.text())
        self.subfiletype = self.subfiletypeBox.currentText()
        self.onlydel = False
        self.startButton.setEnabled(False)
        self.tableWidget.clear()
        # try:
        self.confirmflag = False
        self.CMDBrowser.append("开始检查...")
        if self.renameEpisodeCheckBox.isChecked():
            if self.subpathEdit.text() != '':
                logger.info('check: renamemode')
                episodelist = self.showEpisodeInfo()
                logger.info('check: episodelist:{}'.format(episodelist))
                if not self.errflag:
                    self.confirmButton.setEnabled(True)
                    self.startButton.setEnabled(True)
                    self.showCommand(episodelist)
                    self.commandstrlist = episodelist
            else:
                self.CMDBrowser.append("剧名为空，请在字幕路径中输入...")

        elif self.renameSubCheckBox.isChecked():
            self.renameSub()
        else:
            commandalllist = self.commandCombin()
            if not self.errflag:
                commandstrlist = []
                for commandlist in commandalllist:
                    commandstr = self.commandSplicing(commandlist)
                    commandstrlist.append(commandstr)

                if self.onlydel:
                    self.filepath = self.filepathEdit.text()
                    if self.filepath != '' and os.path.exists(self.filepath):
                        alllist = []
                        onlyfiles = [f for f in listdir(self.filepath) if isfile(join(self.filepath, f))]
                        if len(onlyfiles) != 0:
                            renamelist = []
                            for file in onlyfiles:
                                if " (1).mkv" in file:
                                    alllist.append(file)
                                    removefile = file.replace(' (1)', '')
                                    renamelist.append([file, removefile])
                                    self.showCommand(renamelist)
                                    # self.CMDBrowser.append(file + ' --> ' + removefile)
                            removelist = []
                            for file in onlyfiles:
                                if "." + self.subfiletype in file:
                                    alllist.append(file)
                                    removelist.append(file)
                            if len(removelist) != 0:
                                self.CMDBrowser.append('删除字幕如下：')
                                for sub in removelist:
                                    self.CMDBrowser.append(sub)
                            if len(alllist) != 0:
                                self.startButton.setEnabled(True)
                                self.commandstrlist = []
                            else:
                                self.CMDBrowser.append('未找能可以删除和重命名文件...')
                        else:
                            self.CMDBrowser.append('未找到文件...')
                    else:
                        self.CMDBrowser.append('输入路径为空或非文件夹')
                else:
                    if not self.errflag and len(commandstrlist) != 0:
                        logger.info('check: mixmode')
                        self.confirmButton.setEnabled(True)
                        self.showCommand(commandalllist)
                        self.startButton.setEnabled(True)
                    self.commandstrlist = commandstrlist
                    for commandstr in self.commandstrlist:
                        self.CMDBrowser.append(commandstr)
        # except Exception as e:
        #     logger.error('check: error{}'.format(str(e)))
        #     self.startButton.setEnabled(False)



    def run(self):
        try:
            commandall = self.commandstrlist
            logger.info('run: commandstrlist: {}'.format(commandall))
            self.filepath = self.filepathEdit.text()
            if not self.errflag:
                self.startButton.setEnabled(False)
                self.checkButton.setEnabled(False)
                self.t1 = Starthread(commandstrlist=self.commandstrlist, filepath=self.filepath,
                                     subfiletype='.' + self.subfiletype,
                                     renameEpisodeCheckBox=self.renameEpisodeCheckBox, delCheckBox=self.delCheckBox)
                self.t1._signal.connect(self.set_btn)
                self.t1.start()
                self.t1.trigger.connect(self.display)
        except Exception as e:
            logger.error(e)
            logger.error("run:{}".format(str(e)))

    def display(self, str):
        self.CMDBrowser.append(str)
        self.CMDBrowser.update()

    def set_btn(self):
        self.checkButton.setEnabled(True)

    def path2list(self, path, type):
        onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
        filelist = [f for f in onlyfiles if f.endswith(type)]
        return filelist
    """
    文件过滤
    """
    def filter(self, onlyfiles, keyword):
        filterlist = []
        for i in onlyfiles:
            if self.filter_1(i, keyword):
                continue
            filterlist.append(i)
        return filterlist
    """
    关键字过滤
    """
    def filter_1(self, str, keyword):
        for i in keyword:
            if i == '':
                continue
            if i in str:
                return True
        return False

    """
    按集数
    : rstlist: 初始和检索后字典
    : filelist: 需要匹配的文件列表
    : rstname: 需要匹配的名字
    : rstpath: 需要匹配的文件路径
    """
    def gettogether(self, rstlist, filelist, rstname, rstpath, rex, rex_1, filetype):
        allnum = len(rstlist)
        # print(allnum)
        countrstfile = 0
        if rex_1 == '':
            rstlist = self.gettogether_1(rstlist, filelist, rstname, rstpath, filetype)
            return self.gettogether_1(rstlist, filelist, rstname, rstpath, filetype)
        for num in range(self.initepisode, allnum + self.initepisode+1):
            number = str(num).rjust(2, '0')
            number_1 = rex.replace('$', number)
            for filedict in rstlist:
                if number_1 in filedict['filename'].upper():
                    filepathname = os.path.join(self.filepath, filedict['filename'])
                    filepathname = '"' + filepathname + '"'
                    filedict.update({'filepathname': filepathname})
                    number_2 = rex_1.replace('$', number)
                    for file in filelist:
                        fileUpper = file.upper()
                        if number_2 in fileUpper:
                            rst = file
                            filedict.update({rstname: file})
                            rst = os.path.join(rstpath, rst)
                            rst = '"' + rst + '"'
                            filedict.update({rstname+'path': rst})
                            countrstfile += 1
                            break
                    break
        rstlist = [item for item in rstlist if rstname in item]
        if countrstfile == 0:
            self.errflag = True
            self.CMDBrowser.append('未能匹配到{}文件，请检查检索方式是否正确'.format(rstname))
        return rstlist

    """
    按名字
    """
    def gettogether_1(self, rstlist, filelist, rstname, rstpath, filetype):
        countrstfile = 0
        for filedict in rstlist:
            filename = filedict['filename'].replace('.' + filetype, '')
            for file in filelist:
                if filename in file:
                    countrstfile += 1
                    filenamepath = os.path.join(rstpath, file)
                    filenamepath = '"' + filenamepath + '"'
                    filedict.update({rstname: file,
                                     rstname+'path': filenamepath})
                    break
        rstlist = [item for item in rstlist if rstname in item]

        if countrstfile == 0:
            self.errflag = True
            self.CMDBrowser.clear()
            self.CMDBrowser.append('未能匹配到{}文件，请检查检索方式是否正确'.format(rstname))
        return rstlist

    """
    处理源文件
    """
    def gettogether_2(self, filelist, rex):
        reslist = []
        allnum = len(filelist)
        print('gettogether_2', allnum)
        res = {'filename': 'Na',
               'filepathname': 'Na',
               'outputpathname': 'Na'
               }
        if rex == '':
            for file in filelist:
                filepathname = os.path.join(self.filepath, file)
                filepathname = '"' + filepathname + '"'
                outputname = file.replace('.mkv', ' (1).mkv')
                outputpathname = os.path.join(self.filepath, outputname)
                outputpathname = '"' + outputpathname + '"'
                res.update({'filename': file,
                            'filepathname': filepathname,
                            'outputpathname': outputpathname})
                reslist.append(res.copy())
        else:
            for num in range(self.initepisode, allnum + self.initepisode+1):
                number = str(num).rjust(2, '0')
                print(number)
                number_1 = rex.replace('$', number)
                for file in filelist:
                    fileUpper = file.upper()
                    if number_1 in fileUpper:
                        filepathname = os.path.join(self.filepath, file)
                        filepathname = '"' + filepathname + '"'
                        outputname = file.replace('.mkv', ' (1).mkv')
                        outputpathname = os.path.join(self.filepath, outputname)
                        outputpathname = '"' + outputpathname + '"'
                        res.update({'filename': file,
                                    'filepathname': filepathname,
                                    'outputpathname': outputpathname})
                        reslist.append(res.copy())
                        break
        return reslist


class Starthread(QThread):
    trigger = pyqtSignal(str)
    _signal = pyqtSignal()

    def __init__(self, commandstrlist, filepath, subfiletype, renameEpisodeCheckBox, delCheckBox, parent=None):
        QThread.__init__(self, parent)
        self.commandstrlist = commandstrlist
        self.filepath = filepath
        self.subfiletype = subfiletype
        self.renameEpisodeCheckBox = renameEpisodeCheckBox
        self.delCheckBox = delCheckBox

    def commandSplicing(self, cmdlist):
        str1 = ''
        for i in cmdlist:
            str1 = str1 + ' ' + i
            str1 = str1.strip()
        return str1

    def run(self):
        qmut_1.lock()
        self.trigger.emit("开始")
        if self.renameEpisodeCheckBox.isChecked():
            self.rename(self.commandstrlist)
        else:
            count = len(self.commandstrlist)
            if count != 0:
                for i, command in enumerate(self.commandstrlist):
                    self.trigger.emit("正在执行:{}/{}...\n".format(i+1, count))
                    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, stdin=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    for line in iter(p.stdout.readline, b''):
                        line = str(line, encoding="utf-8")
                        if '100%' in line:
                             self.trigger.emit("进度: 100%")
                        else:
                            self.trigger.emit(line)
                self.trigger.emit("已全部完成")

            if self.delCheckBox.isChecked():
                self.remove(self.filepath)
        qmut_1.unlock()
        self._signal.emit()

    def remove(self, filepath):
        self.trigger.emit("正在执行删除和重命名")
        onlyfiles = [f for f in listdir(filepath) if isfile(join(filepath, f))]
        renamelist = []
        ass = []
        for file in onlyfiles:
            if "(1).mkv" in file:
                renamelist.append(file)
        for file in onlyfiles:
            if self.subfiletype in file:
                ass.append(file)
        if len(renamelist) != 0:
            self.trigger.emit('正在重命名...')
            for file in renamelist:
                removefile = file.replace(' (1)', '')
                try:
                    res = shell.SHFileOperation((0, shellcon.FO_DELETE, os.path.join(filepath, removefile), None,
                                                 shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION,
                                                 None, None))
                except Exception as e:
                    print(e)
            for file in renamelist:
                removefile = file.replace(' (1)', '')
                self.trigger.emit(file + ' --> ' + removefile)
                try:
                    os.rename(os.path.join(filepath, file), os.path.join(filepath, removefile))
                except Exception as e:
                    print(e)
            self.trigger.emit('重命名完成')
        else:
            self.trigger.emit('无需要删除和重命名的文件！')
        if len(ass) != 0:
            self.trigger.emit('正在删除字幕...')
            for file in ass:
                self.trigger.emit(file)
                res = shell.SHFileOperation((0, shellcon.FO_DELETE, os.path.join(filepath, file), None,
                                             shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION,
                                             None, None))
            self.trigger.emit('删除完成！')
        else:
            self.trigger.emit('无需要删除的字幕！')

    def rename(self, commandlist):
        self.trigger.emit('正在重命名...')
        for episodelist in commandlist:
            # self.trigger.emit('episodename: ' + episodelist)
            season = episodelist[2]
            # self.trigger.emit('season: '+season)
            episodepath = episodelist[1].strip('"')
            # self.trigger.emit('episodepath: ' + episodepath)
            episode = episodelist[3]
            # self.trigger.emit('episode: ' + episode)
            episodename = episodelist[0]
            # self.trigger.emit('episodename: ' + episodename)
            filepath = os.path.dirname(episodepath)
            # self.trigger.emit('filepath: ' + filepath)
            seasonpath = os.path.join(filepath, 'season' + ' ' + str(int(season)))
            # self.trigger.emit('seasonpath: ' + seasonpath)
            filename = episodepath.split("\\")[-1].replace('[', ' ').replace(']', ' ')
            # self.trigger.emit('filename: ' + filename)
            rename = '{} - S{}E{} - {}'.format(episodename, season, episode, filename)
            # self.trigger.emit('rename: ' + rename)
            renamepath = os.path.join(seasonpath, rename)
            # self.trigger.emit('renamepath: ' + renamepath)
            self.mkdir(seasonpath)
            self.trigger.emit(episodepath + ' --> ' + renamepath)
            os.rename(episodepath, renamepath)
        self.trigger.emit('重命名完成！')

    def mkdir(self, path):
        if not os.path.exists(path):
            os.mkdir(path)


class configWindow(QWidget, Ui_Form):
    def __init__(self):
        super(configWindow, self).__init__()
        self.setupUi(self)
        self.initUI()

    def initUI(self):
        self.paratable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.paratable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.paratable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.paratable.verticalHeader().setVisible(False)  # 隐藏列表头
        self.updateButton.clicked.connect(self.updatefile)
        self.closeButton.clicked.connect(self.closewindows)
        for i in range(5):
            self.paratable.insertRow(i)

        for index, i in enumerate(['mkvpath', '', 'mkvmix路径', 'filterword', '', '需要过滤字幕的关键词',
                                   'filepathrex', '', '源文件过滤选项', 'subpathrex', '', '字幕过滤选项',
                                   'audiopathrex', '', '音轨过滤选项']):
            item = QTableWidgetItem(i)
            if index%3 == 0 or index%3 == 2:
                item.setFlags(Qt.ItemIsEnabled)
                self.paratable.setItem(int(index/3), index%3, item)
        config = configparser.ConfigParser()
        inipath = 'config.ini'
        config.read(inipath, encoding="utf-8")

        keywordlist = config["mkvmix"]["keyword"]
        mkvpath = config["mkvmix"]["mkvpath"]
        filepathrex = config["mkvmix"]["filepathrex"]
        subpathrex = config["mkvmix"]["subpathrex"]
        audiopathrex = config["mkvmix"]["audiopathrex"]
        self.paratable.setItem(0, 1, QTableWidgetItem(mkvpath))
        self.paratable.setItem(1, 1, QTableWidgetItem(keywordlist))
        self.paratable.setItem(2, 1, QTableWidgetItem(filepathrex))
        self.paratable.setItem(3, 1, QTableWidgetItem(subpathrex))
        self.paratable.setItem(4, 1, QTableWidgetItem(audiopathrex))

    def closewindows(self):
        self.close()

    def updatefile(self):
        row = self.paratable.rowCount()
        configdict = {}
        configdict.update({'keyword': self.paratable.item(1, 1).text(),
                           'mkvpath': self.paratable.item(0, 1).text(),
                          'filepathrex': self.paratable.item(2, 1).text(),
                          'subpathrex': self.paratable.item(3, 1).text(),
                          'audiopathrex': self.paratable.item(4, 1).text()})
        f = open('config.ini', 'w')
        f.writelines('[{}]\n'.format("mkvmix"))
        for k, v in configdict.items():
            f.writelines('{} = {}\n'.format(k, v))
        f.close()
        QMessageBox.about(self, 'Success', '      更新成功          ')



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)  # 创建一个QApplication，也就是你要开发的软件app
    mixMix = MkvMixMain()
    mixMix.show()
    configWindow = configWindow()
    mixMix.action.triggered.connect(configWindow.show)
    sys.exit(app.exec_())
