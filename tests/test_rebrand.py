import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

from cardinal import Cardinal, get_cardinal
from first_setup import create_config_obj, default_config
from FunPayAPI import Account, Runner
from funpaynext import FunPayNEXT, get_app
import handlers
from project_info import REPOSITORY_URL, VERSION
from tg_bot import utils
from tg_bot.bot import TGBot
from Utils import bot_tools, cardinal_tools, updater
from Utils.config_loader import load_main_config


ROOT = Path(__file__).resolve().parents[1]


def account(account_id=1):
    result = Account("test")
    result.id = account_id
    result.username = "seller"
    result._Account__initiated = True
    return result


def response(payload, *, links=None):
    return Mock(status_code=200, json=Mock(return_value=payload), links=links or {})


def chat_text(message_id, text):
    return {
        "tag": "chat-tag",
        "data": {"html": (
            f'<a class="contact-item" data-id="42" data-node-msg="{message_id}" data-user-msg="1">'
            '<div class="media-user-name">buyer</div>'
            f'<div class="contact-item-message">{text}</div>'
            '</a>'
        )},
    }


class RebrandTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.root)

    def test_first_start_and_legacy_configuration(self):
        shutil.copyfile(ROOT / "main.py", "main.py")
        inputs = ["f" * 32, "", "", "1:synthetic", "Password1", ""]
        with (
            patch("builtins.input", side_effect=inputs),
            patch("first_setup.time.sleep"),
            patch("first_setup.telebot.TeleBot.get_me", return_value=SimpleNamespace(username="funpaynext_test_bot")),
            patch("Utils.logger.configure_logging"),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
            self.assertRaises(SystemExit),
        ):
            runpy.run_path(str(self.root / "main.py"), run_name="__main__")

        self.assertIn(f"FunPayNEXT v{VERSION}", stdout.getvalue())
        config = load_main_config("configs/_main.cfg")
        self.assertNotIn("watermark", config["Other"])
        self.assertNotIn("watermark", config["OrderConfirm"])
        config["Other"]["watermark"] = "obsolete"
        config["OrderConfirm"]["watermark"] = "1"
        with open("configs/_main.cfg", "w", encoding="utf-8") as file:
            config.write(file)
        with (
            patch.object(FunPayNEXT, "init") as init,
            patch("Utils.logger.configure_logging"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            runpy.run_path(str(self.root / "main.py"), run_name="__main__")
        init.return_value.run.assert_called_once()

    def test_plugin_imports_and_watermark_argument(self):
        self.assertIs(Cardinal, FunPayNEXT)
        self.assertIs(get_cardinal, get_app)
        self.assertIs(cardinal_tools, bot_tools)
        app = object.__new__(FunPayNEXT)
        app.MAIN_CFG = create_config_obj(default_config)
        app.MAIN_CFG["Other"]["watermark"] = "obsolete"
        app.account = Mock()
        app.send_message(42, "buyer text", watermark=True)
        app.account.send_message.assert_called_once()
        self.assertEqual(app.account.send_message.call_args.args[1], "buyer text")

    def test_new_text_and_images_have_no_outgoing_marks(self):
        seller = account()
        runner = Runner(seller)
        seller.abuse_runner = Mock(return_value=response({"response": {"error": None}, "objects": []}))
        seller.send_message(42, "plain text")
        self.assertEqual(seller.abuse_runner.call_args.kwargs["request"]["data"]["content"], "plain text")
        self.assertFalse(runner.is_by_bot(42, 0))

        seller.method = Mock(side_effect=[
            response({"fileId": 99}), response({"content": "saved"})
        ])
        seller.upload_image(io.BytesIO(b"image"))
        body = seller.method.call_args.args[3].to_string()
        self.assertIn(b'filename="image.png"', body)
        self.assertNotIn(b"Cardinal", body)
        seller.send_review("ORDER", "plain review")
        self.assertEqual(seller.method.call_args.args[3]["text"], "plain review")

    def test_sent_ids_survive_restart_and_are_scoped_to_the_account(self):
        database = str(self.root / "sent.sqlite3")
        seller = account()
        Runner(seller, sent_messages_path=database)
        seller.abuse_runner = Mock(return_value=response({
            "response": {"error": None},
            "objects": [{
                "type": "chat_node", "tag": "node-tag", "data": {
                    "node": {"id": 42, "name": "users-1-2", "silent": False},
                    "messages": [{"id": 912, "html": '<div class="chat-msg-text">plain text</div>'}],
                },
            }],
        }))
        seller.send_message(42, "plain text", update_last_saved_message=True, add_to_ignore_list=False)

        for old_mode in (False, True):
            with self.subTest(old_mode=old_mode):
                restarted = account()
                runner = Runner(restarted, old_mode, sent_messages_path=database)
                event = runner.parse_chat_updates(chat_text(912, "plain text"))[0]
                self.assertTrue(event.chat.last_by_bot)
                self.assertFalse(runner.is_by_bot(43, 912))
        other = Runner(account(99), sent_messages_path=database)
        self.assertFalse(other.is_by_bot(42, 912))

    def test_reading_existing_chat_history_keeps_legacy_recognition(self):
        seller = account()
        runner = Runner(seller)
        runner.mark_as_by_bot(42, 6)
        messages = [
            {"id": 5, "author": 1, "html": f'<div class="chat-msg-text">{seller.bot_character}old</div>'},
            {"id": 6, "author": 1, "html": '<a class="chat-img-link" href="/image"><img alt="image.png"></a>'},
            {"id": 7, "author": 2, "html": '<div class="chat-msg-text">buyer text</div>'},
        ]
        [old, image, buyer] = seller.parse_chats_histories({42: "buyer"}, [{
            "type": "chat_node", "tag": "tag", "data": {
                "node": {"id": 42, "name": "users-1-2", "silent": False}, "messages": messages,
            },
        }])[42]
        self.assertEqual(old.text, "old")
        self.assertTrue(old.by_bot)
        self.assertTrue(image.by_bot)
        self.assertFalse(buyer.by_bot)

    def test_auto_response_ignores_own_sends_in_both_modes(self):
        for old_mode, event in (
            (True, SimpleNamespace(chat=SimpleNamespace(last_by_bot=True))),
            (False, SimpleNamespace(message=SimpleNamespace(author_id=1))),
        ):
            app = SimpleNamespace(autoresponse_enabled=True, old_mode_enabled=old_mode, account=account())
            with patch.object(handlers, "Thread") as thread:
                handlers.send_response_handler(app, event)
                thread.assert_not_called()

    def test_auto_response_still_replies_to_buyer(self):
        config = create_config_obj({"hi": {"enabled": "1", "response": "Configured reply"}})
        app = SimpleNamespace(autoresponse_enabled=True, old_mode_enabled=False,
                              account=account(), bl_response_enabled=False, AR_CFG=config, send_message=Mock())
        message = Mock(author_id=2, chat_id=42, chat_name="buyer", author="buyer")
        message.__str__ = lambda _: "hi"
        with patch.object(bot_tools, "format_msg_text", return_value="Configured reply"), \
                patch.object(handlers, "Thread") as thread:
            handlers.send_response_handler(app, SimpleNamespace(message=message))
        self.assertEqual(thread.call_args.kwargs["args"], (42, "Configured reply", "buyer"))
        thread.return_value.start.assert_called_once()

    def test_auto_delivery_sends_exact_configured_text(self):
        app = object.__new__(FunPayNEXT)
        app.MAIN_CFG = create_config_obj(default_config)
        app.account = Mock()
        app.account.get_chat_by_name.return_value = SimpleNamespace(id=42)
        order = SimpleNamespace(id="ORDER", buyer_username="buyer", chat_id=42)
        event = SimpleNamespace(order=order, config_section_obj={"response": "Configured delivery"})
        with patch.object(bot_tools, "format_order_text", return_value="Configured delivery"):
            handlers.deliver_goods(app, event)
        self.assertTrue(event.delivered)
        self.assertEqual(app.account.send_message.call_args.args[1], "Configured delivery")

    def test_legacy_notifications_keep_order_and_critical_messages(self):
        path = Path("storage/cache/notifications.json")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"1": {"4": 1, "5r": 1, "11": 1, "12": 1, "13": 1, "14": 1},
                                    "2": {"4": 0, "11": 1}}), encoding="utf-8")
        telegram = object.__new__(TGBot)
        telegram.notification_settings = utils.load_notification_settings()
        telegram.bot = Mock()
        self.assertEqual(telegram.notification_settings, {"1": {"4": 1, "5r": 1, "13": 1}, "2": {"4": 0}})
        telegram.send_notification("obsolete", notification_type="14", pin=True)
        telegram.bot.send_message.assert_not_called()
        telegram.send_notification("order", notification_type=utils.NotificationTypes.new_order)
        telegram.bot.send_message.assert_called_once_with("1", "order")
        telegram.bot.reset_mock()
        telegram.send_notification("critical", notification_type=utils.NotificationTypes.critical, pin=True)
        telegram.bot.send_message.assert_called_once_with("1", "critical")
        telegram.bot.pin_chat_message.assert_called_once()

    def test_telegram_profile_replaces_old_project_links_and_names(self):
        telegram = object.__new__(TGBot)
        telegram.cardinal = SimpleNamespace(VERSION=VERSION)
        telegram.bot = Mock()
        telegram.bot.get_me.return_value.full_name = "FunPay Cardinal"
        telegram.bot.get_my_short_description.return_value.short_description = "Old promotion"
        telegram.bot.get_my_description.return_value.description = "Old promotion"
        telegram.edit_bot()
        telegram.bot.set_my_name.assert_called_once_with("FunPayNEXT")
        telegram.bot.set_my_short_description.assert_called_once_with(f"FunPayNEXT | {REPOSITORY_URL}")
        self.assertEqual(telegram.bot.set_my_description.call_count, 4)
        for call in telegram.bot.set_my_description.call_args_list:
            self.assertIn(REPOSITORY_URL, call.args[0])
            self.assertNotIn("t.me/", call.args[0])

    @patch("Utils.updater.requests.get")
    def test_releases_are_from_the_fork_and_install_in_version_order(self, get):
        get.return_value = response([])
        self.assertEqual(updater.get_new_releases("v0.1.0"), 4)
        get.side_effect = [
            response([{"tag_name": "v0.3.0"}], links={"next": {}}),
            response([
                {"tag_name": "v0.1.0"}, {"tag_name": "v0.1.3", "body": None},
                {"tag_name": "v0.2.0", "body": "#unskippable"},
                {"tag_name": "v0.4.0", "prerelease": True},
            ]),
        ]
        releases = updater.get_new_releases("v0.1.0")
        self.assertEqual([item.name for item in releases], ["v0.1.3", "v0.2.0"])
        self.assertTrue(all(item.sources_link.startswith(f"{updater.RELEASE_API}/zipball/") for item in releases))
        self.assertEqual(updater.RELEASE_API, REPOSITORY_URL.replace("github.com/", "api.github.com/repos/"))
        self.assertEqual(get.call_args.args[0], f"{updater.RELEASE_API}/releases")

    def test_update_replaces_code_and_preserves_user_files(self):
        for directory in ("storage/cache", "plugins", "configs", "logs"):
            Path(directory).mkdir(parents=True)
        config = Path("configs/_main.cfg")
        config.write_bytes(b"original")
        plugin = Path("plugins/custom.py")
        plugin.write_bytes(b"custom")
        obsolete = Path("announcements.py")
        obsolete.touch()
        manifest = (ROOT / "delete.json").read_text(encoding="utf-8")
        self.assertEqual(updater.create_backup(), 0)

        with ZipFile("storage/cache/update.zip", "w") as archive:
            archive.writestr("revision/", "")
            archive.writestr("revision/delete.json", manifest)
            archive.writestr("revision/funpaynext.py", "new code")
            archive.writestr("revision/configs/_main.cfg", "archive configuration")
        self.assertEqual(updater.install_release(updater.extract_update_archive()), 0)
        self.assertFalse(obsolete.exists())
        self.assertEqual(Path("funpaynext.py").read_bytes(), b"new code")
        self.assertEqual(config.read_bytes(), b"original")
        self.assertEqual(plugin.read_bytes(), b"custom")

        config.write_bytes(b"modified")
        shutil.copyfile("backup.zip", "storage/cache/backup.zip")
        self.assertTrue(updater.extract_backup_archive())
        self.assertTrue(updater.install_backup())
        self.assertEqual(config.read_bytes(), b"original")
