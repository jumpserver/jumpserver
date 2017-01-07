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
   pip install -r requirements.txt  #  Install pip module
   
   yum -y install `cat rpm_requirements.txt` #  Install rpm package
   
   cp config-example.py config.py  #  Prepaire config from example config
   
   cd apps && python manage.py makemigrations  #  Make migrations for django
   
   python manage.py migrate  # Migrate ORM to database
   
   python manage.py loaddata init  # Init some data
   
   python manage.py loaddata fake   # Generake some fake data
   
   yum -y install redis && service redis start  # Or install redis docker
   
   python manage.py runserver 0.0.0.0:80  # Run it
   
   ```
   
   ~ 文档

   * [项目结构描述](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/project_structure.md)
   * [Python代码规范](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/python_style_guide.md)
   * [API设计规范](https://code.jumpserver.org/jumpserver/jumpserver/blob/master/docs/api_style_guide.md)
   * [表结构](https://code.jumpserver.org/Jumpserver/jumpserver/wikis/table-structure)

