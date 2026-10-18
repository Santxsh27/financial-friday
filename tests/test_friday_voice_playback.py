"""Exercise the exact shipped speech controller, without a model or microphone."""
import shutil
import subprocess
import unittest
from carapace_integrations.friday_voice_playback import VOICE_PLAYBACK_JS


HARNESS = r'''
const assert=require('node:assert/strict');
const settle=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function harness(){let enabled=true,time=100000,serial=0;const requests=[],heard=[],states=[],errors=[],timers=new Map();
 const controller=createFridayVoicePlayback({enabled:()=>enabled,now:()=>time,
 later:(fn,ms)=>{const id=++serial;timers.set(id,{fn,ms});return id;},cancel:id=>timers.delete(id),
 request:text=>new Promise((resolve,reject)=>requests.push({text,resolve,reject})),
 audio:async(result,clip)=>heard.push({result,clip}),stop:()=>states.push('stopped'),
 state:state=>states.push(state),error:error=>errors.push(error)});
 return {controller,requests,heard,states,errors,timers,disable:()=>enabled=false,
 advance:()=>{time+=23000;const items=[...timers.values()];timers.clear();items.forEach(t=>t.fn());}};
}
'''


@unittest.skipUnless(shutil.which('node'), 'Node playback tests run in native and CI environments')
class VoicePlaybackTests(unittest.TestCase):
    def run_js(self, body):
        script=VOICE_PLAYBACK_JS+HARNESS+'\n(async()=>{'+body+'})().catch(e=>{console.error(e);process.exitCode=1;});'
        result=subprocess.run(['node'],input=script,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_short_reply_is_unchanged(self):
        self.run_js("assert.deepEqual(fridaySpokenPreview(' Your goal is INR 8,333.34. '),{text:'Your goal is INR 8,333.34.',truncated:false});")

    def test_long_preview_is_bounded_extract_not_new_advice(self):
        self.run_js("const text=('Your exact contribution is INR 8,333.34. Review the costs before saving. ').repeat(40);const p=fridaySpokenPreview(text);assert(p.truncated);assert(p.text.length<=480);assert(p.text.split(/\\s+/).length<=60);assert(text.startsWith(p.text));")

    def test_no_consent_no_request(self):
        self.run_js("const h=harness();h.disable();h.controller.enqueue('A public test');await settle();assert.equal(h.requests.length,0);")

    def test_stop_discards_loading_audio(self):
        self.run_js("const h=harness();h.controller.enqueue('A public test');h.controller.stop();h.requests[0].resolve('audio');await settle();assert.equal(h.heard.length,0);assert(!h.controller.busy);")

    def test_latest_reply_is_queued_not_silently_dropped(self):
        self.run_js("const h=harness();h.controller.enqueue('First');h.controller.enqueue('Second');h.controller.enqueue('Third');assert.equal(h.requests.length,1);h.requests[0].resolve('old');await settle();assert.equal(h.heard.length,0);assert(h.states.includes('waiting'));h.advance();assert.equal(h.requests[1].text,'Third');h.requests[1].resolve('new');await settle();assert.equal(h.heard[0].result,'new');assert(!h.controller.busy);")

    def test_duplicate_inflight_text_is_not_requested_twice(self):
        self.run_js("const h=harness();h.controller.enqueue('Same');h.controller.enqueue('Same');h.requests[0].resolve('one');await settle();assert.equal(h.requests.length,1);assert.equal(h.heard.length,1);")

    def test_replay_reuses_only_current_memory_clip(self):
        self.run_js("const h=harness();h.controller.enqueue('Same');h.requests[0].resolve('one');await settle();h.controller.enqueue('Same');await settle();assert.equal(h.requests.length,1);assert.equal(h.heard.length,2);")

    def test_stop_also_cancels_cached_microtask_replay(self):
        self.run_js("const h=harness();h.controller.enqueue('Same');h.requests[0].resolve('one');await settle();h.controller.enqueue('Same');h.controller.stop();await settle();assert.equal(h.heard.length,1);")

    def test_revocation_discards_response(self):
        self.run_js("const h=harness();h.controller.enqueue('Private test fixture');h.disable();h.controller.stop(true);h.requests[0].resolve('audio');await settle();assert.equal(h.heard.length,0);assert.equal(h.timers.size,0);")

    def test_reset_removes_replay_cache(self):
        self.run_js("const h=harness();h.controller.enqueue('Same');h.requests[0].resolve('one');await settle();h.controller.stop(true);h.advance();h.controller.enqueue('Same');assert.equal(h.requests.length,2);")

    def test_stop_removes_waiting_timer(self):
        self.run_js("const h=harness();h.controller.enqueue('First');h.requests[0].resolve('one');await settle();h.controller.enqueue('Second');assert.equal(h.timers.size,1);h.controller.stop();h.advance();await settle();assert.equal(h.requests.length,1);assert(!h.controller.busy);")

    def test_rate_failure_is_exposed_and_does_not_lock_voice(self):
        self.run_js("const h=harness();h.controller.enqueue('First');h.requests[0].reject({status:429});await settle();assert.equal(h.errors[0].status,429);assert(!h.controller.busy);h.advance();h.controller.enqueue('Retry');assert.equal(h.requests.length,2);")

    def test_new_generation_waits_for_old_fetch_but_never_plays_it(self):
        self.run_js("const h=harness();h.controller.enqueue('Old');h.controller.stop(true);h.controller.enqueue('New');h.requests[0].resolve('old');await settle();h.advance();assert.equal(h.requests[1].text,'New');h.requests[1].resolve('new');await settle();assert.deepEqual(h.heard.map(v=>v.result),['new']);")

    def test_visual_script_uses_explicit_voice_consent(self):
        from carapace_integrations.friday_assistant_ui import ASSISTANT_JS
        self.assertIn('Enable voice & read',ASSISTANT_JS)
        self.assertIn('Your browser blocked autoplay',ASSISTANT_JS)
        self.assertIn('error.status===429',ASSISTANT_JS)
        self.assertNotIn('if(voiceBusy',ASSISTANT_JS)
        self.assertIn('playback.stop(true)',ASSISTANT_JS)
        self.assertNotIn('speechSynthesis',ASSISTANT_JS)
        from carapace_integrations.friday_roadmap_ui import ROADMAP_JS
        self.assertIn("friday:visual-spoken-reply",ROADMAP_JS)
        self.assertIn("node.dataset.voiceSkip==='true'",ASSISTANT_JS)


if __name__=='__main__': unittest.main()
