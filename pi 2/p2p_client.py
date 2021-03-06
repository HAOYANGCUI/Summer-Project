from xmlrpclib import ServerProxy
from cmd import Cmd
from os.path import join
import thread
from threading import Thread,Event,Timer
from time import sleep
import sys
import socket
import argparse
import logging
# by kzl
from settings import mylogger,NOT_EXIST,ACCESS_DENIED,ALREADY_EXIST,SUCCESS,PORT,SHARED_FOLDER,SERVER_START_TIME,SECRET_LENGTH,IPS_FILE,URL_PREFIX,UPDATE_INTERVAL
from utils import random_string,get_lan_ip,geturl
from p2p_server import Node
from threads import UpdateGUIListTimer 
# gui
from PyQt4 import QtGui,QtCore
from settings import WIN_WIDTH,WIN_HEIGHT,ICON_APP,ICON_FETCH,ICON_QUIT

IP_LAN = get_lan_ip()
SERVER_URL = geturl(URL_PREFIX,IP_LAN,PORT)


class NodeServerThread(Thread):
	"""
	thread for starting and stopping node server
	"""
	def __init__(self,name,url,dirname,secret,ipsfile,event_running):
		mylogger.info('[__init__]: {0}'.format(name))
		super(NodeServerThread,self).__init__()
		self.name = name
		self.daemon = True
		self.url = url
		self.dirname = dirname
		self.secret = secret
		self.ipsfile = ipsfile
		self.event_running = event_running

		# New variables
		# server_node
		self.server_node = None
		
	def run(self):
		mylogger.info('[NodeServerThread]: {0} starting...'.format(self.name))
		self.server_node = Node(self.url,self.dirname,self.secret,self.ipsfile,self.event_running)
		# start node server
		self.server_node._start()

	def stop(self):
		mylogger.info('[NodeServerThread] {0} stopping ...'.format(self.name))
		# shutdown node server
		self.server_node._shutdown()
		mylogger.info('[NodeServerThread] {0} stopped'.format(self.name))

class NodeService():
	"""
	node service: start stop list listall fetch 
	"""	
	def __init__(self,url,dirname,ipsfile):
		self.url = url
		self.dirname = dirname
		self.secret = random_string(SECRET_LENGTH)
		self.ipsfile = ipsfile
		# indicate whether node server is running
		self.event_running= Event() # flag is false by default

		# server thread instance
		self.server_thread = NodeServerThread('Thread-SERVER',self.url,self.dirname,self.secret,self.ipsfile,self.event_running)
		# node server proxy for client use
		self.server = None

	def get_filepath(self,query):
		"""
		query like  './share/11.txt' or '11.txt'
		"""
		if query.startswith(self.dirname):
			return query
		else:
			return join(self.dirname,query)

	def start(self):
		"""
		start NodeServerThread in child thread,and connect to server in main thread 
		"""
		mylogger.info('[start]: NodeService starting...')
		# 1)start node server in child thread
		self.server_thread.start()
		# block current thread until node server is started
		if not self.event_running.wait(3):
			sys.exit()
		mylogger.info('[start]: NodeServerThread started') 
		# 2) connect to server in main thread
		self.server = ServerProxy(self.url,allow_none=True)
		mylogger.info('[start]: NodeService started')

	def stop(self):
		mylogger.info('[stop]: NodeService stopping...')
		# 1) stop node server in child thread
		self.server_thread.stop()
		mylogger.info('[stop]: NodeService stopped')

	"""
	node server methods
	"""
	def fetch(self,query):
		# fetch file from available node
		filepath = self.get_filepath(query)
		return self.server.fetch(filepath,self.secret)

	def get_local_files(self):
		# return local_files
		return self.server.get_local_files()

	def get_remote_files(self):
		# return remote_files
		return self.server.get_remote_files()
		
	def update_local_list(self):
		# update local_files 
		self.server.update_local_list()

	def update_remote_list(self):
		# update remote_files 
		self.server.update_remote_list()
	
	def get_url(self):
		# get url of local node
		return self.url

	def get_remote_urls(self):
		# get remote urls 
		return self.server.get_remote_urls()

	def is_local_updated(self):
		# whether local updated
		return self.server.is_local_updated()

	def is_remote_updated(self):
		# whether remote updated
		return self.server.is_remote_updated()

	def clear_local_update(self):
		# clear local update and set to false
		self.server.clear_local_update()

	def clear_remote_update(self):
		# clear remote update and set to false
		self.server.clear_remote_update()

