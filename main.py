import os
import sys
import uuid
import yaml
import time
import re

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import QApplication, QDialog

import gui
import get

qmutex_Getting = QMutex()
repost=None
reply=None
like=None
condition=None
reposts_list=[]
reply_list=[]
like_list=[]
true_dict={}

def listmerge(source:list):
    for i in source:
        if i['type'] == 'repost':
            basic = [True, False, False]
        elif i['type'] == 'reply':
            basic = [False, True, False]
        elif i['type'] == 'like':
            basic = [False, False, True]
        if i['mid'] not in true_dict.keys():
            true_dict[i['mid']] = {
                'stat':basic,
                'level':i['level'],
                'uname':i['uname'],
                'avatar':i['avatar']
            }
        else:
            if i['type'] == 'repost':
                true_dict[i['mid']]['stat'][0] = True
            elif i['type'] == 'reply':
                true_dict[i['mid']]['stat'][1] = True
            elif i['type'] == 'like':
                true_dict[i['mid']]['stat'][2] = True


class GetThread(QThread):
    global repost, reply, like, condition
    callback_msg = pyqtSignal(str)
    btns = pyqtSignal(bool)
    prog = pyqtSignal(float)

    def __init__(self):
        super().__init__()

    def run(self):
        if qmutex_Getting.tryLock(0):
            true_dict.clear()
            myDlg.ui.lcdNumber.setProperty("intValue", -1)
            self.prog.emit(0)

            like = bool(myDlg.ui.CheckBoxLike.isChecked())
            reply = bool(myDlg.ui.CheckBoxReply.isChecked())
            repost = bool(myDlg.ui.CheckBoxRepost.isChecked())

            condition = bool(myDlg.ui.RadioAnd.isChecked())
            if (like or reply or repost) is False:
                self.callback_msg.emit(f'[{int(time.time())}]您似乎忘记勾选获取条件了。')
                qmutex_Getting.unlock()
                self.btns.emit(True)
                return

            # 正则匹配获取动态ID, 有可能出现胡来的情况
            dynamic_re = "\d+"
            dynamic_id = re.search(dynamic_re, myDlg.ui.LineDynamic.text())
            if dynamic_id is None:
                self.callback_msg.emit(f'[{int(time.time())}]您似乎输入了无效的ID或动态地址。')
                qmutex_Getting.unlock()
                self.btns.emit(True)
                return
            else:
                self.callback_msg.emit(f'[{int(time.time())}]您输入的ID是{dynamic_id.group(0)}。')
            __dynamic_id = dynamic_id.group(0)
            __dynamic_detail = get.n_get_dynamic_detail_main(__dynamic_id, printfunc=self.callback_msg.emit)
            # print(__dynamic_detail)

            if not __dynamic_detail:
                self.callback_msg.emit(f'[{int(time.time())}]获取的动态详细信息不正确。')
                qmutex_Getting.unlock()
                self.btns.emit(True)
                return

            self.callback_msg.emit(f'[{int(time.time())}]动态当前浏览量{__dynamic_detail["view"]}, 转发数{__dynamic_detail["repost"]}, 评论数{__dynamic_detail["comment"]}, 点赞数{__dynamic_detail["like"]}。')
            self.callback_msg.emit(f'[{int(time.time())}]动态发布者: {__dynamic_detail["uname"]}, UID: {__dynamic_detail["uid"]}')
            self.callback_msg.emit(f'[{int(time.time())}]动态内容:\n{__dynamic_detail["content"]}')
            self.prog.emit(20)

            self.callback_msg.emit(f'[{int(time.time())}]获取转发: {repost}, 获取回复: {reply}, 获取点赞: {like}')
            if repost:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取转发情况。')
                reposts_list = get.n_get_dynamic_repost_main(int(__dynamic_detail['dynamic_id']), printfunc=self.callback_msg.emit)
                listmerge(reposts_list)
                self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(reposts_list)}条转发。')
            self.prog.emit(40)
            if reply:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取回复情况。')
                if 'rid' in __dynamic_detail.keys():
                    reply_list = get.n_get_reply_main(int(__dynamic_detail['rid']), oidtype=__dynamic_detail['type'], printfunc=self.callback_msg.emit)
                    listmerge(reply_list)
                    self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(reply_list)}条回复。')
                else:
                    reply_list=[]
                    listmerge(reply_list)
                    self.callback_msg.emit(f'[{int(time.time())}]评论区获取出错。')
            self.prog.emit(60)
            if like:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取点赞情况。')
                like_list = get.n_get_dynamic_like_main(int(__dynamic_detail['dynamic_id']), printfunc=self.callback_msg.emit)
                listmerge(like_list)
                self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(like_list)}条点赞。')
            self.prog.emit(80)
            myDlg.ui.lcdNumber.setProperty("intValue", len(true_dict))
            # TODO

            self.prog.emit(100)
            qmutex_Getting.unlock()
            self.btns.emit(True)
            return
        else:
            self.callback_msg.emit(f'[{int(time.time())}]程序正忙, 请勿进行操作。')


class MainDialog(QDialog):
    
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent)
        self.ui = gui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.getthread=GetThread()
        self.getthread.callback_msg.connect(self.LogWindow)
        self.getthread.btns.connect(self.btns)
        self.getthread.prog.connect(self.progress)
    
    def LogWindow(self, msg):
        with open('log.txt', 'a+', encoding='UTF-8') as logf:
            logf.write(msg)
            logf.write('\n')
        self.ui.textBrowser.append(msg)

    def CleanLogWindow(self):
        self.ui.textBrowser.clear()
    
    def progress(self, value):
        self.ui.progressBar.setProperty("value", value)
    
    def btns(self, state):
        self.ui.PushLottery.setEnabled(state)

        self.ui.RadioAnd.setEnabled(state)
        self.ui.RadioOr.setEnabled(state)

        self.ui.CheckBoxLike.setEnabled(state)
        self.ui.CheckBoxReply.setEnabled(state)
        self.ui.CheckBoxRepost.setEnabled(state)
        # self.ui.PushClear.setEnabled(state)

    def Lottery(self):
        self.btns(False)
        if self.ui.CheckAutoClear.isChecked():
            self.CleanLogWindow()
        self.getthread.start()

if __name__ == '__main__':
    myapp = QApplication(sys.argv)
    myDlg = MainDialog()
    myDlg.show()
    sys.exit(myapp.exec_())