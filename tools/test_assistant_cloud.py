"""Offline controls: no credentials or network without explicit live flag."""
from pathlib import Path
import unittest
from unittest.mock import patch
import verify_assistant_cloud as verifier


class AssistantCloudControls(unittest.TestCase):
    def test_flag_required_before_credentials_or_network(self):
        with patch('sys.argv',['verify','--url','https://sample.run.app','--project','synthetic']), \
             patch.object(verifier.subprocess,'check_output') as cli,patch.object(verifier,'urlopen') as network:
            with self.assertRaises(SystemExit):verifier.main()
            cli.assert_not_called();network.assert_not_called()

    def test_bad_origin_cannot_send_identity_to_another_host(self):
        with patch('sys.argv',['verify','--url','https://example.com','--project','synthetic','--run-live']), \
             patch.object(verifier.subprocess,'check_output') as cli:
            with self.assertRaises(ValueError):verifier.main()
            cli.assert_not_called()

    def test_verifier_has_no_bank_or_permissions_mutations(self):
        source=Path(verifier.__file__).read_text()
        self.assertNotIn('add-iam-policy-binding',source)
        self.assertNotIn('/friday/tasks',source)
        self.assertNotIn('print(secret',source)
        self.assertIn("'human_microphone_used':False",source)


if __name__=='__main__':unittest.main()
