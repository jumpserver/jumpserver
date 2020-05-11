'''
这是work_form的视图配置文件
'''

from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# Create your views here.
from .models import *
from . import models
from datetime import datetime

import pymongo
from bson.json_util import dumps
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from django.contrib.auth.decorators import login_required

@login_required
def service_msg(request):
    if request.method == "POST":
        ###########################
        phoneno =  str(request.POST.get("phoneno")).strip()        # 1: 要查询的手机号码

        conn =  pymongo.MongoClient('103.244.234.57', port = 27017, )

        # 一：查询医药实名认证信息(查询RealNameAuthentication库,获取医药实名认证信息)
        realname_list =  []
        dbRealNameAuthentication =  conn.RealNameAuthentication
        for a in dbRealNameAuthentication.UserIdentity.find({"IdentityId": phoneno}):
            if a['AccountId']['AccountType'] == 'MedPerson':
                realname_detail = {}
                realname_detail['AccountType'] = a['AccountId']['AccountType']
                realname_detail['Key'] = a['AccountId']['Key']
                realname_detail['IdentityType'] = a['IdentityType']
                realname_detail['IdentityId'] = a['IdentityId']
                realname_list.append(realname_detail)

        # 三: 发送记录查询
        # Biz_id是当万方请求阿里云,阿里云回给万方的回执ID,可以根据这个ID在接口中查询具体的发送状态
        # 方法说明,因为不知道请求的Biz_id,所以只能通过mongo里获取,因为服务记录了发送的Biz_id,
        # 如果Biz_id 不为空, 则表示请求发送短信接口成功,成功则通过日期,号码,Biz_id来链接阿里云获取相关信息'
                # 然后通过Biz_id和手机号码与请求日期, 从阿里云调取相关信息
        # 如果Biz_id   为空, 则表示请求发送短信接口失败,则返回相应错误.
                # 通过mongo里直接看错误信息.
        sms_list =  []
        dbShortMessage =  conn.ShortMessage
        SmsReport =  dbShortMessage.SmsReport.find({"Phone_number": phoneno}).sort('Send_time', -1).limit(10)
        for i in SmsReport:
            biz_id =  str(i['Biz_id'])  # Biz_id 回执ID
            submit_time =  i['Send_time']
            submitdate =  str(submit_time[0:4] + submit_time[5:7] + submit_time[8:10])
            sms_detail =  {}
            if biz_id.split():
                # 阿里云调用
                client =  AcsClient('LTAInbYMK1LSMBAG', 'TnsxZWP4WBdX3ML907eeEeTtEdVpEG', 'default')
                aliyun =  CommonRequest()
                aliyun.set_accept_format('json')
                aliyun.set_domain('dysmsapi.aliyuncs.com')
                aliyun.set_method('POST')
                aliyun.set_protocol_type('https')
                aliyun.set_version('2017-05-25')
                aliyun.set_action_name('QuerySendDetails')

                aliyun.add_query_param('PhoneNumber', phoneno)
                aliyun.add_query_param('SendDate', submitdate)
                # CurrentPage 指定发送记录的的当前页码。
                aliyun.add_query_param('CurrentPage', "1")
                # PageSize 每页显示的短信记录数量(1~50)。
                aliyun.add_query_param('PageSize', "1")
                aliyun.add_query_param('BizId', biz_id)

                response =  client.do_action(aliyun)
                aaa =  eval(response)
                if len(eval(response)['SmsSendDetailDTOs']['SmsSendDetailDTO']):            
                    submit_detail =  eval(response)['SmsSendDetailDTOs']['SmsSendDetailDTO'][0]
                    sms_detail['phoneno'] = phoneno 
                    sms_detail['user_send_time'] = i['Send_time'] #用户请求时间
                    sms_detail['ali_send_time'] = submit_detail['SendDate'] # 阿里发的时间
                    if submit_detail['SendStatus'] ==  1:
                        sms_detail['user_receive_time'] = '-'
                        sms_detail['ali_errcode'] = '-' 
                    else:
                        sms_detail['user_receive_time'] = submit_detail['ReceiveDate'] # 用户收到的时间
                        sms_detail['ali_errcode'] = submit_detail['ErrCode'] # 阿里发短信时运营商给的状态码
                    sms_detail['ali_sendstatus'] = submit_detail['SendStatus'] # 阿里的发送状态码, 1等待回执,2发送失败,3发送成功
                    sms_detail['message'] = submit_detail['Content'] # 当阿里发送成功或失败时,这里显示阿里的消息内容
                    sms_detail['source'] = eval(submit_detail['OutId'])['Source'] 
                    sms_detail['type'] = eval(submit_detail['OutId'])['Type']
                    sms_detail['ip'] = eval(submit_detail['OutId'])['IP']
                    sms_list.append(sms_detail)
                else:
                    pass
            else: #当没有biz_id的时候,说明没有请求到阿里.即阿里云没有给万方回执.万方这边的规则应该没有通过导致
                o = json.loads(i['Out_id'])
                sms_detail['phoneno'] = phoneno 
                sms_detail['user_send_time'] = i['Send_time'] #用户请求时间
                sms_detail['ali_send_time'] = '-' # 阿里发的时间
                sms_detail['user_receive_time'] = '-' # 用户收到的时间
                sms_detail['ali_errcode'] = '-' # 阿里发短信时运营商给的状态码
                sms_detail['ali_sendstatus'] = 4 # 阿里的发送状态码, 1等待回执,2发送失败,3发送成功
                sms_detail['message'] = i['Err_msg'] # 无BizId,这里显示万方的消息内容
                sms_detail['source'] = o['Source']
                sms_detail['type'] = o['Type']
                sms_detail['ip'] = o['IP']
                sms_list.append(sms_detail)
        return render(request, 'workform/service_msg.html', {'realname_list': realname_list, 'sms_list': sms_list})
    return render(request, 'workform/service_msg.html')