import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbc_monitor.collector import collect
from fixtures import transaction, SIGNATURE


class CollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_reconnect_duplicates_and_slot_conflict(self):
        now = [0.0]
        def clock():
            now[0] += 0.05
            return now[0]
        class Socket:
            def __init__(self, epoch):
                self.epoch = epoch
                self.messages = [{"id":1,"result":10}]
                for slot in [100,100,101]:
                    self.messages.append({"params":{"subscription":10,"result":{"context":{"slot":slot},
                        "value":{"signature":SIGNATURE,"err":None,"logs":["Program log: Instruction: MigrationDammV2"]}}}})
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def send(self,value):
                request = json.loads(value)
                assert request["method"] in ("logsSubscribe","accountSubscribe")
            async def recv(self):
                if self.messages: return json.dumps(self.messages.pop(0))
                raise OSError("Disconnected")
        epochs=[]
        def connect(*args,**kwargs):
            epochs.append(1)
            return Socket(len(epochs))
        def rpc(self,method,params):
            if method == "getTransaction": return transaction()
            return {"context":{"slot":101},"value":[None,None,None]}
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            now[0] += seconds
            await original_sleep(0)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"run"
            with patch("websockets.connect",side_effect=connect), patch("dbc_monitor.collector.monotonic",side_effect=clock), \
                 patch("dbc_monitor.collector.Rpc.call",new=rpc), patch("dbc_monitor.collector.asyncio.sleep",side_effect=fast_sleep):
                result = await collect(root,seconds=10)
            rows=[json.loads(x) for x in (root/"capture.jsonl").read_text().splitlines()]
            self.assertGreaterEqual(result["duplicates"],2)
            self.assertGreaterEqual(result["reconnects"],1)
            self.assertTrue(any(x["kind"]=="slot_conflict" for x in rows))
            self.assertEqual(rows[-1]["kind"],"run_end")
            self.assertEqual(sum(x["kind"]=="migration_notification" for x in rows),1)

    async def test_invalid_capacity_prevents_network(self):
        with self.assertRaises(ValueError): await collect("unused",seconds=0)
        with self.assertRaises(ValueError): await collect("unused",max_pools=100)

    async def test_invalid_endpoint_leaves_no_partial_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"run"
            with self.assertRaises(ValueError): await collect(root,endpoint="http://invalid.example")
            self.assertFalse(root.exists())

    async def test_cancellation_is_not_reported_as_complete(self):
        class CancelledSocket:
            async def __aenter__(self): raise asyncio.CancelledError()
            async def __aexit__(self,*args): pass
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"run"
            with patch("websockets.connect",return_value=CancelledSocket()):
                with self.assertRaises(asyncio.CancelledError): await collect(root,seconds=1)
            rows=[json.loads(x) for x in (root/"capture.jsonl").read_text().splitlines()]
            self.assertEqual(rows[-1]["reason"],"interrupted")
            self.assertEqual(len(rows[0]["collector_code_sha256"]),64)
