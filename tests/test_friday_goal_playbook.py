"""Independent exact-money expectations for the visual goal playbook."""
from datetime import date
import random
import shutil
import subprocess
import unittest
from carapace_core.friday_roadmap import RoadmapPlan, calculate_roadmap


def make_plan(**changes):
    return RoadmapPlan(**{**dict(title='Artificial travel plan', kind='SAVINGS',
        target_inr='120000', months=12, monthly_income_inr='50000',
        monthly_essentials_inr='30000', monthly_existing_debt_inr='0',
        savings_inr='70000', protected_buffer_inr='50000'), **changes})


def calc(**changes):
    return calculate_roadmap(make_plan(**changes), started=date(2026,10,18), today=date(2026,10,18))


class GoalPlaybookTests(unittest.TestCase):
    def test_allocation_balances_exactly_without_calling_room_safe(self):
        b=calc()['playbook']
        self.assertEqual([v['amount_inr'] for v in b['allocation']['slices']],
                         ['30000.00','0.00','8333.34','11666.66'])
        self.assertEqual(b['allocation']['goal_income_percent'],16)
        self.assertFalse(b['investment_returns_assumed']); self.assertFalse(b['money_moved'])

    def test_explicit_pressure_cases_and_simple_not_predicted_inflation(self):
        cases=calc()['playbook']['scenarios']
        self.assertEqual([c['code'] for c in cases],['PLAN','PRESSURE','PAUSE','COST'])
        self.assertEqual(cases[0]['end_inr'],'120000.08')
        self.assertEqual(cases[2]['end_inr'],'111666.74')
        self.assertEqual(cases[2]['gap_inr'],'8333.26')
        self.assertEqual(cases[3]['target_inr'],'126000.00')
        self.assertEqual(cases[3]['gap_inr'],'5999.92')
        self.assertIn('not a prediction',cases[3]['assumption'])

    def test_pressure_can_miss_even_when_cash_plan_fits(self):
        b=calc(monthly_income_inr='40000')['playbook']
        self.assertTrue(b['scenarios'][0]['reaches_target'])
        self.assertEqual(b['scenarios'][1]['end_inr'],'56000.00')
        self.assertEqual(b['scenarios'][1]['gap_inr'],'64000.00')

    def test_reserve_is_filled_once_before_projection(self):
        b=calc(savings_inr='10000')['playbook']
        self.assertEqual(b['scenarios'][0]['end_inr'],'120000.08')
        self.assertEqual(b['scenarios'][2]['end_inr'],'106666.74')

    def test_concrete_alternatives_reconcile_at_current_capacity(self):
        b=calc(monthly_income_inr='35000')['playbook']
        self.assertEqual([v['code'] for v in b['alternatives']],
                         ['SMALLER_TARGET','MORE_TIME','EXTRA_CAPACITY'])
        a,btime,extra=b['alternatives']
        self.assertEqual(a['target_inr'],'80000.00')
        self.assertEqual(btime['months'],20)
        self.assertEqual(btime['date'],'2028-06-18')
        self.assertEqual(extra['extra_monthly_inr'],'3333.34')

    def test_no_capacity_no_division_by_zero_or_fake_date(self):
        b=calc(monthly_income_inr='0',monthly_existing_debt_inr='5000')['playbook']
        self.assertIsNone(b['allocation']['goal_income_percent'])
        self.assertEqual(b['allocation']['overspend_inr'],'35000.00')
        self.assertEqual(b['alternatives'][0]['code'],'NO_TIMELINE')
        self.assertIsNone(b['alternatives'][0]['date'])
        self.assertFalse(b['scenarios'][0]['reaches_target'])

    def test_month_one_pause_does_not_invent_negative_contribution(self):
        b=calc(months=1)['playbook']
        self.assertEqual(b['scenarios'][2]['end_inr'],'20000.00')

    def test_actual_report_updates_all_views_and_undo_reverts(self):
        p=make_plan();day=date(2026,10,18)
        a=calculate_roadmap(p,[dict(amount_minor=100000)],day,day)
        u=calculate_roadmap(p,[dict(amount_minor=100000,undone=True)],day,day)
        self.assertEqual(a['current_inr'],'21000.00')
        self.assertEqual(u['playbook'],calc()['playbook'])

    def test_late_milestone_and_unknown_factors_not_hidden(self):
        b=calc(monthly_income_inr='35000')['playbook']
        self.assertTrue(b['checkpoints'][-1]['after_deadline'])
        self.assertEqual(b['checkpoints'][-1]['target_inr'],'120000.00')
        self.assertEqual(len(b['not_established']),5)

    def test_expired_date_uses_no_future_months(self):
        s=calculate_roadmap(make_plan(),started=date(2024,1,1),today=date(2026,10,18))
        self.assertEqual(s['playbook']['scenarios'][0]['end_inr'],'20000.00')
        self.assertEqual(s['playbook']['scenarios'][3]['target_inr'],'120000.00')

    def test_target_already_reached_does_not_demand_contributions(self):
        s=calc(savings_inr='200000')
        self.assertEqual(s['recommended_monthly_inr'],'0.00')
        self.assertEqual(s['playbook']['alternatives'],[])

    def test_budget_and_reserve_conservation_across_independent_cases(self):
        from decimal import Decimal
        rng=random.Random(380)
        for _ in range(100):
            income,living,debt,savings,reserve,target=[rng.randrange(0,200000) for i in range(6)]
            b=calc(monthly_income_inr=str(income),monthly_essentials_inr=str(living),
                   monthly_existing_debt_inr=str(debt),savings_inr=str(savings),
                   protected_buffer_inr=str(reserve),target_inr=str(max(1,target)))['playbook']
            amounts=[Decimal(v['amount_inr']) for v in b['allocation']['slices']]
            self.assertEqual(sum(amounts),max(income,living+debt))
            self.assertTrue(all(c['end_inr'][0]!='-' for c in b['scenarios']))
            self.assertEqual(b['scenarios'][0]['reaches_target'],
                             Decimal(b['scenarios'][0]['end_inr'])>=max(1,target))

    @unittest.skipUnless(shutil.which('node'),'Node runs in native/CI environments')
    def test_visual_and_explicit_action_contract(self):
        from carapace_integrations.friday_roadmap_ui import ROADMAP_JS
        r=subprocess.run(['node','--check'],input=ROADMAP_JS,text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertNotIn('__GOAL_PLAYBOOK__',ROADMAP_JS)
        self.assertNotIn('function lineChart',ROADMAP_JS)
        self.assertIn('Continue with Gemini',ROADMAP_JS)
        self.assertIn('Use calculator without AI',ROADMAP_JS)
        self.assertNotIn('consent.checked',ROADMAP_JS)
        self.assertIn('confirm_store:true',ROADMAP_JS)
        self.assertIn('Pressure tests',ROADMAP_JS)
        self.assertNotIn('innerHTML',ROADMAP_JS)


if __name__=='__main__':unittest.main()
