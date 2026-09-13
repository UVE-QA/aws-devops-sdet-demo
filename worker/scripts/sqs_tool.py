"""The break test's hands (scripts/break-poison-message.sh): talk to the queue
the worker is reading, from inside the worker's own image so the endpoint and
the credentials are the ones it uses.

Named sqs_tool and not queue: a script called queue.py puts its own directory
first on sys.path, and urllib3 - underneath boto3 - then imports IT as the
standard library's `queue` and dies on `queue.LifoQueue`. Found the first time
this was run.

    python scripts/sqs_tool.py poison             send a body that is not an event
    python scripts/sqs_tool.py depth <queue-url>  print ApproximateNumberOfMessages
    python scripts/sqs_tool.py purge <queue-url>  empty a queue (local only)
"""
import os
import sys

import boto3


def client():
    return boto3.client(
        "sqs",
        region_name=os.getenv("AWS_REGION", "us-west-2"),
        endpoint_url=os.getenv("SQS_ENDPOINT_URL") or None,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    verb = argv[1]
    if verb == "poison":
        resp = client().send_message(QueueUrl=os.environ["ITEMS_QUEUE_URL"],
                                     MessageBody="this is not an event")
        print(resp["MessageId"])
        return 0
    if verb == "depth" and len(argv) == 3:
        attrs = client().get_queue_attributes(
            QueueUrl=argv[2], AttributeNames=["ApproximateNumberOfMessages"]
        )["Attributes"]
        print(attrs["ApproximateNumberOfMessages"])
        return 0
    if verb == "purge" and len(argv) == 3:
        if not os.getenv("SQS_ENDPOINT_URL"):
            print("purge is for the local queue only", file=sys.stderr)
            return 2
        client().purge_queue(QueueUrl=argv[2])
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
