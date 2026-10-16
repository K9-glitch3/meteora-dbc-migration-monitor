import base64
import copy
from fractions import Fraction
import unittest
from jsonschema import ValidationError

from dbc_monitor.protocol import b58encode, b58decode, migrations, MIGRATE, DBC
from dbc_monitor.records import derive, decode_pool, VALIDATOR, FIELDS
from fixtures import captures, account, transaction, SIGNATURE


class ObservationTests(unittest.TestCase):
    def test_finalized_identity_and_pool_price(self):
        rows = derive(captures(), source="synthetic_test")
        self.assertEqual(rows[1]["verdict"], "SUPPORTED_COMPARISON")
        self.assertEqual(rows[1]["scope"], "migration_identity")
        self.assertEqual(rows[2]["details"]["raw_price_numerator"], "4")
        self.assertEqual(rows[2]["details"]["raw_price_denominator"], "1")
        self.assertEqual(rows[2]["verdict"], "NO_CONCLUSION")
        self.assertEqual(rows[2]["details"]["quote_comparison"], "NOT_PERFORMED")

    def test_missing_transaction(self):
        data = captures(); data[2]["result"] = None
        self.assertEqual(derive(data)[1]["reason"], "finalized_transaction_unavailable")

    def test_finality_required(self):
        data = captures(); data[2]["commitment"] = "confirmed"
        self.assertEqual(derive(data)[1]["reason"], "finality_not_established")

    def test_slot_change_rejected(self):
        data = captures(); data[2]["result"]["slot"] = 101
        self.assertEqual(derive(data)[1]["reason"], "notification_finalized_slot_mismatch")

    def test_signature_change_rejected(self):
        data = captures(); data[2]["result"]["transaction"]["signatures"] = [b58encode(bytes([5])*64)]
        self.assertEqual(derive(data)[1]["reason"], "transaction_signature_mismatch")

    def test_failed_transaction(self):
        data = captures(); data[2]["result"]["meta"]["err"] = {"InstructionError": [0,"custom"]}
        self.assertEqual(derive(data)[1]["reason"], "transaction_failed")

    def test_missing_success_metadata_is_not_accepted(self):
        data=captures();del data[2]["result"]["meta"]["err"]
        self.assertEqual(derive(data)[1]["reason"],"invalid_migration_instruction")
        self.assertEqual(derive(data)[1]["verdict"],"REJECTED_OBSERVATION")

    def test_stale_and_unknown_block_time(self):
        for value, freshness in [(1,"stale"),(None,"unknown")]:
            data = captures(); data[2]["result"]["blockTime"] = value
            row = derive(data)[1]
            self.assertEqual(row["verdict"], "NO_CONCLUSION")
            self.assertEqual(row["freshness"], freshness)

    def test_missing_instruction(self):
        data = captures(); data[2]["result"]["transaction"]["message"]["instructions"] = []
        self.assertEqual(derive(data)[1]["verdict"], "UNSUPPORTED_CONFIGURATION")

    def test_wrong_program_not_accepted(self):
        tx = transaction(); tx["transaction"]["message"]["instructions"][0]["programIdIndex"] = 0
        self.assertEqual(migrations(tx), [])

    def test_bad_account_index_and_authority(self):
        for change in [-1, 999]:
            tx = transaction(); tx["transaction"]["message"]["instructions"][0]["accounts"][4] = change
            with self.assertRaises(ValueError): migrations(tx)
        tx = transaction(); tx["transaction"]["message"]["instructions"][0]["accounts"][12] = 0
        with self.assertRaises(ValueError): migrations(tx)

    def test_cpi_and_loaded_addresses(self):
        tx = transaction(); ix = tx["transaction"]["message"]["instructions"].pop()
        tx["meta"]["innerInstructions"] = [{"index": 0, "instructions": [ix]}]
        self.assertEqual(migrations(tx)[0]["instruction"], "inner:0:0")
        tx["transaction"]["message"]["accountKeys"].pop()
        tx["meta"]["loadedAddresses"]["readonly"] = [DBC]
        self.assertEqual(len(migrations(tx)), 1)

    def test_pool_layout_owner_and_encoding(self):
        for changed in [account(owner=DBC), account(data=["invalid!", "base64"]), account(data=["AA==", "base64"]),
                        account(executable=True), account(data=["AAAA", "base64+zstd"]), None]:
            with self.assertRaises(ValueError): decode_pool(changed)

    def test_unknown_layout_and_price_bounds(self):
        for field, value in [("layout_version", 9), ("collect_fee_mode", 9), ("sqrt_price",0)]:
            a = account(); raw = bytearray(base64.b64decode(a["data"][0])); f = FIELDS[field]
            raw[f["offset"]:f["offset"]+f["size"]] = value.to_bytes(f["size"], "little")
            a["data"][0] = base64.b64encode(raw).decode()
            with self.assertRaises(ValueError): decode_pool(a)

    def test_price_exact_at_large_integer_boundary(self):
        a = account(); raw = bytearray(base64.b64decode(a["data"][0])); f = FIELDS["sqrt_price"]
        value = (1 << 100) + 1234567
        raw[f["offset"]:f["offset"]+16] = value.to_bytes(16,"little")
        a["data"][0] = base64.b64encode(raw).decode()
        d = decode_pool(a)
        self.assertEqual(Fraction(int(d["raw_price_numerator"]),int(d["raw_price_denominator"])),Fraction(value**2,2**128))

    def test_snapshot_must_follow_migration_and_match_roles(self):
        data = captures(); data[3]["result"]["context"]["slot"] = 99
        self.assertEqual(derive(data)[2]["reason"], "snapshot_precedes_migration")
        data = captures(); raw = bytearray(base64.b64decode(data[3]["result"]["value"][0]["data"][0])); raw[168] ^= 1
        data[3]["result"]["value"][0]["data"][0] = base64.b64encode(raw).decode()
        self.assertEqual(derive(data)[2]["reason"], "pool_role_mismatch")

    def test_out_of_order_account(self):
        data = captures(); extra = copy.deepcopy(data[4]); extra["result"]["context"]["slot"] = 101
        data.insert(5,extra)
        for i,row in enumerate(data): row["sequence"] = i+1
        self.assertEqual(derive(data)[-1]["reason"], "out_of_order_slot")

    def test_sequence_gaps_and_duplicate_sequence_fail(self):
        for seq in [2,8,True]:
            data = captures(); data[2]["sequence"] = seq
            with self.assertRaises(ValueError): derive(data)

    def test_schema_rejects_bad_fields(self):
        row = derive(captures())[0]
        for key,value in [("slot",True),("observed_at","not-a-date"),("verdict","SUCCESS"),("signature","fake"),("schema_version","2")]:
            changed = {**row,key:value}
            with self.assertRaises(ValidationError): VALIDATOR.validate(changed)
        with self.assertRaises(ValidationError): VALIDATOR.validate({**row,"secret":"bad"})

    def test_base58_roundtrip(self):
        for size in [0,1,32,64]:
            raw = bytes(range(size))
            self.assertEqual(b58decode(b58encode(raw)), raw)
        with self.assertRaises(ValueError): b58decode("0OIl")
