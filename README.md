                            // Jumpserver //
                            
                            
   ~ Jumpserver是什么?
         
   Jumpserver是一款开源的跳板机(堡垒机)产品, 主要使用Python,Django开发
   他实现了跳板机(堡垒机)的主要功能，删减、优化了传统堡垒机，致力于为互联网
   运维提供服务
   
   ~ 版本依赖
   
   * Python 2.7
   
   * Django 1.10
   
   
   ~ 快速开始
   
   ```
   pip install -r requirements.txt
   
   cp config-example.py config.py
   
   cd apps && python manage.py makemigrations 
   
   python manage.py migrate
   
   python manage.py loaddata init  # 初始化数据
   
   python manage.py loadata fake 
   
   python manage.py runserver 0.0.0.0:80
   
   ```
   
   ~ 文档

   * [项目结构描述](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/project_structure.md)
   * [Python代码规范](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/python_style_guide.md)
   * [API设计规范](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/api_style_guide.md)
   * [表结构](https://code.jumpserver.org/jumpserver/jumpserver/wikis/table_structure_image)

