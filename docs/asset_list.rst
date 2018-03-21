资产列表
===========

这里介绍资产列表的功能。

.. contents:: Topics

.. _view_asset_list:

查看资产列表
`````````````

点击页面左侧的“资产管理”菜单下的“资产列表”按钮，查看当前所有的资产列表。

.. _create_asset_tree:

管理资产树
```````````````

节点不能重名，右击节点可以添加、删除和重命名节点，以及进行资产相关的操作。

.. image:: _static/img/asset_tree.jpg

为资产树节点分配资产

在资产列表页面，选择要添加资产的节点，右键，选择添加资产到节点。

.. image:: _static/img/add_asset_to_node.jpg

选择要被添加的资产，点击"确认"即可。

.. image:: _static/img/select_asset_to_node.jpg

删除节点资产

选择要被删除的节点，选择"从节点删除"，点击"提交"即可。

.. image:: _static/img/delete_asset_from_node.jpg


.. _create_asset:

创建资产
````````````

点击页面左侧的“资产管理”菜单下的“资产列表”按钮，查看当前所有的资产列表。

点击页面左上角的“创建资产”按钮，进入资产创建页面，填写资产信息。

IP 地址和管理用户要确保正确，确保所选的管理用户的用户名和密码能"牢靠"地登录指定的 IP 主机上。资产的系统平台也务必正确填写。公网 IP 信息只用于展示，可不填，Jumpserver 连接资产主机使用的是 IP 信息。

.. image:: _static/img/create_asset.jpg

资产创建信息填写好保存之后，可测试资产是否能正确连接：

.. image:: _static/img/check_asset_connect.jpg

如果资产不能正常连接，请检查管理用户的用户名和密钥是否正确以及该管理用户是否能使用 SSH 从 Jumpserver 主机正确登录到资产主机上。

创建 Windows 资产

同创建 Linux 资产一样。

创建 Windows 资产，系统平台请选择正确的 Windows，端口号为3389，IP 和 管理用户请正确选择，确保管理用户能正确登录到指定的 IP 主机上。

.. image:: _static/img/create_windows_asset.jpg

.. _update_asset:

更新资产
````````````

点击页面右边的“更新”按钮，进入编辑资产页面，更新资产信息，点击“提交”按钮，完成资产更新。

.. _delete_asset:

删除资产
`````````

点击页面右边的“删除”按钮，弹出删除确认框，点击“确认”按钮，完成资产删除。

.. _batch_operation:

批量操作
````````````

选中资产，选择页面左下角批量操作选项，点击“提交”按钮，完成批量操作。