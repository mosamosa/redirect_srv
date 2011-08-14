# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mosamosa (pcyp4g@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import time
import datetime
import base64
import tornado.ioloop
import tornado.web
import fcache
import alog
import tools
import config

## 設定ファイルの再読み込み
def reloadConf():
	global redirect_table
	
	reload(config)
	redirect_table = tools.fixRedirectTable(config.REDIRECT_TABLE)
	
	afcache.settings(
		maxfsize=config.CACHE_MAX_FILE_SIZE,
		maxtotal=config.CACHE_MAX_TOTAL_SIZE,
		cintval=config.FILE_CHECK_INTERVAL,
		minTTL=config.MAX_CACHE_TTL,
		maxTTL=config.MAX_CACHE_TTL
	)

## ログ出力付き RequestHandler
class BaseHandler(tornado.web.RequestHandler):
	## コンストラクタ
	# @param self
	def __init__(self, *args, **kwargs):
		tornado.web.RequestHandler.__init__(self, *args, **kwargs)
		self.logs = []
	
	## finish メソッドオーバーライド
	# @param self
	# @param chunk see RequestHandler.chunk
	# @return      see RequestHandler.chunk
	def finish(self, chunk=None):
		ret = tornado.web.RequestHandler.finish(self, chunk)
		
		# ログ出力
		tt = time.time()
		logStr = self.generateApacheLog(tt)
		
		if len(self.logs) > 0:
			logStr += ' "%s"' % ';'.join(self.logs)
		
		logName = datetime.datetime.fromtimestamp(tt).strftime(config.ACCESS_LOG_FILENAME_FORMAT)
		logFile.puts(os.path.join(config.LOG_DIR, logName), logStr)
		
		return ret
	
	## BASIC認証のユーザ名とパスワードを返す
	# @param self
	# @return (ユーザ名, パスワード) 失敗した場合は None
	def getBasicAuthInfo(self):
		try:
			auth = self.request.headers['Authorization'].split(' ')
			if auth[0] == 'Basic' and len(auth) == 2:
				try:
					info =  base64.b64decode(auth[1]).split(':')
					if len(info) == 2:
						return (info[0].strip(), info[1].strip())
				except TypeError:
					pass
		except KeyError:
			pass
		
		return None
	
	## BASIC認証を行う
	# @param self
	# @param realm ブラウザのダイアログボックス上に表示される文字列
	# @param cb 認証コールバック関数 (lambda info: info[0] == USER and info[1] == PASS)
	# @return 認証結果
	def basicAuth(self, realm, cb):
		info = self.getBasicAuthInfo()
		
		if info is not None and cb(info):
			return True
		
		self.set_status(401)
		self.set_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
		
		return False
	
	## Combine形式のログを作成すする
	# @param self
	# @param tt UNIX時間
	# @return ログ文字列
	def generateApacheLog(self, tt):
		try:    contentLength = int(self._headers['Content-Length'])
		except: contentLength = 0
		try:    referer = self.request.headers['Referer']
		except: referer = ''
		try:    userAgent = self.request.headers['User-Agent']
		except: userAgent = ''
		
		authInfo = self.getBasicAuthInfo()
		
		return '%s - %s [%s] "%s %s %s" %d %d "%s" "%s"' % (
			self.request.remote_ip,
			authInfo[0] if authInfo is not None and authInfo[0] != '' else '-',
			tools.getApacheLogDatetime(tt),
			self.request.method,
			self.request.uri,
			self.request.version,
			self.get_status(),
			contentLength,
			referer,
			userAgent
		)

## 制御リクエストハンドラ
class ControlHandler(BaseHandler):
	## GET
	# @param self
	def get(self):
		judge = lambda info: info[0] == config.ADMIN_USERID and info[1] == config.ADMIN_PASSWD
		
		# 設定再読込
		if self.request.path == '/!reload':
			if self.basicAuth('Admin only', judge):
				reloadConf()
				self.write('Reload succeed. (%s)' % tools.getApacheLogDatetime(time.time()))
		
		# キャッシュクリア
		if self.request.path == '/!clear':
			if self.basicAuth('Admin only', judge):
				afcache.clear()
				self.write('Cache clear succeed. (%s)' % tools.getApacheLogDatetime(time.time()))
		
		# 終了
		if self.request.path == '/!exit':
			if self.basicAuth('Admin only', judge):
				tornado.ioloop.IOLoop.instance().stop()

## 通常リクエストハンドラ
class MainHandler(BaseHandler):
	## ファイル読み込み・書き出し処理
	# @param self
	# @param path ファイルパス
	def getFile(self, path):
		try:
			# ファイル書き出し
			data = afcache.get(path)
			if data is not None:
				self.set_header('Content-Type', 'application/octet-stream')
				self.set_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(path))
				self.set_header('Content-Transfer-Encoding', 'binary')
				self.set_header('Expires', 0)
				self.set_header('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
				self.set_header('Pragma', 'public')
				self.write(data)
				self.finish()
			else:
				# ファイルが見つからない
				self.set_status(404)
				self.finish()
		except fcache.Queried:
			# ファイル読込中リトライ
			tornado.ioloop.IOLoop.instance().add_callback(lambda: self.getFile(path))
		except fcache.Error, e:
			# ファイルサイズ制限超過などのエラー
			self.logs.append('[WARN] Cache error. [%s] (%s)' % (e.msg, path))
			self.getRequest(True)
	
	## GET処理本体
	# @param self
	# @param disableSelfHost このサーバからのファイル転送を無効化する
	def getRequest(self, disableSelfHost):
		# パスチェック
		if not tools.pathCheck(self.request.path):
			# パスが不正
			self.set_status(404)
			self.finish()
			return
		
		# リダイレクト先決定
		baseUrl = tools.selRedirectTo(self.request.path, redirect_table, disableSelfHost)
		if baseUrl is None:
			# リダイレクト先が見つからない
			self.logs.append('[ERROR] Not redirect anywhere. (%s)' % self.request.path)
			self.set_status(500)
			self.finish()
		elif baseUrl == '':
			# ファイル送信
			path = os.path.join(config.ROOT_DIR.replace('/', '\\'), self.request.path.replace('/', '\\').lstrip('\\'))
			self.getFile(path)
		else:
			# リダイレクト
			url = baseUrl.rstrip('/') + self.request.path
			self.logs.append('[INFO] Redirect to: %s' % url)
			self.redirect(url)
	
	## GET
	# @param self
	@tornado.web.asynchronous
	def get(self):
		self.getRequest(False)

if __name__ == "__main__":
	# 初期化・起動
	application = tornado.web.Application([
		(r"/!.*", ControlHandler),
		(r".*", MainHandler),
	])

	logFile = alog.AsyncLogWriter()
	logFile.initialize()
	
	afcache = fcache.AyncFileCache(
		maxfsize=config.CACHE_MAX_FILE_SIZE,
		maxtotal=config.CACHE_MAX_TOTAL_SIZE,
		cintval=config.FILE_CHECK_INTERVAL,
		minTTL=config.MAX_CACHE_TTL,
		maxTTL=config.MAX_CACHE_TTL
	)
	afcache.initialize()
	
	redirect_table = {}
	reloadConf()
	
	application.listen(config.SERVER_PORT)
	tornado.ioloop.IOLoop.instance().start()
	
	afcache.finalize()
	logFile.finalize()
