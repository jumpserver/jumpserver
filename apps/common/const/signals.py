"""
`m2m_changed`

```
def m2m_signal_handler(action, instance, reverse, model, pk_set, using):
     pass
```
"""
PRE_ADD = 'pre_add'
POST_ADD = 'post_add'
PRE_REMOVE = 'pre_remove'
POST_REMOVE = 'post_remove'
PRE_CLEAR = 'pre_clear'
POST_CLEAR = 'post_clear'

POST_PREFIX = 'post'
PRE_PREFIX = 'pre'

SKIP_SIGNAL = 'skip_signal'
