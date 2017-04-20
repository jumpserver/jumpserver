from django import forms
from captcha.fields import CaptchaField,CaptchaTextInput
#from django.conf import settings

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control','placeholder':'Username','required':'length[6~50]'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control','placeholder':'Password','required':''}))
#    captcha = CaptchaField(widget=CaptchaTextInput(output_format=getattr(settings, 'CAPTCHA_OUTPUT_FORMAT', '%(hidden_field)s %(text_field)s %(image)s'),attrs={'class': 'form-control','placeholder':'captcha','required':''}))
    captcha = CaptchaField(widget=CaptchaTextInput(output_format='%(hidden_field)s %(text_field)s %(image)s',attrs={'class': 'form-control','placeholder':'Captcha','required':''}))


