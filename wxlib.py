# encoding=utf-8

import hashlib
import json
from random import Random
import urllib
import urllib2
import time
from django.utils.encoding import smart_str, smart_unicode
import xml.etree.ElementTree as ET

DELIVER_NOTIFY_URL = 'https://api.weixin.qq.com/pay/delivernotify'
ORDER_QUERY_URL = 'https://api.weixin.qq.com/pay/orderquery'
ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'

config = {
    'appId': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'appSecret': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'paySignKey': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'partnerId': 'xxxxxxxxxxxxxxxxxxxx',
    'partnerKey': 'xxxxxxxxxxxxxxxxxxxxxx'
}


def build_form(parameter):
    base = {
        'bank_type': 'WX',
        'fee_type': '1',
        'input_charset': 'UTF-8',
        'partner': config['partnerId']
    }
    parameter.update(base)
    parameter['package'] = build_package(parameter)
    timestamp = str(int(time.time()))
    noncestr = random_str()
    pay_sign_array = {
        'appid': config['appId'],
        'noncestr': noncestr,
        'package': parameter['package'],
        'timestamp': timestamp
    }
    pay_sign_array['paysign'] = build_sign(pay_sign_array)
    pay_sign_array['signtype'] = 'SHA1'
    del pay_sign_array['appkey']
    return pay_sign_array


def build_package(parameter):
    filterParameter = para_filter(parameter)
    filterKeys = filterParameter.keys()
    filterKeys.sort()
    joined_string = '&'.join(['%s=%s' % (key.lower(), unicode(filterParameter[key])) for key in filterKeys])
    joined_string += '&key=' + config['partnerKey']
    m = hashlib.md5(joined_string.encode('utf-8'))
    m.digest()
    sign = m.hexdigest().upper()
    package = '&'.join(
        ['%s=%s' % (key, urllib.quote(unicode(filterParameter[key]).encode('utf-8'))) for key in filterKeys])
    package += '&sign=' + sign
    return package


def para_filter(params):
    return {key: params[key]
            for key in params
            if key.lower() not in {'sign', 'sign_type'} and params[key]}


def verify_notify(params):
    wx_sign = params['sign']
    filterParams = para_filter(params)
    filterParams['sign_type'] = 'MD5'
    filterKeys = filterParams.keys()
    filterKeys.sort()
    joined_string = '&'.join(['%s=%s' % (key.lower(), unicode(filterParams[key])) for key in filterKeys])
    joined_string += '&key=' + config['partnerKey']
    m = hashlib.md5(joined_string.encode('utf-8'))
    m.digest()
    sign = m.hexdigest().upper()
    return wx_sign == sign


def build_sign(parameter):
    filter = ['appid', 'timestamp', 'noncestr', 'package', 'appkey']
    filter.sort()
    parameter['appkey'] = config['paySignKey']
    joined_string = '&'.join(['%s=%s' % (key.lower(), parameter[key]) for key in filter])
    sign = hashlib.sha1(joined_string).hexdigest()
    return sign


def build_delivery_sign(parameter):
    filter = ['appid', 'appkey', 'openid', 'transid', 'out_trade_no', 'deliver_timestamp', 'deliver_status',
              'deliver_msg']
    filter.sort()
    parameter['appkey'] = config['paySignKey']
    joined_string = '&'.join(['%s=%s' % (key.lower(), parameter[key]) for key in filter])
    sign = hashlib.sha1(joined_string).hexdigest()
    return sign


def build_right_sign(parameter):
    filter_key = ['appid', 'appkey', 'timestamp', 'openid']
    filter_key.sort()
    parameter['appkey'] = config['paySignKey']
    joined_string = '&'.join(['%s=%s' % (key.lower(), parameter[key]) for key in filter_key])
    sign = hashlib.sha1(joined_string).hexdigest()
    return sign


def build_warning_sign(parameter):
    filter_key = ['appid', 'appkey', 'timestamp']
    filter_key.sort()
    parameter['appkey'] = config['paySignKey']
    joined_string = '&'.join(['%s=%s' % (key.lower(), parameter[key]) for key in filter_key])
    sign = hashlib.sha1(joined_string).hexdigest()
    return sign


def get_access_token():
    token_url = ACCESS_TOKEN_URL + '?grant_type=client_credential&appid=' + config['appId'] + '&secret=' + config['appSecret']
    urlopen = urllib2.urlopen(token_url, timeout=12000)
    result = urlopen.read()
    data = json.loads(result)
    if 'errcode' in data:
        return False
    return data['access_token']


def deliver_notify(parameter):
    url = DELIVER_NOTIFY_URL + '?access_token=' + get_access_token()
    parameter['appid'] = config['appId']
    parameter['app_signature'] = build_delivery_sign(parameter)
    parameter['sign_method'] = 'sha1'
    del parameter['appkey']
    result = do_post(url, parameter)
    return json.loads(result)


def order_query(out_trade_no):
    if config != None or out_trade_no != None:
        return False
    url = ORDER_QUERY_URL + '?access_token=' + get_access_token()
    parameter = {
        'appid': config['appId'],
        'package': 'out_trade_no=' + out_trade_no +
                   '&partner=' + config['partnerId'] +
                   '&sign=' + (hashlib.md5('out_trade_no=' + out_trade_no +
                                           '&partner=' + config['partnerId'] +
                                           '&key=' + config['partnerkey'])).lower(),
        'timestamp': int(time.time())
    }
    app_signature = build_sign(parameter)
    parameter['app_signature'] = app_signature
    parameter['sign_method'] = 'sha1'
    result = do_post(url, parameter)
    return json.load(result)


def do_post(url, parameter):
    req = urllib2.Request(url)
    #enable cookie
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    response = opener.open(req, json.dumps(parameter))
    return response.read()


def random_str(randomlength=32):
    str = ''
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str += chars[random.randint(0, length)]
    return str


def xml_to_dict(raw_str):
    raw_str = smart_str(raw_str)
    msg = {}
    root_elem = ET.fromstring(raw_str)
    if root_elem.tag == 'xml':
        for child in root_elem:
            msg[child.tag] = smart_unicode(child.text)
        return msg
    else:
        return None


def get_address_sign(parameter):
    parameter['appid'] = config['appId']
    parameter['noncestr'] = random_str()
    parameter['timestamp'] = int(time.time())
    filter = ['appid', 'url', 'timestamp', 'noncestr', 'accesstoken']
    filter.sort()
    joined_string = '&'.join(['%s=%s' % (key.lower(), parameter[key]) for key in filter])
    sign = hashlib.sha1(joined_string).hexdigest()
    parameter['addrsign'] = sign
    parameter['scope'] = 'jsapi_address'
    parameter['signType'] = 'SHA1'
    return parameter