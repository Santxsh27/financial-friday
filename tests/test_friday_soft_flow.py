"""Motion can decorate interaction; it cannot create actions or certainty."""
import json
import shutil
import subprocess
import unittest

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_soft_flow import FLOW_CSS, FLOW_JS, FLOW_HELPERS
from carapace_integrations.friday_chat_ui import CHAT_JS
from carapace_integrations.friday_cashflow_ui import CASHFLOW_JS


class SoftFlowTests(unittest.TestCase):
    def run_helper(self, code):
        node=shutil.which('node')
        if not node:self.skipTest('Node optional for presentation execution checks')
        result=subprocess.run([node],input=FLOW_HELPERS+code,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_motion_requires_on_fine_visible_and_no_system_reduction(self):
        result=self.run_helper("""
process.stdout.write(JSON.stringify([
fridayFlowAllowed('on',false,true,false),fridayFlowAllowed('off',false,true,false),
fridayFlowAllowed('on',true,true,false),fridayFlowAllowed('on',false,false,false),
fridayFlowAllowed('on',false,true,true),fridayFlowAllowed('invalid',false,true,false)]));
""")
        self.assertEqual(result,[True,False,False,False,False,False])

    def test_tilt_is_bounded_and_invalid_dimensions_are_neutral(self):
        result=self.run_helper("""
process.stdout.write(JSON.stringify([fridayFlowOffset(50,50,100,100),
fridayFlowOffset(-500,900,100,100),fridayFlowOffset(1,2,0,100),fridayFlowOffset(NaN,2,100,100)]));
""")
        self.assertEqual(result[0],{'rx':0,'ry':0,'x':50,'y':50})
        self.assertEqual(result[1],{'rx':-.7,'ry':-.7,'x':0,'y':100})
        self.assertEqual(result[2],result[0]);self.assertEqual(result[3],result[0])

    def test_many_moves_queue_one_frame_and_zero_id_is_cancelled(self):
        result=self.run_helper("""
let queues=0,cancelled=[],cleared=[],applied=[],callback;
const c=fridayFlowController({enabled:()=>true,frame:fn=>{queues++;callback=fn;return 0;},
cancel:id=>cancelled.push(id),clear:target=>cleared.push(target),measure:()=>({left:0,top:0,width:100,height:100}),
apply:(target,point)=>applied.push(point)});
c.move('one',10,10);c.move('one',90,90);callback();c.move('one',20,20);c.reset();
process.stdout.write(JSON.stringify({queues,cancelled,cleared,applied}));
""")
        self.assertEqual(result['queues'],2)
        self.assertEqual(result['cancelled'],[0])
        self.assertEqual(result['cleared'],['one'])
        self.assertEqual(len(result['applied']),1)
        self.assertAlmostEqual(result['applied'][0]['ry'],.56)

    def test_target_change_and_disabled_motion_clear_without_another_frame(self):
        result=self.run_helper("""
let enabled=true,callback,cleared=[],cancelled=[],applied=0;
const c=fridayFlowController({enabled:()=>enabled,frame:fn=>{callback=fn;return 7;},
cancel:id=>cancelled.push(id),clear:target=>cleared.push(target),measure:()=>({left:0,top:0,width:100,height:100}),
apply:()=>applied++});
c.move('one',10,10);c.move('two',20,20);enabled=false;callback();
process.stdout.write(JSON.stringify({cleared,cancelled,applied}));
""")
        self.assertEqual(result['cleared'],['one','two'])
        self.assertEqual(result['cancelled'],[7])
        self.assertEqual(result['applied'],0)

    def test_motion_has_no_network_storage_permission_or_action_dispatch(self):
        for marker in ('fetch(', 'jsonRequest(', 'localStorage', 'setInterval(',
            '.click(', 'dispatchEvent(', 'preventDefault(', 'stopPropagation(',
            'innerHTML', 'confirm_sandbox_execution', 'getUserMedia'):
            self.assertNotIn(marker,FLOW_JS)
        for marker in ('cancelAnimationFrame','visibilitychange','attributeFilter',"pulse.setAttribute('aria-hidden','true')",'button.disabled'):
            self.assertIn(marker,FLOW_JS)

    def test_css_respects_reduction_disabled_controls_and_keyboard_focus(self):
        for marker in ('prefers-reduced-motion:reduce','html[data-motion="off"]',
            'button:disabled','focus-visible','pointer-events:none','@media(hover:hover)',
            'form[aria-busy="true"]','--flow-ease'):
            self.assertIn(marker,FLOW_CSS)
        self.assertNotIn('transition:all',FLOW_CSS)
        self.assertIn('button.friday-start-card:not(:disabled):hover',FLOW_CSS)

    def test_composition_keeps_one_style_and_no_duplicate_motion_runtime(self):
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('<style'),1)
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('const flowPreviousShow=show'),1)
        for marker in ('flow-page-in','friday-chat-cashflow','/api/friday/cashflow','Check my money runway'):
            self.assertIn(marker,FINANCIAL_FRIDAY_HTML)

    def test_busy_feedback_is_bound_to_real_requests_and_reading_scroll_is_preserved(self):
        for script,subject in ((CHAT_JS,'command'),(CASHFLOW_JS,'form')):
            self.assertIn(subject+".setAttribute('aria-busy','true')",script)
            self.assertIn(subject+".setAttribute('aria-busy','false')",script)
        self.assertIn('chatLog.scrollHeight-chatLog.scrollTop-chatLog.clientHeight<80',CHAT_JS)
        self.assertIn("dataset.motion==='off'?'auto':'smooth'",CHAT_JS)
        self.assertIn('sentGeneration!==chatGeneration',CHAT_JS)
