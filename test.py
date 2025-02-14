# encoding:utf-8

import requests
import base64

'''
公式识别
'''

request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/formula"
# 二进制方式打开图片文件
f = open('/Users/yanjiajun/Desktop/screenshot.png', 'rb')
img = base64.b64encode(f.read())

params = {"image":img}
access_token = '24.694faa7fc56d3b920fddfe6e0e007ee6.2592000.1732008710.282335-115929953'
request_url = request_url + "?access_token=" + access_token
headers = {'content-type': 'application/x-www-form-urlencoded'}
response = requests.post(request_url, data=params, headers=headers)
if response:
    print (response.json())