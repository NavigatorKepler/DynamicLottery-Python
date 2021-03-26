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

            self.callback_msg.emit(f'[{int(time.time())}]获取转发: {repost}, 获取回复: {reply}, 获取点赞: {like}')
            if repost:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取转发情况。')
                reposts_list = get.n_get_dynamic_repost_main(int(__dynamic_id), printfunc=self.callback_msg.emit)
                listmerge(reposts_list)
                self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(reposts_list)}条转发。')

            if reply:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取回复情况。')
                reply_aid = get.n_get_dynamic_detail_main(int(__dynamic_id), printfunc=self.callback_msg.emit)
                if 'rid' in reply_aid.keys():
                    reply_list = get.n_get_reply_main(int(reply_aid['rid']), printfunc=self.callback_msg.emit)
                    listmerge(reply_list)
                    self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(reply_list)}条回复。')
                else:
                    reply_list=[]
                    self.callback_msg.emit(f'[{int(time.time())}]评论区获取出错。')

            if like:
                self.callback_msg.emit(f'[{int(time.time())}]开始获取点赞情况。')
                like_list = get.n_get_dynamic_like_main(int(__dynamic_id), printfunc=self.callback_msg.emit)
                listmerge(like_list)
                self.callback_msg.emit(f'[{int(time.time())}]此次共获取到了{len(like_list)}条点赞。')

            # TODO

            qmutex_Getting.unlock()
            self.btns.emit(True)
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
    
    def LogWindow(self, msg):
        self.ui.textBrowser.append(msg)

    def CleanLogWindow(self):
        self.ui.textBrowser.clear()
    
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