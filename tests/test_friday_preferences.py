"""Presentation controls must stay local, optional and separate from payment rules."""
import json
import shutil
import subprocess
import unittest

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_preferences import PREFERENCES_CSS, PREFERENCES_JS


class FridayPreferenceTests(unittest.TestCase):
    def run_runtime(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is optional for presentation execution checks')
        helper = 'function fridayPreferenceRuntime' + PREFERENCES_JS.split(
            'function fridayPreferenceRuntime', 1)[1].split('const preferenceActions', 1)[0]
        setup = """
const values={},storage={getItem:key=>values[key],setItem:(key,value)=>values[key]=value};
let changed=null,mode=null,hidden=false,time=0,starts=0,constructs=0;
const scheme={matches:false,addEventListener:(name,fn)=>changed=fn};
const parameter={setValueAtTime(){},exponentialRampToValueAtTime(){}};
class Audio {constructor(){constructs++;this.currentTime=0;this.state='running';}
createOscillator(){return {frequency:parameter,connect(){},disconnect(){},start(){starts++;},stop(){}};}
createGain(){return {gain:parameter,connect(){},disconnect(){}};}}
const create=(saved=storage,AudioType=Audio)=>fridayPreferenceRuntime(saved,scheme,(resolved,choice)=>mode={resolved,choice},AudioType,()=>hidden,()=>time);
"""
        result = subprocess.run([node], input=helper + setup + body, text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_sound_is_muted_and_no_audio_constructed_on_load(self):
        result = self.run_runtime("const r=create();process.stdout.write(JSON.stringify({sound:r.getSound(),played:r.tone(true),constructs,starts,mode}));")
        self.assertFalse(result['sound'])
        self.assertFalse(result['played'])
        self.assertEqual(result['constructs'], 0)
        self.assertEqual(result['mode']['resolved'], 'light')

    def test_theme_persistence_device_changes_and_invalid_values(self):
        result = self.run_runtime("""
create().setTheme('dark');const restored=create().resolved();const r=create();r.setTheme('system');scheme.matches=true;changed();r.setTheme('invalid');
process.stdout.write(JSON.stringify({restored,mode,values}));
""")
        self.assertEqual(result['restored'], 'dark')
        self.assertEqual(result['mode'], {'resolved': 'dark', 'choice': 'system'})
        self.assertEqual(result['values']['friday-theme'], 'system')

    def test_sound_requires_trusted_action_and_is_throttled_and_mutable(self):
        result = self.run_runtime("""
const r=create();r.setSound(true);const synthetic=r.tone(false),one=r.tone(true),repeat=r.tone(true);time=200;hidden=true;const background=r.tone(true);hidden=false;r.setSound(false);const muted=r.tone(true);
process.stdout.write(JSON.stringify({synthetic,one,repeat,background,muted,starts,values}));
""")
        self.assertTrue(result['one'])
        for name in ('synthetic', 'repeat', 'background', 'muted'):
            self.assertFalse(result[name])
        self.assertEqual(result['starts'], 1)
        self.assertEqual(result['values']['friday-sound'], 'off')

    def test_storage_and_audio_failures_do_not_break_the_interface(self):
        result = self.run_runtime("""
const denied={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};
class Broken {constructor(){throw Error('audio unavailable');}}
const r=create(denied,Broken);r.setTheme('dark');r.setSound(true);const played=r.tone(true);r.setTheme('light');
process.stdout.write(JSON.stringify({mode,played,sound:r.getSound()}));
""")
        self.assertEqual(result['mode']['resolved'], 'light')
        self.assertFalse(result['played'])
        self.assertFalse(result['sound'])

    def test_controls_do_not_create_financial_or_microphone_authority(self):
        for forbidden in ('fetch(', 'jsonRequest(', 'getUserMedia', 'confirm_sandbox_execution',
                          'saveMandate(', 'setInterval(', 'innerHTML'):
            self.assertNotIn(forbidden, PREFERENCES_JS)
        for marker in ('showModal()', "preferencesButton.focus()", 'e.isTrusted',
                       "$('motion-toggle')", 'aria-pressed', 'Colour theme'):
            self.assertIn(marker, PREFERENCES_JS)
        self.assertIn('prefers-reduced-motion:reduce', PREFERENCES_CSS)
        self.assertIn('html[data-motion="off"]', PREFERENCES_CSS)
        self.assertIn('.stage.blocked', PREFERENCES_CSS)
        self.assertIn('input::file-selector-button{background:#34435c;color:#edf1fa', PREFERENCES_CSS)
        self.assertIn('friday-theme-toggle', FINANCIAL_FRIDAY_HTML)
        self.assertEqual(FINANCIAL_FRIDAY_HTML.count('<style'), 1)
