# About

A streaming JSON parser based on ijson.

Wraps ijson in generators rather than having to deal with the event stream:

```python
for username, sessions in ijsongenerators.parse(data).items():
        for session in sessions:
            for session_name, groups in session.items():
                print(username, list(groups))
```
