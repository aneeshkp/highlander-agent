import sys, time
from p import Daemon


class MyDaemon(Daemon):
    def run(self):
        while True:
            time.sleep(1)


s = {"instance_to_monitor": {
    "id": "1a1c8b46-bee3-4734-81f6-1a3b46581ca2",
    "instance": {
        "on_fail_event": [
            {
                "rule": {
                    "method": "notify_instance",
                    "arg": {
                        "instance_id": "1a355d66-5b12-4450-ab9a-9bfad3d6ab23",
                        "message": {
                            "rule": {
                                "method": "wakeup_instance",
                                "arg": {
                                    "instance_id": "1a355d66-5b12-4450-ab9a-9bfad3d6ab23",
                                    "message": "fail over"
                                }
                            }
                        }
                    }
                }
            },
            {
                "rule": {
                    "method": "shutdown_monitoring3",
                    "arg": {
                        "instance_id": "1a1c8b46-bee3-4734-81f6-1a3b46581ca2",
                        "message": "something"
                    }
                }
            },
            {
                "rule": {
                    "method": "shutdown_monitoring2",
                    "arg": {
                        "instance_id": "1a1c8b46-bee3-4734-81f6-1a3b46581ca2",
                        "message": "something"
                    }
                }
            }
        ]
    }
}
}

import simplejson

j=s
print j["instance_to_monitor"]
on_fail_event = j["instance_to_monitor"]["instance"]["on_fail_event"]
for rule in on_fail_event:
    print rule

"""if __name__ == "__main__":
    daemon = MyDaemon('/tmp/pid/daemon-example.pid')
    daemon.start()
"""
