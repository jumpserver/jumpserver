# Common app 

Common app provide common view, function or others.

Common app shouldn't rely on other apps, because It may lead to cycle 
import.

If your want to implement some function or class, you should think 
whether other app use or not. If yes, You should make in common.

If the ability more relate to your app tightness, It's mean your app 
provide this ability, not common, You should write it on your app utils.



## Celery usage 


JumpServer use celery to run task async. Using redis as the broker, so
you should run a redis instance

#### Run redis

	$ yum -y install redis 
	
	or
	
	$ docker run -name jumpserver-redis -d -p 6379:6379 redis redis-server


#### Write tasks in app_name/tasks.py

ops/tasks.py

```
from __future__ import absolute_import

import time
from celery import shared_task
from common import celery_app


@shared_task
def longtime_add(x, y):
    print 'long time task begins'
    # sleep 5 seconds
    time.sleep(5)
    print 'long time task finished'
    return x + y
    

@celery_app.task(name='hello-world')
def hello():
    print 'hello world!'
  
```

#### Run celery in development 

```
$ cd apps
$ celery -A common worker -l info 
```

#### Test using task

```
$ ./manage.py shell
>>> from ops.tasks import longtime_add
>>> res = longtime_add.delay(1, 2)
>>> res.get()
```




