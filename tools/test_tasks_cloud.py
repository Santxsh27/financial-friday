import json
import unittest
from verify_tasks_cloud import api_request


class TaskCloudVerificationTests(unittest.TestCase):
    def test_explicit_rule_update_uses_put_not_default_post(self):
        url='https://test-api.run.app'
        self.assertEqual(api_request(url,'/v1/friday/mandate',{}).get_method(),'GET')
        request=api_request(url,'/v1/friday/mandate',{}, {'automatic_sandbox_execution':False},method='PUT')
        self.assertEqual(request.get_method(),'PUT')
        self.assertFalse(json.loads(request.data)['automatic_sandbox_execution'])
        self.assertEqual(api_request(url,'/v1/friday/tasks',{}, {'message':'Test request'}).get_method(),'POST')


if __name__=='__main__':
    unittest.main()
