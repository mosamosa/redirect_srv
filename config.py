# -*- coding: utf-8 -*-

## サーバポート番号
SERVER_PORT = 8080

## ファイルチェック間隔 (sec)
FILE_CHECK_INTERVAL = 60

## 最小キャッシュ生存時間 (sec)
MIN_CACHE_TTL = 60

## 最大キャッシュ生存時間 (sec)
MAX_CACHE_TTL = 600

## 最大キャッシュ可能ファイルサイズ (byte)
CACHE_MAX_FILE_SIZE = 1000000

## 最大総キャッシュサイズ (byte)
CACHE_MAX_TOTAL_SIZE = 100000000

## ルートディレクトリ
ROOT_DIR = r'htdocs'

## ログディレクトリ
LOG_DIR = r'logs'

## アクセスログファイル名形式
ACCESS_LOG_FILENAME_FORMAT = 'access_log_%Y%m%d.log'

## 管理者ID
ADMIN_USERID = 'admin'

## 管理者パスワード
ADMIN_PASSWD = 'changeme'

## リダイレクト設定
# 上から順にパターンマッチが行われ、weight の比率でリダイレクト先が決定されます
#
# weight について：
#   リダイレクト先は weight の比率によって決定されます
#   例：{'weight': 100, ...}, {'weight': 100, ...}, {'weight':  50, ...}
#     以上のような設定の場合、100:100:50 -> 2:2:1 の割合でリダイレクトされます
#     以下ののような設定も値の大小は関係なく、比率のみ考慮されるため上記と同じ結果になります
#       {'weight': 0.4, ...}, {'weight': 0.4, ...}, {'weight': 0.2, ...}
#
# base_url について：
#   空文字列の base_url はこのサーバ自身を表します
#   ファイルを ROOT_DIR ディレクトリ配下から読み込み、このサーバから送信されます
#   CACHE_MAX_FILE_SIZEを超えるなどキャッシュ不可能な場合は他のサーバにリダイレクトされます
#   この場合、サーバ自身の weight を除いた比率でリダイレクト先が決定されます
#
# pattern について：
#     「*」：空文字列を含む任意の文字列と一致します。(「/」などパス区切り文字を含まない)
#     「?」：任意の一文字と一致します。(「/」などパス区切り文字を含まない)
#   「**/」：ワイルドカード「*/」の0回以上の繰り返しを意味し、 ディレクトリを再帰的にたどってマッチを行います
#            例えば, foo/**/bar は foo/bar, foo/*/bar, foo/*/*/bar ... (以下無限に続く)に対してそれぞれ マッチ判定を行います
#
# 例：
#REDIRECT_TABLE = [
#	{
#		'pattern': ['/tf2/sound/**/*', '/tf2/*'],			# /tf2/sound/ 配下のファイルすべてと、 /tf2/ 直下のファイルにマッチします
#		'to': [
#			{'weight': 100, 'base_url': ''},				# 通常時は foo.com と bar.com には殆どリダイレクトされず、このサーバから直接ファイル送信されます
#			{'weight':	 4, 'base_url': 'http://foo.com/'}, # CACHE_MAX_TOTAL_SIZE を超過した場合など、このサーバから直接ファイル送信できない場合は、
#			{'weight':	 2, 'base_url': 'http://bar.com/'}, # foo.com と bar.com へ 2：1の割合でリダイレクトされます
#		]
#	},
#	{
#		'pattern': ['/tf2/maps/**/*'],						# /tf2/maps/ 配下のファイルすべてとマッチします
#		'to': [
#			{'weight': 100, 'base_url': 'http://foo.com/'}, # foo.com と bar.com 均等にリダイレクトが行われます
#			{'weight': 100, 'base_url': 'http://bar.com/'}, # 
#		]
#	},
#	{
#		'pattern': ['/**/*'],								# 上記以外のファイルすべてとマッチします
#		'to': [
#			{'weight': 100, 'base_url': 'http://foo.com/'}, # foo.com にのみリダイレクトが行われます
#			{'weight':	 0, 'base_url': 'http://bar.com/'}, # 
#		]
#	},
#]
REDIRECT_TABLE = [
	{
		'pattern': ['/tf2/sound/**/*', '/tf2/*'],			# /tf2/sound/ 配下のファイルすべてと、 /tf2/ 直下のファイルにマッチします
		'to': [
			{'weight': 100, 'base_url': ''},				# 通常時は foo.com と bar.com には殆どリダイレクトされず、このサーバから直接ファイル送信されます
			{'weight':	 4, 'base_url': 'http://foo.com/'}, # CACHE_MAX_TOTAL_SIZE を超過した場合など、このサーバから直接ファイル送信できない場合は、
			{'weight':	 2, 'base_url': 'http://bar.com/'}, # foo.com と bar.com へ 2：1の割合でリダイレクトされます
		]
	},
	{
		'pattern': ['/tf2/maps/**/*'],						# /tf2/maps/ 配下のファイルすべてとマッチします
		'to': [
			{'weight': 100, 'base_url': 'http://foo.com/'}, # foo.com と bar.com 均等にリダイレクトが行われます
			{'weight': 100, 'base_url': 'http://bar.com/'}, # 
		]
	},
	{
		'pattern': ['/**/*'],								# 上記以外のファイルすべてとマッチします
		'to': [
			{'weight': 100, 'base_url': 'http://foo.com/'}, # foo.com にのみリダイレクトが行われます
			{'weight':	 0, 'base_url': 'http://bar.com/'}, # 
		]
	},
]
