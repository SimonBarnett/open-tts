import io
import unittest
from pathlib import Path
from unittest import mock

from open_tts.__main__ import cmd_render, main


class TestCliRenderMessage(unittest.TestCase):
    def test_success_line_is_cp1252_safe(self) -> None:
        args = mock.Mock(
            script="interviews/partner-smart-catalogue.yaml",
            output=None,
            skip_tts=True,
            no_video=True,
        )
        out = Path("interviews/output/partner-smart-catalogue")
        buf = io.StringIO()
        with mock.patch("open_tts.__main__.render_interview", return_value=out), mock.patch(
            "open_tts.__main__.print",
            side_effect=lambda *a, **k: buf.write(" ".join(str(x) for x in a) + "\n"),
        ), mock.patch.object(Path, "is_file", return_value=True):
            code = cmd_render(args)
        self.assertEqual(code, 0)
        line = buf.getvalue()
        self.assertIn("Rendered interview ->", line)
        line.encode("cp1252")

    def test_main_configures_stdio(self) -> None:
        with mock.patch("open_tts.__main__._configure_stdio") as conf, mock.patch(
            "argparse.ArgumentParser.parse_args",
            side_effect=SystemExit(2),
        ):
            with self.assertRaises(SystemExit):
                main([])
        conf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
