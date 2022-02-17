from django.test import TestCase

# Create your tests here.

# TODO: Model
# 用户             User
# 角色             Role
# 权限             Permission
# 用户-角色 关系    RoleBinding
# 角色-权限 关系    Role


# TODO:
#  1. 创建用户、邀请用户 (给用户添加角色)
#  2. 创建角色 (创建角色并指定权限集)
#  3. APIView 控制用户访问权限 (获取用户访问API行为的codename，获取用户角色-权限，判断是否包含)
#  4. 获取权限集 (分类获取 scope: system、org、app)
#  5. 定义权限位 (整理所有权限位并分类，同时在Model中重新定义权限名称)
#  7. 添加内置角色
#  6. 修改用户Model/Serializer/API，删除旧role字段，关联新role
#  8. 权限位名称翻译 (整理一个dict，key为codename，value为翻译)
#  9. 修改用户-组织关联的角色，修改表结构
#  10. 前端获取所有权限，给每个按钮添加对应的权限控制指令
