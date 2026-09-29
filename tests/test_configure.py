import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from configure import generate_config, install_command


class ConfigureTests(unittest.TestCase):
    def test_paths_with_spaces_are_separate_arguments(self):
        root = Path("/some folder/zotero-study")
        command = install_command(root, "/python folder/python3")
        self.assertEqual(command[-2:], ["/python folder/python3", "/some folder/zotero-study/scripts/server.py"])

    def test_config_matches_launch_command(self):
        root = Path("/example/zotero-study")
        config = generate_config(root, "/example/python3")["mcpServers"]["zotero-study"]
        self.assertEqual(config["command"], "/example/python3")
        self.assertEqual(config["args"], [str(root / "scripts/server.py")])
        self.assertGreater(config["tool_timeout_sec"], 55)

    def test_clean_checkout_generates_only_local_configuration(self):
        source = Path(__file__).resolve().parents[1] / "scripts/configure.py"
        with tempfile.TemporaryDirectory(prefix="zotero study ") as directory:
            root = Path(directory).resolve()
            (root / "scripts").mkdir()
            shutil.copyfile(source, root / "scripts/configure.py")
            process = subprocess.run([sys.executable, str(root / "scripts/configure.py")], capture_output=True, text=True, check=True)
            config = json.loads((root / ".mcp.json").read_text())
            self.assertEqual(config["mcpServers"]["zotero-study"]["args"], [str(root / "scripts/server.py")])
            self.assertIn("Optional standalone", process.stdout)


if __name__ == "__main__":
    unittest.main()
