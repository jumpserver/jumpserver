## Celery 

Jumpserver use celery to run task async. Using redis as the broker, so
you should run a redis instance

1. Run redis
```
# yum -y install redis 
or
# docker run -name jumpserver-redis -d -p 6379:6379 redis redis-server
```


2. Write tasks in app_name/tasks.py

ops/tasks.py
```
from __future__ import absolute_import

import time
from celery import shared_task


@shared_task
def longtime_add(x, y):
    print 'long time task begins'
    # sleep 5 seconds
    time.sleep(5)
    print 'long time task finished'
    return x + y
```

3. Run celery in development 
```
# cd apps
# celery -A common worker -l info 
```

4. Test using task
```
# ./manage.py shell
> from ops.tasks import longtime_add
> res = longtime_add.delay(1, 2)
> res.get()
```

