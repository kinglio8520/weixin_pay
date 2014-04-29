from django.conf.urls import patterns, url

urlpatterns = patterns('wxpay.views',
   url(r'^payable/(?P<payment_no>p?[0-9]+)', 'payable'),
   url(r'^payment_notify', 'payment_notify'),
   url(r'^warning_notify', 'warning_notify'),
   url(r'^right_notify', 'right_notify'),
   url(r'^address_sign', 'get_address_data')
)
