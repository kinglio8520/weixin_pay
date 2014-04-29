from datetime import date
import logging
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
import time
from django.utils.encoding import smart_str, smart_unicode
from django.views.decorators.csrf import csrf_exempt
from orders.notify import send_wechat_right_notify_mail, send_wechat_warning_notify_mail
from rest_framework.decorators import api_view
from orders.models import Payment
from payments import payment_form_tpl
import json
from rest_framework.response import Response
from wxpay.wxlib import verify_notify, build_form, xml_to_dict, deliver_notify, random_str, build_warning_sign, build_right_sign, get_address_sign
from django.utils.translation import ugettext_lazy as _
from orders.models import Payment
from rest_framework import status


logger = logging.getLogger('payment')


def payment_error(errMsg):
    return render_to_response('payment_error.html', {'errMsg': errMsg})


def payment_notify(request):
    params = request.GET
    raw_str = request.body
    if params:
        logger.info('Wechat Verifying Payment for Request: %s' % unicode(params))
        logger.info('Wechat Xml Append with Request: %s' % unicode(raw_str))
        verifyResult = verify_notify(params)
        if verifyResult:
            wechat_data = xml_to_dict(raw_str)
            out_trade_no = params['out_trade_no']
            total_fee = int(params['total_fee'])
            trade_state = params['trade_state']
            logger.info('Wechat Payment Verify Succeeded! The trade state is %s' % trade_state)

            if trade_state == '0':
                timestamp = int(time.time())
                parameters = {
                    'openid': wechat_data['OpenId'],
                    'transid': params['transaction_id'],
                    'out_trade_no': out_trade_no,
                    'deliver_timestamp': str(timestamp),
                    'deliver_status': '1',
                    'deliver_msg': 'ok',
                }
                result = deliver_notify(parameters)
                if result['errcode'] == 0:
                    logger.info('Wechat Delivery Notify Succeeded!')
                    payment = Payment.objects.get(payment_no=out_trade_no)
                    payment.confirm(float(total_fee/100.00))
                    return HttpResponse('success')
                else:
                    logger.error('Wechat Delivery Notify Failed: %s' % result['errmsg'])
                    return HttpResponse('Delivery Notify Failed!', status=400)
            else:
                logger.error('Trade State != 0')
                return HttpResponse('success')
        else:
            logger.error('Wechat Payment Verify Failed!')
            return HttpResponse('Verify Result Failed', status=400)
    else:
        logger.error('Missing Post Parameters')
        return HttpResponse('Missing Post Parameters', status=400)


@api_view(['GET'])
def payable(request, payment_no):
    payment = Payment.objects.get(payment_no=payment_no)
    if not payment.is_payable:
        return Response({'detail': _('Already Paid')}, status=status.HTTP_400_BAD_REQUEST)

    parameter = {
        'body': payment.comment,
        'out_trade_no': payment.payment_no,
        'spbill_create_ip': request.META.get('REMOTE_ADDR', ''),
        'total_fee': str(int(payment.amount*100)),  # unit is fen check other day
        'notify_url': 'http://%s/wxpay/payment_notify/' % request.META['HTTP_HOST']
    }
    return Response(build_form(parameter))


def warning_notify(request):
    raw_str = request.body
    logger.info('Warning Notify Wechat Xml Append with Request: %s' % unicode(raw_str))
    wechat_data = xml_to_dict(raw_str)
    parameters = {key.lower(): wechat_data[key] for key in wechat_data}
    # if build_warning_sign(parameters) == wechat_data['AppSignature']:
    send_wechat_warning_notify_mail(wechat_data)
    return HttpResponse('success')
    # else:
    #     logger.error('Wechat Warning Notify Verify Failed!')
    #     return HttpResponse('error')


def right_notify(request):
    raw_str = request.body
    logger.info('Right Notify Wechat Xml Append with Request: %s' % unicode(raw_str))
    wechat_data = xml_to_dict(raw_str)
    parameters = {key.lower(): wechat_data[key] for key in wechat_data}
    if build_right_sign(parameters) == wechat_data['AppSignature']:
        send_wechat_right_notify_mail(wechat_data)
        return HttpResponse('success')
    else:
        logger.error('Wechat Right Notify Verify Failed!')
        return HttpResponse('error')

@api_view(['GET'])
def get_address_data(request):
    params = {'accesstoken': request.QUERY_PARAMS.get('accesstoken'), 'url': request.META['HTTP_HOST'] + request.path}
    result = get_address_sign(params)
    return Response(result)