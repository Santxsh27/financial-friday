import unittest
from carapace_ai.friday_tasks import TaskProposal, TaskEvidenceError, validate_task_evidence


class TaskEvidenceTests(unittest.TestCase):
    def proposal(self,**changes):
        return TaskProposal.model_validate({'action':'PREPARE_VERIFICATION','explanation':'Prepare only an unsent verification message.',**changes})

    def test_duplicate_source_identity_is_rejected(self):
        with self.assertRaises(TaskEvidenceError) as raised:
            validate_task_evidence(self.proposal(),[{'source_id':'request','source_text':'one'},{'source_id':'request','source_text':'two'}])
        self.assertEqual(raised.exception.reason,'DUPLICATE_SOURCE')

    def test_unsupported_citation_is_not_silently_dropped(self):
        with self.assertRaises(TaskEvidenceError) as raised:
            validate_task_evidence(self.proposal(evidence_ids=['unavailable']),[{'source_id':'request','source_text':'ordinary text'}])
        self.assertEqual(raised.exception.reason,'UNAVAILABLE_CITATION')

    def test_exact_quote_is_required(self):
        finding={'kind':'COERCION','source_id':'request','quote':'pay me right now','reason':'Potential time-pressure payment demand.'}
        with self.assertRaises(TaskEvidenceError):validate_task_evidence(self.proposal(findings=[finding]),[{'source_id':'request','source_text':'A polite ordinary request'}])
        admitted=validate_task_evidence(self.proposal(findings=[finding]),[{'source_id':'request','source_text':'The message says pay me right now.'}])
        self.assertEqual(admitted['findings'][0]['quote'],'pay me right now')

    def test_admission_has_no_financial_execution_side_effect(self):
        proposal=self.proposal(action='PREPARE_PAYMENT',bill_reference='untrusted')
        admitted=validate_task_evidence(proposal,[{'source_id':'request','source_text':'ordinary text'}])
        # Exact quotations alone are not payment authorization. The separate
        # service gate must still enforce provider identity, rules and consent.
        self.assertEqual(admitted['action'],'PREPARE_PAYMENT')
        self.assertNotIn('payment_authorized',admitted)


if __name__=='__main__':unittest.main()
