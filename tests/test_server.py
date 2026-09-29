import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from server import ZoteroClient, ToolError, APIError, call_tool, rpc_response, NoRedirect

PAPER = {"key": "ABCD2345", "version": 1, "data": {"itemType": "journalArticle", "title": "石墨烯 Graphene", "DOI": "10.1021/nl0717715"}}
ATTACHMENT = {"key": "PDF23456", "version": 1, "data": {"itemType": "attachment", "parentItem": "ABCD2345", "contentType": "application/pdf"}}


class Response:
    def __init__(self, data, headers):
        self.headers = headers
        self.raw = data.encode() if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode()
    def read(self, size):
        return self.raw[:size]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class FakeZotero:
    """HTTP boundary double; assertions inspect actual urllib Requests and JSON bodies."""
    def __init__(self):
        self.calls = []
        self.notes = []
        self.server_id = "local-instance-A"
        self.error_path = None
        self.error_code = 403
        self.partial_failure = False
        self.drop_write_response = False
        self.remember = False
        self.file_url = "https://example.com/not-local.pdf"

    def open(self, request, timeout):
        self.calls.append(request)
        parsed = urlsplit(request.full_url)
        path = parsed.path.removeprefix("/api/")
        query = parse_qs(parsed.query)
        headers = {"Zotero-API-Version": "3", "Total-Results": "1"}
        if self.server_id:
            headers["Zotero-Server-ID"] = self.server_id
        if self.error_path == path:
            raise HTTPError(request.full_url, self.error_code, "failure", {"Retry-After": "1"}, io.BytesIO(b"secret"))
        if path.endswith("/items/top"):
            return Response([PAPER], headers)
        if path == "users/0/groups":
            return Response([{ "id": 123, "data": {"name": "Study Group"}}], headers)
        if path.endswith("/collections"):
            return Response([{ "key": "COLL2345", "data": {"name": "RBK", "parentCollection": False}}], headers)
        if path.endswith("/items/ABCD2345"):
            return Response(PAPER, headers)
        if path.endswith("/items/PDF23456"):
            return Response(ATTACHMENT, headers)
        if path.endswith("/items/ABCD2345/children"):
            return Response([ATTACHMENT], headers)
        if path.endswith("/items/PDF23456/children"):
            return Response([{ "key": "ANNO2345", "data": {"itemType": "annotation", "annotationText": "highlight", "annotationComment": "为什么？", "annotationPageLabel": "3"}}], headers)
        if path.endswith("/fulltext"):
            return Response({"content": "石墨烯 graphene全文", "indexedPages": 2, "totalPages": 5}, headers)
        if path.endswith("/file/view/url"):
            return Response(self.file_url, headers)
        if path == "local/authorize":
            assert json.loads(request.data) == {"appName": "Zotero Study (Codex)"}
            assert request.headers.get("Zotero-server-id") == self.server_id
            return Response({"key": "never-expose-this-key", "remember": self.remember}, headers)
        if path.endswith("/items"):
            if request.method == "GET":
                matches = [n for n in self.notes if query["tag"][0] in [t["tag"] for t in n["data"]["tags"]]]
                return Response(matches, headers)
            assert request.headers["Zotero-api-key"] == "never-expose-this-key"
            assert request.headers["Zotero-server-id"] == self.server_id
            assert len(request.headers["Zotero-write-token"]) == 32
            data = json.loads(request.data)[0]
            note = {"key": "NOTE2345", "version": 2, "data": data}
            if self.partial_failure:
                return Response({"successful": {}, "failed": {"0": {"code": 400}}}, headers)
            self.notes.append(note)
            if self.drop_write_response:
                raise URLError("timeout after commit")
            return Response({"successful": {"0": note}, "failed": {}}, headers)
        raise AssertionError("Unexpected request: " + path)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = ZoteroClient()
        self.fake = FakeZotero()
        self.client.opener = self.fake

    def invoke(self, name, **args):
        return call_tool(self.client, name, args)

    def save(self, **overrides):
        args = dict(parent_key="ABCD2345", title="学习总结 Study", body="GO → rGO\n\n<script>not executable</script>", request_id="study-request-123")
        args.update(overrides)
        return self.invoke("create_study_note", **args)

    def test_status_no_write_and_no_paper_content(self):
        result = self.invoke("connection_status")
        self.assertTrue(result["connected"])
        self.assertNotIn("Graphene", json.dumps(result))
        self.assertTrue(all(r.method == "GET" for r in self.fake.calls))

    def test_unicode_query_encoded_pagination(self):
        self.invoke("search_items", query="石墨烯 & carbon", tag="A&B", start=10, limit=1)
        query = parse_qs(urlsplit(self.fake.calls[-1].full_url).query)
        self.assertEqual(query["q"], ["石墨烯 & carbon"])
        self.assertEqual(query["tag"], ["A&B"])
        self.assertEqual(query["start"], ["10"])

    def test_group_and_collection_scope(self):
        self.invoke("search_items", library="groups/123", collection_key="COLL2345")
        self.assertIn("/groups/123/collections/COLL2345/items/top", self.fake.calls[-1].full_url)

    def test_collections_and_libraries(self):
        self.assertEqual(self.invoke("list_libraries")["groups"][0]["id"], 123)
        self.assertEqual(self.invoke("list_collections")["collections"][0]["data"]["name"], "RBK")

    def test_metadata_children_annotations(self):
        self.assertEqual(self.invoke("get_item", item_key="ABCD2345")["DOI"], "10.1021/nl0717715")
        self.assertEqual(self.invoke("get_children", item_key="ABCD2345")["items"][0]["key"], "PDF23456")
        annotation = self.invoke("get_children", item_key="PDF23456")["items"][0]
        self.assertEqual(annotation["annotationComment"], "为什么？")
        self.assertEqual(annotation["annotationPageLabel"], "3")

    def test_fulltext_chunk_preserves_index_coverage(self):
        result = self.invoke("get_fulltext", attachment_key="PDF23456", max_chars=3)
        self.assertEqual(result["content"], "石墨烯")
        self.assertEqual(result["next_offset"], 3)
        self.assertEqual(result["index_metadata"], {"indexedPages": 2, "totalPages": 5})
        tail = self.invoke("get_fulltext", attachment_key="PDF23456", offset=3)
        self.assertIsNone(tail["next_offset"])

    def test_fulltext_rejects_parent_key(self):
        with self.assertRaises(ToolError):
            self.invoke("get_fulltext", attachment_key="ABCD2345")

    def test_remote_attachment_path_rejected(self):
        with self.assertRaises(ToolError):
            self.invoke("get_attachment_path", attachment_key="PDF23456")

    def test_file_path_decoding(self):
        self.fake.file_url = Path(__file__).resolve().as_uri()
        self.assertEqual(self.invoke("get_attachment_path", attachment_key="PDF23456")["path"], str(Path(__file__).resolve()))

    def test_validation_before_network(self):
        for name, args in [("get_item", {"item_key": "../../etc"}),
                           ("search_items", {"library": "users/1"}),
                           ("search_items", {"limit": True}),
                           ("search_items", {"limit": 101}),
                           ("search_items", {"start": -1}),
                           ("search_items", {"qmode": "bad"}),
                           ("connection_status", {"url": "https://evil.invalid"})]:
            with self.subTest(name=name, args=args), self.assertRaises(ToolError):
                call_tool(self.client, name, args)
        self.assertEqual(self.fake.calls, [])

    def test_create_escapes_html_and_does_not_expose_key(self):
        result = self.save()
        self.assertTrue(result["saved"])
        self.assertEqual(len(self.fake.notes), 1)
        note = self.fake.notes[0]["data"]["note"]
        self.assertNotIn("<script>", note)
        self.assertIn("&lt;script&gt;", note)
        self.assertIn("GO → rGO", note)
        self.assertNotIn("never-expose", json.dumps(result))
        self.assertIsNone(self.client.write_key)

    def test_same_request_deduplicates_across_restart(self):
        self.save()
        self.client = ZoteroClient()
        self.client.opener = self.fake
        self.assertTrue(self.save()["already_existed"])
        self.assertEqual(len(self.fake.notes), 1)
        self.assertEqual(sum(r.method == "POST" for r in self.fake.calls), 2)

    def test_uncertain_write_retry_recovers_existing(self):
        self.fake.drop_write_response = True
        with self.assertRaisesRegex(ToolError, "SAME request_id"):
            self.save()
        self.assertTrue(self.save()["already_existed"])
        self.assertEqual(len(self.fake.notes), 1)

    def test_conflicting_request_does_not_overwrite(self):
        self.save()
        with self.assertRaisesRegex(ToolError, "different content"):
            self.save(body="different")
        self.assertEqual(len(self.fake.notes), 1)

    def test_partial_failure_never_reports_saved(self):
        self.fake.partial_failure = True
        with self.assertRaisesRegex(ToolError, "did not confirm"):
            self.save()
        self.assertEqual(self.fake.notes, [])

    def test_denied_authorization_stops(self):
        self.fake.error_path = "local/authorize"
        with self.assertRaises(APIError):
            self.save()
        self.assertEqual(self.fake.notes, [])
        self.assertEqual(sum(r.method == "POST" for r in self.fake.calls), 1)

    def test_old_zotero_readable_write_unavailable(self):
        self.fake.server_id = None
        self.assertTrue(self.invoke("connection_status")["connected"])
        with self.assertRaisesRegex(ToolError, "Zotero 10"):
            self.save()
        self.assertTrue(all(r.method == "GET" for r in self.fake.calls))

    def test_server_identity_change_clears_authorization(self):
        self.invoke("connection_status")
        self.client.write_key = "sensitive"
        self.fake.server_id = "different-instance"
        with self.assertRaisesRegex(ToolError, "instance changed"):
            self.invoke("get_item", item_key="ABCD2345")
        self.assertIsNone(self.client.write_key)

    def test_expired_key_is_not_retried_automatically(self):
        self.client.write_key = "never-expose-this-key"
        self.client.remember_key = True
        original = self.fake.open
        def fail_write(request, timeout):
            if request.method == "POST":
                raise HTTPError(request.full_url, 401, "expired", {}, None)
            return original(request, timeout)
        self.fake.open = fail_write
        with self.assertRaises(APIError):
            self.save()
        self.assertIsNone(self.client.write_key)

    def test_rate_limit_enforces_pause(self):
        self.fake.error_path = "users/0/items/top"
        self.fake.error_code = 429
        self.assertFalse(self.invoke("connection_status")["connected"])
        self.fake.error_path = None
        with self.assertRaisesRegex(ToolError, "pause"):
            self.invoke("search_items")

    def test_no_remote_endpoint_or_redirect(self):
        for url in ["https://api.zotero.org/api", "http://evil.invalid/api", "http://user:pass@localhost/api"]:
            with self.assertRaises(ValueError):
                ZoteroClient(url)
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.invalid"))

    def test_tool_error_protocol(self):
        result = rpc_response(self.client, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_item", "arguments": {}}})
        self.assertTrue(result["result"]["isError"])
        result = rpc_response(self.client, {"jsonrpc": "2.0", "id": 4, "method": "server/discover"})
        self.assertEqual(result["error"]["code"], -32601)

    def test_stdio_protocol_in_real_subprocess(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        ]
        source = "\n".join(json.dumps(m) for m in messages) + "\ninvalid JSON\n"
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/server.py")], input=source, capture_output=True, text=True, timeout=10)
        results = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(len(results[1]["result"]["tools"]), 9)
        self.assertEqual(results[-1]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