class ConsoleClient(NodeService,Cmd):
	"""
	a simple console client
	"""
	prompt = '>'

	def __init__(self,url,dirname,ipsfile):
		NodeService.__init__(self,url,dirname,ipsfile)
		Cmd.__init__(self)
		# start node service
		NodeService.start(self)

	def do_fetch(self,arg):
		"""
		fetch <filename>
		"""
		if not arg or not arg.strip():
			msg = '###[do_fetch]: Please enter file name'
			print(msg)
			return
		code = NodeService.fetch(self,arg)
		if code == SUCCESS:
			msg ="###[do_fetch]: Fetch successfully for [{0}]".format(arg)
		elif code == ACCESS_DENIED:
			msg ="###[do_fetch]: Access denied for [{0}]".format(arg)
		elif code == NOT_EXIST:
			msg ="###[do_fetch]: Not exist for [{0}]".format(arg)
		else:
			msg = "###[do_fetch]: Already exist for [{0}]".format(arg)
		print(msg)

	def do_list(self,arg):
		"""
		list all shared files in local node	
		"""
		print('###[do_list]: list shared files in local node')
		for f in NodeService.get_local_files(self):
			print(f)

	def do_listr(self,arg):
		"""
		list shared files in all remote nodes	
		"""
		print('###[do_listr]: list shared files in all remote nodes')
		for url,lt in NodeService.get_remote_files(self).iteritems():
			print('*'*60)
			print('url:{0}'.format(url))
			print('files:')
			for f in lt:
				print(f)

	def do_update(self,arg):
		"""
		update local files list
		"""
		print('###[do_update]: update local files list')
		NodeService.update_local_list(self)
		self.do_list(arg)

	def do_updater(self,arg):
		"""
		update remote files list
		"""
		print('###[do_updater]: update remote files list')
		NodeService.update_remote_list(self)
		self.do_listr(arg)

	def do_url(self,arg):
		"""
		get url of local node
		"""
		print('###[do_url]: get url of local node')
		print(NodeService.get_url(self))

	def do_urlr(self,arg):
		"""
		get remote urls
		"""
		print('###[do_urlr]: get remote urls')
		for url in NodeService.get_remote_urls(self):
			print url

	def do_isupdate(self,arg):
		"""
		whether local list updated
		"""
		print('###[do_isupdate]: whether local list updated')
		print(NodeService.is_local_updated(self))

	def do_isupdater(self,arg):
		"""
		whether remote list updated
		"""
		print('###[do_isupdater]: whether remote list updated')
		print(NodeService.is_remote_updated(self))

	def do_exit(self,arg):
		"""
		exit or quit program
		"""
		print('###[do_exit]: program is going to exit... ')
		NodeService.stop(self)
		sys.exit()

	do_EOF = do_quit = do_exit;

	def do_help(self,arg):
		"""
		output help of command
		"""
		Cmd.do_help(self,arg)

def main_console():
	client = ConsoleClient(SERVER_URL,SHARED_FOLDER,IPS_FILE)
	client.cmdloop()

# argparse
parser = argparse.ArgumentParser(description='p2p node application')
'''
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", action="store_true",help="output detail to console")
group.add_argument("-q", "--quiet", action="store_true",help="output detail to log file")
'''
group_mode = parser.add_mutually_exclusive_group()
group_mode.add_argument("-c", "--console",action="store_true", help = "run application in console mode" )
group_mode.add_argument("-g", "--gui", action = "store_true", help="run application in gui mode")
args = parser.parse_args()


class GuiWidget(QtGui.QWidget):
	"""
	gui widget: 
	"""	
	def __init__(self,parent):
		super(GuiWidget,self).__init__(parent)
		self.initUI()

	def initUI(self):
		# controls and layouts
		hbox1 = QtGui.QHBoxLayout()
		self.le = QtGui.QLineEdit()
		self.btn_fetch = QtGui.QPushButton('Fetch File')
		self.btn_update = QtGui.QPushButton('Update List')
		hbox1.addWidget(self.le)
		hbox1.addWidget(self.btn_fetch)
		hbox1.addWidget(self.btn_update)
		
		vbox1 = QtGui.QVBoxLayout()
		self.label_local = QtGui.QLabel('local')
		self.list_local = QtGui.QListWidget()
		vbox1.addWidget(self.label_local)
		vbox1.addWidget(self.list_local)
		
		vbox2 = QtGui.QVBoxLayout()
		self.label_remote = QtGui.QLabel('remote')
		self.list_remote = QtGui.QListWidget()
		vbox2.addWidget(self.label_remote)
		vbox2.addWidget(self.list_remote)
		
		hbox2 = QtGui.QHBoxLayout()
		hbox2.addLayout(vbox1)
		hbox2.addLayout(vbox2)

		vbox = QtGui.QVBoxLayout(self)
		vbox.addLayout(hbox1)
		vbox.addLayout(hbox2)
	
		# set layout
		self.setLayout(vbox)

