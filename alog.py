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

import time
import threading
import Queue

## 非同期ログ出力クラス
class AsyncLogWriter:
	## コンストラクタ
	# @param self
	# @param ttl 使用していないファイルを閉じる時間 (秒単位)
	# @param checkInterval flushなどを行う間隔 (秒単位)
	def __init__(self, ttl = 60, checkInterval = 1):
		self.ttl = ttl
		self.checkInterval = checkInterval
		self.qLog = Queue.Queue()
		self.tLogTerminate = False
		self.tLog = threading.Thread(target=AsyncLogWriter.writeThread, args=(self,))
	
	## 初期化処理
	# @param self
	def initialize(self):
		if not self.tLog.isAlive():
			self.tLogTerminate = False
			self.tLog.start()
	
	## 終了処理
	# @param self
	def finalize(self):
		if self.tLog.isAlive():
			self.tLogTerminate = True
			self.tLog.join()
	
	## 書き込み要求
	# @param self
	# @param fname ファイル名
	# @param line 文字列
	def puts(self, fname, line):
		self.qLog.put((fname, line))
	
	## 書き込みスレッド
	# @param self
	@staticmethod
	def writeThread(self):
		ctime = time.time()
		finfo = {}
		
		while not self.tLogTerminate:
			try:
				# 書き込み要求待ち
				fname, line = self.qLog.get(timeout=0.1)
				
				if fname not in finfo:
					# ファイルを開く
					try:
						tmp = open(fname, 'a')
						finfo[fname] = {'fp': tmp, 'atime': time.time()}
					except IOError:
						finfo[fname] = {'fp': None, 'atime': time.time()}
				
				# 書き込み
				if finfo[fname]['fp'] is not None:
					finfo[fname]['fp'].write(line)
					finfo[fname]['fp'].write('\n')
					finfo[fname]['atime'] = time.time()
				
			except Queue.Empty:
				pass
			
			# 周期チェック
			crrtime = time.time()
			
			if abs(crrtime - ctime) >= self.checkInterval:
				abandon = []
				
				for fname in finfo:
					# flush
					if finfo[fname]['fp'] is not None:
						finfo[fname]['fp'].flush()
					
					# 使用していないファイルを列挙
					if abs(crrtime - finfo[fname]['atime']) >= self.ttl:
						abandon.append(fname)
				
				# 使用していないファイルを閉じる
				for fname in abandon:
					if finfo[fname]['fp'] is not None:
						finfo[fname]['fp'].close()
					
					del finfo[fname]
				
				ctime = crrtime
		
		# すべてのファイルを閉じる
		for fname in finfo:
			if finfo[fname]['fp'] is not None:
				finfo[fname]['fp'].close()
