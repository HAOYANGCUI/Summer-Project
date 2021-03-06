from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy,Fault,Binary
from os.path import isfile
import sys
import time
import socket
import thread
from threading import Thread,Event,Lock
# by kzl
from settings import mylogger,MAX_HISTORY_LENGTH,NOT_EXIST,ACCESS_DENIED,ALREADY_EXIST,SUCCESS,URL_PREFIX,PORT
from utils import inside,getport,read_urls,save_urls,list_equal
from files import list_all_files,savefile_frombinary_xmlrpc,readfile_asbinary_xmlrpc
from threads import SaveFileThread,SaveIPsThread

class FileInfo():
	"""
	class for storing file info
	"""
	def __init__(self,filename,filepath,filesize,filedate):
		self.filename = filename
		self.filepath = filepath
		self.filesize = filesize
		self.filedate = filedate

		
class Node:
	"""
	a simple node class
	"""
	def __init__(self,url,dirname,secret,ipsfile,event_running):
		self.url = url
		self.dirname = dirname
		self.secret = secret
		# ipsfile for storing all available nodes
		self.ipsfile = ipsfile
		# store all known urls in set (including self)
		self.known = set()
		# inform client node server is running
		self.event_running = event_running
		# inform client to update local or remote list
		self.event_update_local = Event()
		self.event_update_remote = Event()

		# New variables
		# store local node server for later shutdown
		self.local_server = None

		# NEW variables
		self.local_files = []
		# url---[f1,f2,f3...]
		self.remote_files = {}

	def _read(self):
		"""
		read urls from ipsfile
		"""
		mylogger.info('[_read]: reading urls ... ')
		urls = read_urls(self.ipsfile)
		# make sure self.url in urls
		if not self.url in urls:
			urls.append(self.url)
		for url in urls:
			self._add(url)
		mylogger.info('[_read]: reading urls finished')

	def _save(self):
		"""
		save urls to ipsfile
		"""
		mylogger.info('[_save]: saving urls ... ')
		save_urls(self.known,self.ipsfile)
		mylogger.info('[_save]: saving urls finiehed')

	def _start(self):
		"""
		start node server
		"""
		try:
			t = ('',getport(self.url))
			# in both server and client set allow_none=True
			self.local_server = SimpleXMLRPCServer(t,allow_none=True,logRequests=False)
			self.local_server.register_instance(self)
			msg ="[_start]: Server started at {0}...".format(self.url)
			print(msg)
			mylogger.info(msg)
			# 1)on start up ,read urls 
			self._read()
			# 2)after all urls added to known set,inform others about myself's status online
			self.online()
			mylogger.info('[_start]: event_running..')
			# 3)start server
			self.event_running.set() # set flag to true
			self.local_server.serve_forever()
		except socket.error,e:
			mylogger.warn(e)
			mylogger.warn('[_start]: socket error')
			mylogger.warn('[_start]: program is going to exit...')
			# event_running must be false
		except Exception, e:
			mylogger.warn(e)
			mylogger.warn('[_start]: except')
			mylogger.warn('[_start]: Server stopped at {0}'.format(self.url))
			# event_running must be false

	def _shutdown(self):
		"""
		shut down node server
		"""
		mylogger.warn('[_shutdown]: shutdown server...')
		# 1)on shutdown,save urls on thread-save
		thread_save = SaveIPsThread('Thread-save',self._save)
		thread_save.start()
		# 2) inform other nodes that myself is offline
		self.offline()
		# 3) shutdown server
		self.local_server.shutdown()

	def fetch(self,query,secret):
		"""
		fetch a given file from all available nodes
		query:  filepath
		"""
		mylogger.info('-'*60)
		mylogger.info('[fetch]: fetching from {0}'.format(self.url))
		if secret != self.secret:
			return ACCESS_DENIED
		code,data = self.query(query,self.url,[]) 
		mylogger.info('[fetch]: query return code {0}'.format(code))
		mylogger.info("[fetch]: knows: {0}".format(self.known))
		if code == SUCCESS:
			# create a background(daemon) thread to save file
			thread = SaveFileThread('Thread-savefile',query,data)
			thread.start()
		return code

	def query(self,query,starturl,history=[]):
		"""
		query a given file
		return value:(NOT_EXIST,None)(ACCESS_DENIED,None)(ALREADY_EXIST,None)(SUCCESS,data)
		"""
		mylogger.info('-'*40)
		mylogger.info('[query]: querying from {0}'.format(self.url))
		code,data = self._handle(query,starturl)
		if code == SUCCESS:
			mylogger.info('[query]: success')
			return code,data
		elif code == NOT_EXIST:
			# history is a list containing urls from which we can not find file
			history = history + [self.url]
			if len(history)>MAX_HISTORY_LENGTH:
				mylogger.info('[query]: history too long')
				return NOT_EXIST,None
			mylogger.info("[query]: query for {0} NOT in {1}".format(query,history))
			code,data = self._broadcast(query,starturl,history)
			mylogger.info("[query]: [after broadcast]: {0}".format(code))
			mylogger.info("[query]: knows: {0}".format(self.known))
			return code,data
		else: # access denied or already exist
			return code,data

	def _handle(self,query,starturl):
		"""
		handle query in local node
		# query like  './share/11.txt' 
		"""
		mylogger.info('-'*20)
		mylogger.info('[handle]: begin')
		filepath = query # query is filepath
		mylogger.info('[handle]: filepath is {0}'.format(filepath))
		if not isfile(filepath):
			mylogger.info('[handle]: not file')
			return NOT_EXIST,None
		if not inside(self.dirname,filepath):
			mylogger.info('[handle]: not inside')
			return ACCESS_DENIED,None
		if starturl == self.url:
			mylogger.info('[handle]: ******already exist******')
			return ALREADY_EXIST,None
		mylogger.info('[handle]: success')
		mylogger.info('[handle]: reading {0} ...'.format(filepath))
		t1 = time.clock()
		data = readfile_asbinary_xmlrpc(filepath)
		mylogger.info('[handle]: reading finished'.format(filepath))
		mylogger.info('[handle]: time used {0}s'.format(time.clock()-t1))
		return SUCCESS,data

	def _broadcast(self,query,starturl,history):
		"""
		broadcast to all other nodes
		"""
		mylogger.info('-'*10)
		mylogger.info('[broadcast]:')
		mylogger.info("knows: {0}".format(self.known))
		mylogger.info("history: {0}".format(history))
		for other in self.known.copy():
			mylogger.info('[broadcast]: other is {0}'.format(other))
			if other in history:
				continue
			s = ServerProxy(other)
			mylogger.info('[broadcast]: Connecting from {0} to {1}'.format(self.url,other))
			mylogger.info('*'*80)
			try:
				code,data = s.query(query,starturl,history)
				mylogger.info('[broadcast]: query return code {0}'.format(code))
				if code == SUCCESS:
					mylogger.info('[broadcast]: query SUCCESS!!!')
					return code,data
				elif code == NOT_EXIST:
					mylogger.info('[broadcast]: query NOT_EXIST!!!')
				else:
					mylogger.info('[broadcast]: query ACCESS_DENIED!!!')
			except Fault, f: # connected to server,but method does not exist(Never happen in this example)
				mylogger.warn(f)
				mylogger.warn("[broadcast]:except fault")
			except socket.error, e:
				mylogger.warn("[broadcast]:except socket error")
				mylogger.error('[broadcast]: {0} for {1}'.format(e,other))
				# added by kzl
				self.known.remove(other)
				#mylogger.warn('[broadcast]: <knows>: {0}'.format(self.known))
				#mylogger.warn("[broadcast]: <history>: {0}".format(history))
			except Exception, e:
				mylogger.warn(e)
				mylogger.warn("[broadcast]: Exception")
		mylogger.info('[broadcast] not found')
		return NOT_EXIST,None

	"""
	node that we can list all available files in dirname
	"""
	def is_local_updated(self):
		"""
		whether local updated
		"""
		return self.event_update_local.is_set()

	def is_remote_updated(self):
		"""
		whether remote updated
		"""
		return self.event_update_remote.is_set()

	def clear_local_update(self):
		"""
		clear local update and set to false
		"""
		self.event_update_local.clear()

	def clear_remote_update(self):
		"""
		clear remote update and set to false
		"""
		self.event_update_remote.clear()

	def _trigger_update_local(self):
		"""
		trigger update local list event
		"""
		self.event_update_local.set()

	def _trigger_update_remote(self):
		"""
		trigger update remote list event
		"""
		self.event_update_remote.set()
		
	def _add(self,url):
		"""
		add url to myself's known set
		at the same time, list files in url
		[used in _read]
		"""
		mylogger.info('[_add]: adding {0}...'.format(url))
		self.known.add(url)
		if url == self.url:
			#mylogger.info("[_add]: call list_local 1")
			lt = self.list_local()
			if len(lt):
				self.local_files = lt
				self._trigger_update_local()
		else:
			#mylogger.info("[_add]: call list_other 2")
			lt = self.list_other(url)
			if len(lt):
				self.remote_files[url] = lt
				self._trigger_update_remote()

	def get_url(self):
		"""
		get url of local node
		"""
		mylogger.info('[get_url]: ')
		return self.url

	def get_remote_urls(self):
		"""
		get remote urls of local node
		"""
		mylogger.info('[get_remote_urls]: ')
		copy = self.known.copy()
		copy.remove(self.url)
		return list(copy)

	def add_node(self,other,otherfiles):
		"""
		add other to myself's known set
		add otherfiles to myself's remote_files
		[used in online]
		[used in list_other  SPECIAL!!!]
		"""
		if other in self.known:
			mylogger.info("{0} in known set".format(other))
			return
		mylogger.info('[add_node]: HELLO {0}'.format(other))
		self.known.add(other)
		if len(otherfiles):
			self.remote_files[other] = otherfiles
			self._trigger_update_remote()
		return True

	def remove_node(self,other,otherfiles=[]):
		"""
		remove other from myself's known set
		remove otherfiles from myself's remote_files
		[used in offline]
		"""
		mylogger.info('[remove_node]: BYEBYE {0}'.format(other))
		self.known.remove(other)
		if other in self.remote_files:
			del self.remote_files[other]
			self._trigger_update_remote()
		return True

	def get_local_files(self):
		"""
		return the newest local_files
		"""
		return self.local_files

	def get_remote_files(self):
		"""
		return the newest remote_files
		"""
		return self.remote_files

	def fetch_with_cache(self,query,secret):
		"""
		fetch a given file from current local_files and remote_files
		query:  filepath
		"""
		return True

	def online(self):
		"""
		inform others about myself's status(on)
		"""
		mylogger.info('[online]')
		for other in self.known.copy():
			if other == self.url:
				continue
			s = ServerProxy(other)
			try:
				# inform other node to add local node 
				files = self.get_local_files()
				s.add_node(self.url,files)
			except Fault,f:
				mylogger.warn(f)
				mylogger.warn('[online]: {0} started but inform failed'.format(other))
			except socket.error,e:
				mylogger.error('[online]: {0} for {1}'.format(e,other))
				#mylogger.warn('[online]: {0} not started'.format(other))
			except Exception, e:
				mylogger.warn(e)
				mylogger.warn("[online]: Exception")
		return True
	
	def offline(self):
		"""
		inform others about myself's status(off)
		"""
		mylogger.info('[offline]')
		for other in self.known.copy():
			if other == self.url:
				continue
			s = ServerProxy(other)
			try:
				# inform other node to remove local node 
				s.remove_node(self.url)
			except Fault,f:
				mylogger.warn(f)
				mylogger.warn('[offline]: {0} started but inform failed'.format(other))
			except socket.error,e:
				mylogger.error('[offline]: {0} for {1}'.format(e,other))
				#mylogger.warn('[offline]: {0} not started'.format(other))
			except Exception, e:
				mylogger.warn(e)
				mylogger.warn("[online]: Exception")
		return True

	def list_local(self):
		"""
		list files in local node
		"""
		mylogger.info('[list_local]: list files in {0}'.format(self.url))
		return list_all_files(self.dirname)
	
	def list_other(self,other):
		"""
		list files in other node
		"""
		mylogger.info('[list_other]: list files in {0}'.format(other))
		lt = []
		s = ServerProxy(other)
		try:
			#mylogger.info("[list_other]: call list_local 3")
			# since we connect to other,introduce self.url to other
			# inform other node to add local node 
			files = self.get_local_files()
			s.add_node(self.url,files)
			# introduce self.url to other
			lt = s.list_local()
		except Fault,f:
			mylogger.warn(f)
			mylogger.warn('[list_other]: {0} started but list failed'.format(other))
		except socket.error,e:
			mylogger.error('[list_other]: {0} for {1}'.format(e,other))
			#mylogger.warn('[list_other]: {0} not started'.format(other))
		except Exception, e:
			mylogger.warn(e)
			mylogger.warn("[online]: Exception")
		finally:
			return lt

	def update_local_list(self):
		"""
		update method
		list all files in local node
		"""
		mylogger.info('[update_local_list]: update local list')
		temp = self.list_local()
		if not list_equal(temp,self.local_files):
			self.local_files = temp
			self._trigger_update_local()
		return True

	def update_remote_list(self):
		"""
		update method
		list all files in remote nodes
		"""
		mylogger.info('[update_remote_list]: update remote list')
		for other in self.known.copy():
			if other == self.url:
				continue
			else:
				lt = self.list_other(other)
				if other in self.remote_files:
					if not list_equal(lt,self.remote_files[other]):
						self.remote_files[other]= lt
						if not len(lt):
							del self.remote_files[other]
						self._trigger_update_remote()
				elif len(lt):# k not in dict
					self.remote_files[other]= lt
					self._trigger_update_remote()
		return True

def main():
	n = Node('http://192.169.1.200','share/','','ips.txt',Event(),Event())
	n._start()

if __name__ =='__main__':
	main()
