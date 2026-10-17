"""Offline safety controls for the release verifier, never an actual cloud call."""
import unittest
from unittest.mock import patch
import verify_submission_cloud as verifier


class SubmissionCloudToolTests(unittest.TestCase):
    def test_fixed_origin_rejects_credentials_paths_queries_and_non_cloud_urls(self):
        for url in ('http://test.run.app','https://user@sample.run.app','https://sample.run.app/path',
                    'https://sample.run.app:443','https://sample.run.app?token=x','https://example.com'):
            with self.subTest(url=url),self.assertRaises(ValueError):verifier.validated_origin(url)
        self.assertEqual(verifier.validated_origin('https://sample.run.app/'),'https://sample.run.app')

    def test_no_live_flag_does_not_read_credentials_or_make_requests(self):
        with patch('sys.argv',['verify','--url','https://sample.run.app','--project','synthetic']), \
             patch.object(verifier.subprocess,'check_output') as cli,patch.object(verifier,'urlopen') as network:
            with self.assertRaises(SystemExit):verifier.main()
            cli.assert_not_called();network.assert_not_called()

    def test_no_financial_executor_or_public_identity_override_is_in_verifier(self):
        from pathlib import Path
        source=Path(verifier.__file__).read_text()
        self.assertNotIn('/v1/friday/tasks',source.replace("'/v1/friday/tasks' not in schema",''))
        self.assertNotIn('add-iam-policy-binding',source)
        self.assertIn('synthetic_workspace_cleanup_verified',source)
        self.assertNotIn('print(secret',source)


if __name__=='__main__':unittest.main()
