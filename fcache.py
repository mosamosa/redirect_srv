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
import threading
import Queue

## 問い合わせ中例外
class Queried(Exception):
	pass

## エラー例外
class Error(Exception):
	def __init__(self, msg):
		self.msg = msg

## 非同期ファイルキャッシュクラス
class AyncFileCache:
	## コンストラクタ
	# @param self
	# @param maxfsize キャッシュする最大ファイルサイズ (byte)
	# @param maxtotal 最大総キャッシュサイズ (byte)
	# @param cintval ファイル更新チェック間隔 (sec)
	# @param minTTL 最小キャッシュ生存時間 (sec)
	# @param maxTTL 最大キャッシュ生存時間 (sec)
	def __init__(self, maxfsize, maxtotal, cintval, minTTL, maxTTL):
		self.settings(maxfsize, maxtotal, cintval, minTTL, maxTTL)
		self.lock = threading.RLock()
		self.cache = {}
		self.qRead = Queue.Queue()
		self.thReadTerminate = False
		self.thRead = threading.Thread(target=AyncFileCache.readThread, args=(self,))
	
	## 設定
	# @param self
	# @param maxfsize キャッシュする最大ファイルサイズ (byte)
	# @param maxtotal 最大総キャッシュサイズ (byte)
	# @param cintval ファイル更新チェック間隔 (sec)
	# @param minTTL 最小キャッシュ生存時間 (sec)
	# @param maxTTL 最大キャッシュ生存時間 (sec)
	def settings(self, maxfsize = None, maxtotal = None, cintval = None, minTTL = None, maxTTL = None):
		if maxfsize is not None:
			self.maxfsize = maxfsize
		if maxtotal is not None:
			self.maxtotal = maxtotal
		if cintval is not None:
			self.cintval = cintval
		if minTTL is not None:
			self.minTTL = minTTL
		if maxTTL is not None:
			self.maxTTL = maxTTL
	
	## 初期化処理
	# @param self
	def initialize(self):
		if not self.thRead.isAlive():
			self.thReadTerminate = False
			self.thRead.start()
	
	## 終了処理
	# @param self
	def finalize(self):
		if self.thRead.isAlive():
			self.thReadTerminate = True
			self.thRead.join()
	
	## ファイルデータ取得
	# @param self
	# @param fname ファイル名
	def get(self, fname):
		with self.lock:
			if fname in self.cache:
				self.cache[fname]['atime'] = time.time()
				
				# 処理中判定
				if self.cache[fname]['lock']:
					raise Queried()
				
				# 再チェック判定
				if abs(time.time() - self.cache[fname]['ctime']) >= self.cintval:
					self.cache[fname]['lock'] = True
					self.qRead.put(fname)
					raise Queried()
				
				# エラー判定
				if self.cache[fname]['err']:
					raise Error(self.cache[fname]['errMsg'])
				
				return self.cache[fname]['data']
				
			else:
				self.cache[fname] = {'ctime': 0, 'atime': 0, 'mtime': 0, 'data': None, 'err': False, 'errMsg': '', 'lock': False}
				
				# 新規ファイル
				self.cache[fname]['atime'] = time.time()
				self.cache[fname]['lock'] = True
				self.qRead.put(fname)
				raise Queried()
	
	## キャッシュクリア
	# @param self
	def clear(self):
		with self.lock:
			self.cache = {}
	
	## 総キャッシュサイズ削減
	# @param self
	# @param padding 水増しサイズ (byte)
	# @param maxtotal 最大総キャッシュサイズ (bytes)
	# @param ignore 除外するファイル名のリスト
	# @return maxtotal 以下のサイズに削減できたか否か
	def trim(self, padding = 0, maxtotal = None, ignore = None):
		if maxtotal is None:
			maxtotal = self.maxtotal
		
		if ignore is None:
			ignore = set()
		else:
			ignore = set(ignore)
		
		crrtime = time.time()
		total = padding
		
		with self.lock:
			# キーをアクセス時間の降順にソート
			fnames = [(fname, self.cache[fname]['atime']) for fname in self.cache]
			fnames = [fname[0] for fname in sorted(fnames, lambda a, b: b[1] - a[1])]
			abandon = []
			
			# 総サイズを超えたものを古い順に列挙
			for fname in fnames:
				if fname in ignore:
					continue
				
				size = len(self.cache[fname]['data']) if self.cache[fname]['data'] is not None else 0
				total += size
				
				# ロックされているか、最小生存時間以下のものは削除しない
				if self.cache[fname]['lock'] or abs(crrtime - self.cache[fname]['atime']) <= self.minTTL:
					continue
				
				if size > 0 and total > maxtotal:
					total -= size
					abandon.append(fname)
			
			# 列挙したものを削除
			for fname in abandon:
				del self.cache[fname]
		
		return not (total > maxtotal)
	
	## 読み込みスレッド
	# @param self
	@staticmethod
	def readThread(self):
		ctime = time.time()
		
		while not self.thReadTerminate:
			try:
				# ファイル読み込みキュー待ち
				err = False
				errMsg = ''
				fname = self.qRead.get(timeout=0.1)
				
				try:
					fstat = os.stat(fname)
					
					if fstat.st_size > self.maxfsize:
						# ファイルが大きすぎる
						err = True
						errMsg = 'File size too large. (%d bytes)' % fstat.st_size
					else:
						# ファイル更新チェック
						with self.lock:
							mtime = self.cache[fname]['mtime']
							fsize = len(self.cache[fname]['data']) if self.cache[fname]['data'] is not None else None
						
						if mtime != fstat.st_mtime or fsize is None or fsize != fstat.st_size:
							# ファイル更新あり
							if self.trim(fstat.st_size, ignore=[fname]):
								data = open(fname, 'rb').read()
								
								# ファイル読み込み成功
								with self.lock:
									self.cache[fname]['ctime'] = time.time()
									self.cache[fname]['mtime'] = fstat.st_mtime
									self.cache[fname]['data'] = data
									self.cache[fname]['err'] = False
									self.cache[fname]['errMsg'] = ''
									self.cache[fname]['lock'] = False
							else:
								# 最大総キャッシュサイズ超過
								err = True
								errMsg = 'Cache full.'
						else:
							# ファイル更新なし
							with self.lock:
								self.cache[fname]['ctime'] = time.time()
								self.cache[fname]['err'] = False
								self.cache[fname]['errMsg'] = ''
								self.cache[fname]['lock'] = False
				except:
					# ファイルが見つからない
					with self.lock:
						self.cache[fname]['ctime'] = time.time()
						self.cache[fname]['mtime'] = 0
						self.cache[fname]['data'] = None
						self.cache[fname]['err'] = False
						self.cache[fname]['errMsg'] = ''
						self.cache[fname]['lock'] = False
				
				if err:
					# エラー
					with self.lock:
						self.cache[fname]['ctime'] = time.time()
						self.cache[fname]['mtime'] = 0
						self.cache[fname]['data'] = None
						self.cache[fname]['err'] = True
						self.cache[fname]['errMsg'] = errMsg
						self.cache[fname]['lock'] = False
				
			except Queue.Empty:
				pass
			
			crrtime = time.time()
			
			# 生存時間超過処理
			if abs(crrtime - ctime) >= 1:
				abandon = []
				
				with self.lock:
					# 最大生存時間を超過した物を列挙
					for fname in self.cache:
						if self.cache[fname]['lock']:
							continue
						if abs(crrtime - self.cache[fname]['atime']) >= self.maxTTL:
							abandon.append(fname)
					
					# 列挙したものを削除
					for fname in abandon:
						del self.cache[fname]
				
				ctime = crrtime
