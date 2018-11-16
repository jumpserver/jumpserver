升级常见问题
---------------------

1. git pull 时提示 error: Your local changes to the following file would be overwritten by merge

.. code-block:: shell

    # 这是因为你修改了本地文件导致代码冲突, 请确认修改的内容并手动进行合并，请谨慎处理

    # 如果希望保留你的改动
    $ git stash
    $ git pull
    $ git stash pop
    # 可以使用git diff -w +文件名 来确认代码自动合并的情况

    # 或者放弃本地的修改
    $ git reset --hard
    $ git pull

2. sh make_migrations.sh 时提示 1064, "You have an error in your SQL syntax; check the manual than corresponds to your MySql server version for the right syntax to use near '(6) NOT NULL'"

.. code-block:: vim

    # 这是因为你的数据库版本不对, 从 1.4.x 版本开始 mysql 版本需要大于等于 5.6, mariadb 版本需要大于等于 5.5.6
    # 请更换数据库重新操作
