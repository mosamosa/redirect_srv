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

import re
import copy
import time
import datetime
import locale

# for getApacheLogDatetime function
locale.setlocale(locale.LC_ALL, 'C')

## GLOB風ワイルドカードを正規表現に変換する
# @param wc GLOB風ワイルドカード
# @return 正規表現文字列
def wc2re(wc):
	ret = wc
	ret = re.sub(r'\*{2}[/\\]', 'xyzanydirzyx',  ret)
	ret = re.sub(r'\*',         'xyzanyfilezyx', ret)
	ret = re.sub(r'\?',         'xyzanycharzyx', ret)
	ret = re.escape(ret)
	ret = ret.replace('xyzanydirzyx',  r'([^/\\]+[/\\])*')
	ret = ret.replace('xyzanyfilezyx', r'[^/\\]*')
	ret = ret.replace('xyzanycharzyx', r'[^/\\]')
	ret = '^' + ret + '$'
	return ret

## 不正パスチェック
# @param path パス
# @return チェック結果
def pathCheck(path):
	if re.search(r'\.\.[/\\]', path):
		return False
	else:
		return True

## ネイティブタイムゾーンのクラスを作成する
# @param クラス名
# @return タイムゾーンクラス
def createNativeTZ(name):
	tt = time.time()
	tlocal = datetime.datetime.fromtimestamp(tt)
	tutc   = datetime.datetime.utcfromtimestamp(tt)
	diff = tlocal - tutc
	
	class TempTZ(datetime.tzinfo):
		def utcoffset(self,dt):
			return diff
		def dst(self,dt):
			return datetime.timedelta(0)
		def tzname(self,dt):
			return 'Native'
	
	TempTZ.__name__ = name
	
	return TempTZ

# ネイティブタイムゾーンクラス作成
NativeTZ = createNativeTZ('NativeTZ')

## Apacheログ形式のタイムスタンプを作成する
# @param timestamp UNIX時間
# @return タイムスタンプ文字列
def getApacheLogDatetime(timestamp = None):
	if timestamp is None:
		timestamp = time.time()
	
	dt = datetime.datetime.fromtimestamp(timestamp, NativeTZ())
	
	return dt.strftime('%d/%b/%Y:%H:%M:%S %z')

## 出現比率に応じた数列を発生させる Generator を作成する
# @param ratio 比率のリスト
# @return 数列を発生させる Generator
def occuRatioSequence(ratio):
	if len(ratio) == 1:
		while True:
			yield 0
	
	total = float(sum(ratio))
	ratio = [total / x for x in ratio]
	
	unit = min(ratio) / len(ratio)
	offset = max(ratio) / (len(ratio) - 1)
	
	ratio = [(i, x) for i, x in enumerate(ratio)]
	ratio.sort(lambda a, b: -1 if a[1] - b[1] < 0 else 1 if a[1] - b[1] > 0 else 0)
	
	index = [x[0] for x in ratio]
	ratio = [x[1] for x in ratio]
	
	ramp = [(i * offset) % ratio[i] for i, x in enumerate(ratio)]
	
	while True:
		ramp = [x + unit for x in ramp]
		seq = [index[i] for i, x in enumerate(ramp) if x >= ratio[i]]
		ramp = [x - ratio[i] if x >= ratio[i] else x for i, x in enumerate(ramp)]
		
		for x in seq:
			yield x

## config.REDIRECT_TABLEの整形
# @param redirTable config.REDIRECT_TABLE
# @return fixed config.REDIRECT_TABLE
def fixRedirectTable(redirTable):
	redirTable = copy.deepcopy(redirTable)
	
	for redir in redirTable:
		redir['pattern'] = [re.compile(wc2re(x)) for x in redir['pattern']]
		redir['to'] = [x for x in redir['to'] if x['weight'] != 0]
		
		for redirTo in redir['to']:
			redirTo['weight'] = abs(redirTo['weight'])
		
		redir['seq'] = {}
	
	return redirTable

## リダイレクト先を選択する
# @param path リクエストパス
# @param redirTable fixed config.REDIRECT_TABLE
# @param disableSelfHost このサーバからのファイル転送を無効化する
# @return リダイレクト先URL
def selRedirectTo(path, redirTable, disableSelfHost = False):
	for redir in redirTable:
		found = False
		
		for ptn in redir['pattern']:
			if ptn.match(path):
				found = True
				break
		
		if found:
			redirTo = [x for x in redir['to'] if not disableSelfHost or x['base_url'] != '']
			
			if len(redirTo) >= 1:
				ratio = tuple(x['weight'] for x in redirTo)
				
				if ratio not in redir['seq']:
					redir['seq'][ratio] = occuRatioSequence(ratio)
				
				return redirTo[redir['seq'][ratio].next()]['base_url']
			
			break
	
	return None