class GuiClient(NodeService,QtGui.QMainWindow):
	"""
	a simple client with gui
	"""
	def __init__(self,url,dirname,ipsfile,update_interval):
		NodeService.__init__(self,url,dirname,ipsfile)
		QtGui.QMainWindow.__init__(self)
		# update_interval for update timer
		self.update_interval = update_interval
		# start gui client
		self.start()

	def start(self):
		# 1)start node service
		NodeService.start(self)
		# 2)init params
		self.initParams()
		# 3)init gui
		self.initUI()

		# 4)user timer to update gui list every 3 seconds
		self.update_timer = UpdateGUIListTimer('Thread-Update GUI Timer',self.update_interval,self.updateList)
		self.update_timer.start()
	
	def stop(self):	
		# 1) stop update timer
		self.update_timer.stop()
		# 2) stop node service
		NodeService.stop(self)

	def initParams(self):
		self.localurl = NodeService.get_url(self)
		self.local_files = []
		self.remote_files = {}

	def initUI(self):
		mylogger.info("[initUI]...")
		# menus toolbars statusbar
		# actions
		self.fetchAction = QtGui.QAction(QtGui.QIcon(ICON_FETCH), '&Fetch', self)
		self.fetchAction.setShortcut('Ctrl+F')
		self.fetchAction.setStatusTip('Fetch file')
		self.fetchAction.triggered.connect(self.onFetchHandler)

		self.stopAction = QtGui.QAction(QtGui.QIcon(ICON_QUIT), '&Quit', self)
		self.stopAction.setShortcut('Ctrl+Q')
		self.stopAction.setStatusTip('Quit application')
		self.stopAction.triggered.connect(self.close)

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(self.fetchAction)
		fileMenu.addAction(self.stopAction)
		
		toolbar = self.addToolBar('tool')
		toolbar.addAction(self.fetchAction)
		toolbar.addAction(self.stopAction)
	
		self.statusbar = self.statusBar()
		# GuiWidget 
		self.main_widget = GuiWidget(self)
		self.main_widget.le.textChanged[str].connect(self.onTextChanged)
		self.main_widget.btn_fetch.clicked.connect(self.onFetchHandler)
		self.main_widget.btn_update.clicked.connect(self.onUpdateHandler)
		self.main_widget.list_remote.itemClicked.connect(self.onListItemClicked)
		# set central widget for main window
		self.setCentralWidget(self.main_widget)

		# set control states
		self.setFetchEnabled(False)
		# set list files
		self.setLocal()
		self.setRemote()

		# settings for window
		self.resize(WIN_WIDTH,WIN_HEIGHT)
		#self.move(200,200)
		self.center()
		self.setWindowTitle('File Sharing Client')
		self.setWindowIcon(QtGui.QIcon(ICON_APP))
		self.show()

	def closeEvent(self,event):
		mylogger.info("[closeEvent]")
		# If we close the QtGui.QWidget, the QtGui.QCloseEvent is generated and closeEvent is called.
        	reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure to exit?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes) 
        	if reply == QtGui.QMessageBox.Yes:
			msg = ('###[closeEvent]: program is going to exit... ')
			mylogger.info(msg)
			print(msg)
			self.stop()
            		event.accept()
       		else:
            		event.ignore()        

	def onUpdateHandler(self,value):
		mylogger.info("[onUpdateHandler]...")
		self.updateList()

	def _setLocalFiles(self):
		self.local_files = NodeService.get_local_files(self)

	def _setRemoteFiles(self):
		self.remote_files = NodeService.get_remote_files(self)

	def _setLocalLabel(self):
		#mylogger.info("[_setLocalLabel]...")
		str_local = "local@{0} [total {1} files]".format(self.localurl,len(self.local_files))
		self.main_widget.label_local.setText(str_local)

	def _getRemoteFileCount(self,remotefiles):
		count = 0
		for url,ls in remotefiles.iteritems():
			count +=len(ls)
		return count

	def _setRemoteLabel(self):
		#mylogger.info("[_setRemoteLabel]...")
		nodeCount = len(self.remote_files)
		fileCount = self._getRemoteFileCount(self.remote_files)
		str_remote = "remote [{0} nodes,total {1} files]".format(nodeCount,fileCount)
		self.main_widget.label_remote.setText(str_remote)

	def _setLocalList(self):
		#mylogger.info("[_setLocalList]...")
		self.main_widget.list_local.clear()
		for f in self.local_files:
			self.main_widget.list_local.addItem(f)

	def _setRemoteList(self):
		#mylogger.info("[_setRemoteList]...")
		self.main_widget.list_remote.clear()
		for url,lt in self.remote_files.iteritems():
			for f in lt:
				self.main_widget.list_remote.addItem(f)

	def setLocal(self):
		if NodeService.is_local_updated(self):
			mylogger.info('[setLocal]...')
			self._setLocalFiles()
			self._setLocalLabel()
			self._setLocalList()
			mylogger.info('[setLocal] finished')
			# after set local list,clear local update
			NodeService.clear_local_update(self) # set to false
		else:
			mylogger.info('*********NO GUI UPDATE FOR local list*********')
	
	def setRemote(self):
		if NodeService.is_remote_updated(self):
			mylogger.info('[setRemote]...')
			self._setRemoteFiles()
			self._setRemoteLabel()
			self._setRemoteList()
			mylogger.info('[setRemote] finished')
			# after set remote list,clear remote update
			NodeService.clear_remote_update(self) # set to false
		else:
			mylogger.info('*********NO GUI UPDATE FOR remote list*********')

	def updateList(self):
		mylogger.info('-'*50)
		mylogger.info("[updateList]...")
		# update local and remote files
		NodeService.update_local_list(self)
		NodeService.update_remote_list(self)
		self.setLocal()
		self.setRemote()
		mylogger.info("[updateList] finished")
		mylogger.info('-'*50)

	def setFetchEnabled(self,enabled):
		self.fetchAction.setEnabled(enabled)
		self.main_widget.btn_fetch.setEnabled(enabled)

	def center(self):
		mbr = self.frameGeometry()
        	cen = QtGui.QDesktopWidget().availableGeometry().center()
        	mbr.moveCenter(cen)
        	self.move(mbr.topLeft())

	def keyPressEvent(self,event):	
		mylogger.info("[keyPressEvent]")
		if event.key() == QtCore.Qt.Key_Escape:
			self.close()
		elif event.key() == QtCore.Qt.Key_Enter:
			self.onFetchHandler(False)
		else: pass
	

	def onTextChanged(self,value):
		if value.isEmpty():
			# set control states
			self.setFetchEnabled(False)
		else:
			# set control states
			self.setFetchEnabled(True)
		
	def onFetchHandler(self,value):
		mylogger.info("[onFetchHandler]")
		# by default ,for a button value is False
		arg = str(self.main_widget.le.text())
		if not arg.strip():
			msg = 'Please enter query file'
			self.statusbar.showMessage(msg)
			return
		# add statusbar messge for fetching file
		msg = "Fetching [{0}].......".format(arg)
		mylogger.info(msg)
		self.statusbar.showMessage(msg)
		# use NodeService
		code = NodeService.fetch(self,arg)
		if code == SUCCESS:
			msg ="Fetch successfully for [{0}]".format(arg)
			self._onFetchSuccessfully(arg)
		elif code == ACCESS_DENIED:
			msg ="Access denied for [{0}]".format(arg)
		elif code == NOT_EXIST:
			msg ="Not exist for [{0}]".format(arg)
		else:
			msg = "Already exist for [{0}]".format(arg)
		mylogger.info(msg)
		self.statusbar.showMessage(msg)
	
	def _onFetchSuccessfully(self,arg):
		# when fetch successfully, need to update local list
		NodeService.update_local_list(self)
		self.setLocal()

	def onListItemClicked(self,value):
		self.main_widget.le.setText(value.text())
		self.statusbar.showMessage('')
		
def main_gui():
	app = QtGui.QApplication(sys.argv)
	client = GuiClient(SERVER_URL,SHARED_FOLDER,IPS_FILE,UPDATE_INTERVAL)
	sys.exit(app.exec_())


if __name__ =='__main__':
	if args.console:
		main_console()
	else: # args.gui
		main_gui()
