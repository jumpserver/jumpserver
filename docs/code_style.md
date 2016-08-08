# Jumpserver 项目规范（Draft）

## 语言框架
1. Python 2.7 由于ansible目前不支持python3
2. Django 1.10 (最新版本)
3. Terminal Websocket使用go实现


## 代码风格

1. Python方面大致的风格，我们采用[pocoo的Style Guidance](http://www.pocoo.org/internal/styleguide/)，但是有些细节部分会尽量放开。
2. 前端部分(js, css, html)，采用[Google的HTML/CSS Coding Style Guidance](https://google.github.io/styleguide/htmlcssguide.xml)以及[JavaScript Coding Style](http://google.github.io/styleguide/javascriptguide.xml)
3. Google的Style指南还规范了各种写法，不光包括Coding Format，请尽量遵守，但Coding Format的原则则必须遵守。
4. Go的代码风格由@Tad指定。
5. 所有人编码前请仔细阅读相应的代码风格指导规范，编码的时候请严格遵循，相互review代码。


## Django规范
1. 尽量使用Class Base View编程，更少代码
2. 使用Django Form
3. 每个url独立命名，不要硬编码，同理static也是
4. 数据库表名手动指定，不要使用默认
5. 代码优雅简洁
6. 注释明确优美
7. 测试案例尽可能完整
8. 尽可能利用Django造好的轮子


关于代码风格规范一些补充说明：

### 基本的代码布局

#### 缩进

1. Python严格采用4个空格的缩进，不使用tab（\t），任何python代码都都必须遵守此规定。
2. web部分代码(HTML, CSS, JavaScript)，Node.js采用2空格缩进，同样不使用tab (\t)。
之所以与Python不同，是因为js中有大量回调式的写法，2空格可以显著降低视觉上的负担。

#### 最大行长度

按PEP8规范，Python一般限制最大80个字符, 强制遵守。

**补充说明：HTML代码不受此规范约束。**

#### 长语句缩进

Python代码参考pocoo style(注: 参考Flask源码)一致。JavaScript代码参考Google的Coding Format说明。

#### 空行

Python代码参考pocoo style一致。JavaScript代码参考Google的Coding Format说明。

### 语句和表达式

Python代码参考pocoo style一致。JavaScript代码参考Google的Coding Format说明。

### 命名约定

Python代码参考pocoo style一致。JavaScript代码参考Google的Coding Format说明。

### 文档注释(Docstring，即各方法，类的说明文档注释)

Python代码参考pocoo style一致。JavaScript代码参考Google的Coding Format说明。

### 注释(comment)

Python代码参考pocoo style一致。JavaScript代码参考Google的Coding Format说明。



### Go项目

请@Tad负责补完。


### API

这里仅考虑REST API的基本情况。

#### HTTP Method

1. 读操作使用GET方法，写操作使用PUT/POST/DELETE方法，其中删除记录的操作使用DELETE方法。  
2. 使用PUT方法实现的API必须是幂等的（多次执行同样操作，结果相同）。
3. POST则是实现非幂等的接口。
4. 一般性的CRUD操作，R一般使用GET方法，C使用POST，U使用PUT方法，D使用DELETE方法。

#### URL

1. 每个项目的的root path后面整合的时候回指定为项目名，这个不需要各项目组考虑。整合的方案可以采用Nginx来转发，后面可以详细讨论
3. 一般性的增删查改(CRUD)API，完全使用HTTP method加上url提供的语义，url中的可变部分（比如上面提到的<role_id>）一般用来传递该API操作的核心实体对象的唯一ID，如果有更多的参数需要提供，GET方法请使用url parameter(例如："?client_id=xxxxx&app_id=xxxxxx")，PUT/POST/DELETE方法请使用请求体传递参数。

**其他具体情况具体讨论**
