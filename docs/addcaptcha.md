# 添加登录验证码

使用django-simple-captcha

如果是升级，请手动执行：
pip install -r install/requirements.txt
python manage.py syncdb

如果安装pillow报错：ValueError: jpeg is required unless explicitly disabled using --disable-jpeg, aborting，请确认这些已经安装：
sudo yum install python-devel
sudo yum install zlib-devel
sudo yum install libjpeg-turbo-devel

如果验证码图片生成不了，报错：The _imagingft C module is not installed，请确认安装：
sudo yum install freetype-devel libjpeg-devel libpng-devel

