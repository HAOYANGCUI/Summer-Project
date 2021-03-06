#coding:utf-8

import requests
import json
import time

class weibo:
	def __init__(self, username, password):
		self.__username = username
		self.__password = password
		try:
			self.cookies = self.__login__().cookies
			self.status = True
		except:
			self.cookies = None
			self.status = False

	def __login__(self):
		url = r'https://passport.weibo.cn/sso/login'
		header = {
			'Host':'passport.weibo.cn',
			'User-Agent':'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A403 Safari/8536.25',
			'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language':'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
			'Accept-Encoding':'gzip, deflate',
			'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
			'Pragma':'no-cache',
			'Cache-Control':'no-cache',
			'Referer':'https://passport.weibo.cn/signin/login',
			'Connection':'keep-alive'}
		post_data = {
			'username':'%s' % self.__username,
			'password':'%s' % self.__password,
			'savestate':'1',
			'ec':'0',
			'pagerefer':'',
			'entry':'mweibo',
			'loginfrom':'',
			'client_id':'',
			'code':'',
			'qq':'',
			'hff':'',
			'hfp':''}
		try:
			response = requests.post(url, data = post_data, headers = header)
			print u'登陆成功\nuid:'+json.loads(response.text)['data']['uid']
			return response
		except:
			print u'登录失败'
			return None

	def update(self, text):
		url = r'http://m.weibo.cn/mblogDeal/addAMblog'

		header = {
			'Host':'m.weibo.cn',
			'User-Agent':'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A403 Safari/8536.25',
			'Accept':'application/json, text/javascript, */*; q=0.01',
			'Accept-Language':'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
			'Accept-Encoding':'gzip, deflate',
			'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
			'X-Requested-With':'XMLHttpRequest',
			'Referer':'http://m.weibo.cn/mblog',
			'Connection':'keep-alive'
		}

		post_data = {
			'content':text
		}
		try:
			response = requests.post(url = url, data = post_data, headers = header, cookies = self.cookies)
			print json.loads(response.text)['msg']
			return response
		except:
			try:
				time.sleep(10)
				try:
					self.cookies = self.__login__().cookies
				except:
					self.cookies = None
					return None
				response = requests.post(url = url, data = post_data, headers = header, cookies = self.cookies)
				print json.loads(response.text)['msg']
				return response
			except:
				print u'发送失败'
				return None

if __name__ == '__main__':
	username = '0061404613526'
	password = '241205weibo'
	w = weibo(username, password)
	w.update('DANGER')
	
