Jumpserver 项目规范（Draft）
============================

语言框架
----------

1. Python 3.6.1 (当前最新)
2. Django 1.11 (当前最新)
3. Flask 0.12 Luna (当前最新)
4. Paramiko 2.12 Coco (当前最新)

Django 规范
--------------

1. 尽量使用 Class Base View 编程，更少代码
2. 使用 Django Form
3. 每个 URL 独立命名，不要硬编码，同理 Static 也是
4. 数据库表名手动指定，不要使用默认
5. 代码优雅简洁
6. 注释明确优美
7. 测试案例尽可能完整
8. 尽可能利用 Django 造好的轮子

代码风格
-----------

Python 方面大致的风格，我们采用 pocoo 的\ `Style
Guidance`_\ ，但是有些细节部分会尽量放开 参考国内翻译

基本的代码布局
~~~~~~~~~~~~~~

缩进
^^^^^^^^

1. Python 严格采用4个空格的缩进，任何 Python 代码都都必须遵守此规定。
2. Web 部分代码（HTML、CSS、JavaScript），Node.js 采用2空格缩进，同样不使用 TAB。
   之所以与 Python 不同，是因为 JS 中有大量回调式的写法，2空格可以显著降低视觉上的负担。

最大行长度
^^^^^^^^^^^^^

按 PEP8 规范，Python 一般限制最大79个字符，
但是 Django 的命名，URL 等通常比较长,
而且21世纪都是宽屏了，所以我们限制最大120字符

**补充说明：HTML 代码不受此规范约束。**

长语句缩进
^^^^^^^^^^^^

编写长语句时，可以使用换行符"\"换行。在这种情况下，下一行应该与上一行的最后一个“.”句点或“=”对齐，或者是缩进4个空格符。

::

    this_is_a_very_long(function_call, 'with many parameters') \
        .that_returns_an_object_with_an_attribute

    MyModel.query.filter(MyModel.scalar > 120) \
                 .order_by(MyModel.name.desc()) \
                 .limit(10)

如果你使用括号“()”或花括号“{}”为长语句换行，那么下一行应与括号或花括号对齐：

::

    this_is_a_very_long(function_call, 'with many parameters',
                        23, 42, 'and even more')

对于元素众多的列表或元组，在第一个“[”或“(”之后马上换行：

::

    items = [
        'this is the first', 'set of items', 'with more items',
        'to come in this line', 'like this'
    ]

.. _Style Guidance: http://www.pocoo.org/internal/styleguide/


空行
^^^^^^

顶层函数与类之间空两行，此外都只空一行。不要在代码中使用太多的空行来区分不同的逻辑模块。

::

    def hello(name):
        print 'Hello %s!' % name


    def goodbye(name):
        print 'See you %s.' % name


    class MyClass(object):
        """This is a simple docstring."""

        def __init__(self, name):
            self.name = name

        def get_annoying_name(self):
            return self.name.upper() + '!!!!111'

语句和表达式
~~~~~~~~~~~~

一般空格规则
^^^^^^^^^^^^

1. 单目运算符与运算对象之间不空格（例如，-，~等），即使单目运算符位于括号内部也一样。
2. 双目运算符与运算对象之间要空格。

::

    exp = -1.05
    value = (item_value / item_count) * offset / exp
    value = my_list[index]
    value = my_dict['key']

比较
^^^^

1. 任意类型之间的比较，使用“==”和“!=”。
2. 与单例（singletons）进行比较时，使用 is 和 is not。
3. 永远不要与True或False进行比较（例如，不要这样写：foo ==
   False，而应该这样写：not foo）。

否定成员关系检查
^^^^^^^^^^^^^^^^

使用 foo not in bar，而不是 not foo in bar。

命名约定
~~~~~~~~

1. 类名称：采用骆驼拼写法（CamelCase），首字母缩略词保持大写不变（HTTPWriter，而不是 HttpWriter）。
2. 变量名：小写_以及_下划线（lowercase_with_underscores）。
3. 方法与函数名：小写_以及_下划线（lowercase_with_underscores）。
4. 常量：大写_以及_下划线（UPPERCASE_WITH_UNDERSCORES）。
5. 预编译的正则表达式：name_re。
6. 受保护的元素以一个下划线为前缀。双下划线前缀只有定义混入类（mixin classes）时才使用。
7. 如果使用关键词（keywords）作为类名称，应在名称后添加后置下划线（trailing underscore）。
   允许与内建变量重名，不要在变量名后添加下划线进行区分。如果函数需要访问重名的内建变量，请将内建变量重新绑定为其他名称。
8. 命名要有寓意, 不使用拼音,不使用无意义简单字母命名 (循环中计数例外 for i in)
9. 命名缩写要谨慎, 尽量是大家认可的缩写

函数和方法的参数：
^^^^^^^^^^^^^^^^^^

1. 类方法：cls 为第一个参数。
2. 实例方法：self 为第一个参数。
3. property函数中使用匿名函数（lambdas）时，匿名函数的第一个参数可以用 x 替代，
   例如：display_name = property(lambda x: x.real_name or x.username)。


文档注释（Docstring，即各方法，类的说明文档注释）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

所有文档字符串均以 reStructuredText 格式编写，方便 Sphinx 处理。文档字符串的行数不同，布局也不一样。
如果只有一行，代表字符串结束的三个引号与代表字符串开始的三个引号在同一行。
如果为多行，文档字符串中的文本紧接着代表字符串开始的三个引号编写，代表字符串结束的三个引号则自己独立成一行。
（有能力尽可能用英文, 否则请中文优雅注释）

::

    def foo():
        """This is a simple docstring."""


    def bar():
        """This is a longer docstring with so much information in there
        that it spans three lines.  In this case, the closing triple quote
        is on its own line.
        """

文档字符串应分成简短摘要（尽量一行）和详细介绍。如果必要的话，摘要与详细介绍之间空一行。

模块头部
~~~~~~~~

模块文件的头部包含有 utf-8 编码声明（如果模块中使用了非 ASCII 编码的字符，建议进行声明），以及标准的文档字符串。

::

    # -*- coding: utf-8 -*-
    """
        package.module
        ~~~~~~~~~~~~~~

        A brief description goes here.

        :copyright: (c) YEAR by AUTHOR.
        :license: LICENSE_NAME, see LICENSE_FILE for more details.
    """

注释（Comment）
~~~~~~~~~~~~~~~~

注释的规范与文档字符串编写规范类似。二者均以 reStructuredText 格式编写。
如果使用注释来编写类属性的文档，请在#符号后添加一个冒号“:”。
(有能力尽可能用英文, 否则请中文优雅注释)

::

    class User(object):
        #: the name of the user as unicode string
        name = Column(String)
        #: the sha1 hash of the password + inline salt
        pw_hash = Column(String)