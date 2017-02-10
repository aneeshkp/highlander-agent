class a:
    def callme(self,methodname, arg):
        methodnamepossibles=globals().copy()


s={'rule': {'method': 'failover', 'arg': {'instance_id': '1a355d66-5b12-4450-ab9a-9bfad3d6ab23', 'message': 'fail over'}}}
d={"rule": {"method": "failover", "arg": {"instance_id": "1a355d66-5b12-4450-ab9a-9bfad3d6ab23", "message": "fail over"}}}

print d["rule"]["method"]

