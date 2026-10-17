"""Developer-authored scenarios and source controls, not independent validation."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pydantic import ValidationError
from carapace_core.friday_goals import GoalScenario, PurchaseGoal, build_goal_scenario, amortisation, paise
from carapace_core.friday_access import permitted_friday_route
from carapace_ai.friday_goal_intake import GoalIntakeRequest, interpret_goal, quoted_value
from carapace_ai.friday_research import ResearchRequest, research_public_topic, safe_source_url
from carapace_integrations.friday_goals_ui import GOALS_JS
import test_friday_surface_isolation as surface_fixture


def request(**updates):
    data={'monthly_income_inr':'50000','monthly_essentials_inr':'30000',
        'monthly_existing_debt_inr':'0','savings_inr':'100000','protected_buffer_inr':'50000',
        'goals':[{'title':'Course','price_inr':'90000','months':2}], 'confirm_assumptions':True}
    data.update(updates)
    return GoalScenario.model_validate(data)


def planner(text, *, metadata=None):
    client=Mock();client.models.generate_content.return_value=SimpleNamespace(text=json.dumps(text),
        candidates=[SimpleNamespace(grounding_metadata=metadata)],usage_metadata=None)
    return SimpleNamespace(mode='VERTEX_AI',model_name='gemini-synthetic-test',_client=client)


class GoalEngineTests(unittest.TestCase):
    def test_single_goal_closed_form(self):
        result=build_goal_scenario(request())
        g=result['baseline']['goals'][0]
        self.assertEqual((g['status'],g['required_inr'],g['gap_inr']),('SCENARIO_FUNDED','90000.00','0.00'))
        self.assertFalse(result['money_moved']);self.assertFalse(result['persisted']);self.assertFalse(result['ai_called'])

    def test_same_savings_cannot_fund_two_goals(self):
        result=build_goal_scenario(request(monthly_income_inr='30000',goals=[
            {'title':'First','price_inr':'50000','months':1},{'title':'Second','price_inr':'50000','months':1}]))
        self.assertEqual(result['baseline']['funded_count'],1)
        self.assertEqual(result['baseline']['goals'][1]['gap_inr'],'50000.00')

    def test_earlier_deadline_has_priority_not_input_order(self):
        result=build_goal_scenario(request(monthly_income_inr='30000',goals=[
            {'title':'Later','price_inr':'50000','months':3},{'title':'Sooner','price_inr':'50000','months':1}]))
        self.assertEqual(result['baseline']['goals'][1]['status'],'SCENARIO_FUNDED')
        self.assertEqual(result['baseline']['goals'][0]['status'],'SHORTFALL')

    def test_missing_buffer_is_funded_first(self):
        result=build_goal_scenario(request(savings_inr='0',goals=[{'title':'Laptop','price_inr':'20000','months':2}]))
        self.assertEqual(result['baseline']['funded_count'],0)
        self.assertEqual(result['baseline']['remaining_buffer_gap_inr'],'10000.00')
        self.assertEqual(result['baseline']['calendar'][0]['buffer_top_up_inr'],'20000.00')

    def test_stress_case_never_claims_more_funded_goals_in_simple_case(self):
        result=build_goal_scenario(request())
        self.assertEqual(result['stress']['funded_count'],0)
        self.assertGreater(Decimal(result['stress']['goals'][0]['gap_inr']),0)

    def test_deficit_is_reported_not_borrowed(self):
        result=build_goal_scenario(request(monthly_income_inr='10000'))
        self.assertEqual(result['baseline']['worst_monthly_deficit_inr'],'20000.00')
        self.assertTrue(all(m['contribution_inr']=='0.00' for m in result['baseline']['calendar']))

    def test_financed_purchase_reduces_capacity_for_later_goal(self):
        result=build_goal_scenario(request(goals=[{'title':'Car','price_inr':'200000','months':1,
            'down_payment_percent':25,'annual_interest_percent':'12','loan_months':12},
            {'title':'Course','price_inr':'60000','months':3}]))
        b=result['baseline'];self.assertEqual(b['goals'][0]['principal_inr'],'150000.00')
        self.assertGreater(Decimal(b['calendar'][1]['new_emi_inr']),0)
        self.assertLess(Decimal(b['calendar'][1]['contribution_inr']),Decimal(b['calendar'][0]['contribution_inr']))

    def test_zero_interest_and_rounding_settle(self):
        self.assertEqual(amortisation(10000,'0',3),{'emi_minor':3333,'interest_minor':0,'total_minor':10000,'final_instalment_minor':3334})
        for principal,rate,months in [(1,'0',360),(10000000,'8.5',240),(99999,'30',360)]:
            a=amortisation(principal,rate,months)
            self.assertEqual(a['total_minor'],principal+a['interest_minor'])

    def test_last_goal_loan_is_checked_beyond_purchase_deadline(self):
        result=build_goal_scenario(request(goals=[{'title':'Large purchase',
            'price_inr':'5000000','months':1,'down_payment_percent':1,
            'annual_interest_percent':'0','loan_months':120}]))
        b=result['baseline']
        self.assertEqual(b['funded_count'],1)  # Down payment only.
        self.assertEqual(b['calendar'][0]['new_emi_inr'],'0.00')
        self.assertEqual(b['peak_planned_emi_inr'],'41250.00')
        self.assertEqual(b['monthly_capacity_at_peak_emi_inr'],'-21250.00')
        self.assertEqual(b['worst_monthly_deficit_inr'],'21250.00')

    def test_random_single_goal_against_simple_oracle(self):
        rng=random.Random(35)
        for _ in range(80):
            saving,buffer,capacity,target,months=[rng.randint(0,100000),rng.randint(0,100000),rng.randint(0,20000),rng.randint(1,200000),rng.randint(1,60)]
            result=build_goal_scenario(request(monthly_income_inr=str(30000+capacity),savings_inr=str(saving),protected_buffer_inr=str(buffer),goals=[{'title':'Test','price_inr':str(target),'months':months}]))
            available=max(0,saving-buffer)+max(0,capacity*months-max(0,buffer-saving))
            self.assertEqual(paise(result['baseline']['goals'][0]['gap_inr']),100*max(0,target-available))

    def test_no_implicit_confirmation_and_strict_types(self):
        with self.assertRaises(ValueError):build_goal_scenario(request(confirm_assumptions=False))
        for field,value in [('monthly_income_inr','NaN'),('savings_inr','-1'),('confirm_assumptions','true')]:
            with self.subTest(field=field),self.assertRaises(ValidationError):request(**{field:value})
        with self.assertRaises(ValidationError):PurchaseGoal(title='X',price_inr='1',months=True)


class GoalIntakeTests(unittest.TestCase):
    def test_generation_schema_preserves_field_named_title(self):
        from carapace_ai.friday_goal_intake import GoalIntake
        from carapace_ai.friday_review import generation_schema
        schema=generation_schema(GoalIntake.model_json_schema())
        self.assertIn('title',schema['properties'])
        self.assertIn('title',schema['required'])
        self.assertNotIn('title',schema['properties']['title'])

    def test_lakh_crore_and_source_binding(self):
        for text,expected in [('₹70 lakh',7000000),('1.5 crore',15000000),('₹1,25,000',125000),('36 months',36)]:
            self.assertEqual(quoted_value(text),Decimal(expected))
        p=planner({'title':'Home','price_inr':{'value':'7000000','quote':'70 lakh'},'months':{'value':'36','quote':'36 months'}})
        result=interpret_goal(p,GoalIntakeRequest(message='Home for 70 lakh in 36 months.',confirm_send_to_gemini=True))
        self.assertEqual(result['fields'],{'price_inr':'7000000','months':36})
        self.assertIn('monthly_income_inr',result['missing'])
        self.assertTrue(result['needs_confirmation'])

    def test_hallucinated_value_or_quote_rejected(self):
        for fact in [{'value':'8000000','quote':'70 lakh'},{'value':'7000000','quote':'invented 70 lakh'}]:
            p=planner({'title':'Home','price_inr':fact})
            with self.assertRaises(ValueError):interpret_goal(p,GoalIntakeRequest(message='Home for 70 lakh.',confirm_send_to_gemini=True))

    def test_no_silent_zero_no_model_without_consent(self):
        p=planner({'title':'Purchase'})
        with self.assertRaises(ValueError):interpret_goal(p,GoalIntakeRequest(message='A purchase goal'))
        p._client.models.generate_content.assert_not_called()
        result=interpret_goal(p,GoalIntakeRequest(message='A purchase goal',confirm_send_to_gemini=True))
        self.assertEqual(result['fields'],{})


class ResearchTests(unittest.TestCase):
    def result(self,metadata):
        p=planner({},metadata=metadata)
        p._client.models.generate_content.return_value.text='* **Example:** Not established. Confirm with the source.'
        return p

    def metadata(self):
        return SimpleNamespace(grounding_chunks=[SimpleNamespace(web=SimpleNamespace(uri='https://www.rbi.org.in/',title='RBI'))],
            search_entry_point=SimpleNamespace(rendered_content='<div><a href="https://www.google.com/search?q=loan" target="_blank">Search</a></div>'),grounding_supports=[SimpleNamespace()])

    def test_requires_actual_provider_sources_and_search_suggestions(self):
        for metadata in [None,SimpleNamespace(grounding_chunks=[]),SimpleNamespace(grounding_chunks=self.metadata().grounding_chunks)]:
            with self.assertRaises(RuntimeError):research_public_topic(self.result(metadata),ResearchRequest(topic='GOLD',confirm_public_search=True))

    def test_public_research_excludes_records_and_history(self):
        p=self.result(self.metadata());result=research_public_topic(p,ResearchRequest(topic='FUEL',city='Chennai',confirm_public_search=True))
        self.assertFalse(result['private_records_used']);self.assertFalse(result['quote_feed']);self.assertFalse(result['independently_fact_checked'])
        self.assertEqual(result['sources'][0]['title'],'RBI')
        config=p._client.models.generate_content.call_args.kwargs
        self.assertEqual(len(config['config'].tools),1)
        self.assertNotIn('statement',config['contents'].lower())

    def test_card_citations_use_provider_segments_and_chunk_indices(self):
        metadata=self.metadata()
        metadata.grounding_supports=[SimpleNamespace(
            segment=SimpleNamespace(text='Not established. Confirm with the source.'),
            grounding_chunk_indices=[0,99,True])]
        result=research_public_topic(self.result(metadata),ResearchRequest(topic='FUEL',confirm_public_search=True))
        self.assertEqual(result['facts'][0]['source_ids'],[1])
        self.assertEqual(result['citations'][0]['source_ids'],[1])
        self.assertEqual(result['sources'][0]['id'],1)

    def test_no_request_without_consent(self):
        p=self.result(self.metadata())
        with self.assertRaises(ValueError):research_public_topic(p,ResearchRequest(topic='GOLD'))
        p._client.models.generate_content.assert_not_called()

    def test_directive_investment_output_rejected(self):
        p=self.result(self.metadata())
        p._client.models.generate_content.return_value.text='* **Gold:** You should buy now.'
        with self.assertRaises(RuntimeError):research_public_topic(p,ResearchRequest(topic='GOLD',confirm_public_search=True))

    def test_private_context_flags_not_admitted(self):
        with self.assertRaises(ValidationError):ResearchRequest.model_validate({'topic':'GOLD','include_statements':True})

    def test_invalid_urls_and_private_inputs(self):
        for url in ['javascript:alert(1)','http://example.com','https://localhost/','https://127.0.0.1/','https://a:b@example.com','https://[::1]/','https://example.com:444/']:
            self.assertFalse(safe_source_url(url),url)
        self.assertTrue(safe_source_url('https://vertexaisearch.cloud.google.com/grounding-api-redirect/test'))
        for q in ['My account 123456789012','my OTP is 123456','me@example.com']:
            with self.assertRaises(ValidationError):ResearchRequest(topic='QUESTION',question=q)


class GoalApiTests(unittest.TestCase):
    def setUp(self):
        self.fixture=surface_fixture.ConsumerApiSurfaceTests('runTest');self.addCleanup(self.fixture.doCleanups)
        _,self.app,self.client=self.fixture.api();self.headers=self.fixture.headers

    def test_new_routes_authenticated_and_admitted_without_execution(self):
        for suffix in ['goals/preview','goals/interpret','research']:
            path='/v1/friday/'+suffix
            self.assertTrue(permitted_friday_route('POST',path,legacy_demo_enabled=False))
            self.assertIn(path,self.client.get('/openapi.json').json()['paths'])
        response=self.client.post('/v1/friday/goals/preview',headers=self.headers,json=request().model_dump())
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()['money_moved'])

    def test_model_tools_reject_absent_consent(self):
        for suffix,payload in [('goals/interpret',{'message':'A purchase'}),('research',{'topic':'GOLD'})]:
            response=self.client.post('/v1/friday/'+suffix,headers=self.headers,json=payload)
            self.assertEqual(response.status_code,422,response.text)

    def test_local_provider_does_not_fake_live_search(self):
        response=self.client.post('/v1/friday/research',headers=self.headers,json={'topic':'GOLD','confirm_public_search':True})
        self.assertEqual(response.status_code,503)

    def test_scenario_does_not_write_owner_state(self):
        before=self.app.state.financial_friday.portfolio.view('one')
        self.client.post('/v1/friday/goals/preview',headers=self.headers,json=request().model_dump())
        self.assertEqual(before,self.app.state.financial_friday.portfolio.view('one'))


class GoalUiTests(unittest.TestCase):
    def test_safe_output_and_explicit_search(self):
        self.assertNotIn('innerHTML',GOALS_JS)
        self.assertIn("frame.setAttribute('sandbox','allow-popups allow-popups-to-escape-sandbox')",GOALS_JS)
        self.assertNotIn('allow-scripts',GOALS_JS)
        self.assertNotIn('setInterval',GOALS_JS)
        self.assertIn('confirm_public_search:true',GOALS_JS)
        self.assertIn('confirm_assumptions:assumptionCheck.checked',GOALS_JS)
        self.assertIn('goalEpoch++',GOALS_JS)
        self.assertIn('researchEpoch++',GOALS_JS)


if __name__=='__main__':unittest.main()
