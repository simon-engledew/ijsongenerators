# About

A streaming JSON parser based on ijson.

Can handle JSON documents larger than the available memory.

Wraps ijson in generators rather than having to deal with the event stream:

```python
for username, sessions in ijsongenerators.parse(data):
    for _, session in sessions:
        for session_name, groups in session:
            print(username, list(groups))
```

Each value will either be a literal or a generator that yields more of the document.

Each generator will yield string value pairs or number value indexed array entries.

It can also do a wildcard search for any matching objects at a path:

```python
for sessions in ijsongenerators.search(data, 'users', ijsongenerators.WILDCARD, 'sessions'):
    print(sessions[0]['username'])
```

This will yield resolved Python objects, so make sure the search describes the exact part of the document you are interested in.
