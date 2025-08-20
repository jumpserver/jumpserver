import base64
import io
import urllib.parse
from io import BytesIO
from urllib.parse import urlparse

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes
from playwright.sync_api import sync_playwright

charts_map = {
    "UserReport": {
        "title": "用户登录报告",
        "path": "/ui/#/reports/users/user-activity"
    },
    "ChangePassword": {
        "title": "用户改密报告",
        "path": "/ui/#/reports/users/change-password"
    },
    "AssetStatistics": {
        "title": "资产统计报告",
        "path": "/ui/#/reports/assets/asset-statistics"
    },
    "AssetReport": {
        "title": "资产活动报告",
        "path": "/ui/#/reports/assets/asset-activity"
    },
    "AccountStatistics": {
        "title": "账号统计报告",
        "path": "/ui/#/reports/accounts/account-statistics"
    },
    "AccountAutomationReport": {
        "title": "账号自动化报告",
        "path": "/ui/#/reports/accounts/account-automation"
    }
}


def export_chart_to_pdf(chart_name, sessionid, request=None):
    chart_info = charts_map.get(chart_name)

    if not chart_info:
        return None, None

    if request:
        url = request.build_absolute_uri(urllib.parse.unquote(chart_info['path']))
    else:
        url = urllib.parse.unquote(chart_info['path'])
    if settings.DEBUG_DEV:
        url = url.replace(":8080", ":9528")
    days = request.GET.get('days', 7)
    url = url + f"?days={days}"
    print("Url: ", url)

    with sync_playwright() as p:
        lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1000, "height": 800}, locale=lang)
        # 设置 sessionid cookie
        parsed_url = urlparse(url)
        context.add_cookies([
            {
                'name': settings.SESSION_COOKIE_NAME,
                'value': sessionid,
                'domain': parsed_url.hostname,
                'path': '/',
                'httpOnly': True,
                'secure': False,  # 如有 https 可改 True
            }
        ])
        page = context.new_page()
        try:
            page.goto(url, wait_until='networkidle')
            page_title = page.title()
            print(f"Page title: {page_title}")
            pdf_bytes = page.pdf(format="A4", landscape=True,
                                 margin={"top": "35px", "bottom": "30px", "left": "20px", "right": "20px"})
        except Exception as e:
            print(f'Playwright error: {e}')
            pdf_bytes = None
        finally:
            browser.close()
        return pdf_bytes, page_title


@method_decorator(csrf_exempt, name='dispatch')
class ExportPdfView(View):
    def get(self, request):
        chart_name = request.GET.get('chart')
        return self._handle_export(request, chart_name)

    def post(self, request):
        chart_name = request.POST.get('chart')
        return self._handle_export(request, chart_name)

    def _handle_export(self, request, chart_name):
        if not chart_name:
            return HttpResponseBadRequest('Missing chart parameter')
        sessionid = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if not sessionid:
            return HttpResponseBadRequest('No sessionid found in cookies')

        pdf_bytes, title = export_chart_to_pdf(chart_name, sessionid, request=request)
        if not pdf_bytes:
            return HttpResponseBadRequest('Failed to generate PDF')
        filename = f"{title}-{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        response = FileResponse(io.BytesIO(pdf_bytes), as_attachment=True, filename=filename,
                                content_type='application/pdf')
        return response


class SendMailView(View):

    def post(self, request):
        chart_name = request.GET.get('chart')
        if not chart_name:
            return HttpResponseBadRequest('Missing chart parameter')
        email = request.user.email
        if not email:
            return HttpResponseBadRequest('Missing email parameter')
        sessionid = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if not sessionid:
            return HttpResponseBadRequest('No sessionid found in cookies')

        # 1. 生成 PDF
        pdf_bytes, title = export_chart_to_pdf(chart_name, sessionid, request=request)
        if not pdf_bytes:
            return HttpResponseBadRequest('Failed to generate PDF')

        # 2. PDF 转图片
        images = convert_from_bytes(pdf_bytes, dpi=200)
        # 3. 图片转 base64
        img_tags = []
        for img in images:
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            img_tags.append(f'<img src="data:image/png;base64,{encoded}" style="width:100%; max-width:800px;" />')
        html_content = "<br/>".join(img_tags)

        # 4. 发送邮件
        subject = f"{title} 报表"
        from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        to = [email]
        msg = EmailMultiAlternatives(subject, '', from_email, to)
        msg.attach_alternative(html_content, "text/html")
        filename = f"{title}-{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        msg.attach(filename, pdf_bytes, "application/pdf")
        msg.send()

        return JsonResponse({"message": "邮件发送成功"})
