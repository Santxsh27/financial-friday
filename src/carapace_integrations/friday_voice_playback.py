"""Bounded, latest-reply speech state machine shared by UI and Node tests."""
VOICE_PLAYBACK_JS = r'''
    function fridaySpokenPreview(value){
      const original=String(value||'').replace(/\s+/g,' ').trim();
      if(!original)return {text:'',truncated:false};
      const words=original.split(' ');let selected=[];
      for(const word of words){if(selected.length>=60||(selected.join(' ').length+word.length+1)>480)break;selected.push(word);}
      let text=selected.join(' ');const truncated=text.length<original.length;
      if(truncated){const boundaries=[...text.matchAll(/[.!?](?=\s|$)/g)];const last=boundaries.at(-1);if(last&&last.index>100)text=text.slice(0,last.index+1);}
      return {text,truncated};
    }
    function createFridayVoicePlayback(options){
      const now=options.now||Date.now,later=options.later||setTimeout,cancel=options.cancel||clearTimeout;
      let generation=0,pending=null,running=null,timer=null,lastStarted=-Infinity,cache=null;
      function stop(clearCache=false){generation++;pending=null;if(timer!==null)cancel(timer);timer=null;if(clearCache)cache=null;options.stop();}
      function enqueue(value){
        const clip=fridaySpokenPreview(value);if(!clip.text||!options.enabled())return;
        if(running?.clip.text===clip.text&&running.generation===generation)return;
        if(cache?.clip.text===clip.text&&!running&&!pending){const saved=cache,version=generation;Promise.resolve().then(()=>{if(version===generation&&options.enabled())return options.audio(saved.result,clip);}).catch(error=>{if(version===generation)options.error(error);});return;}
        pending={clip,generation};if(running)options.state('queued',clip);drain();
      }
      async function drain(){
        if(running||timer!==null||!pending||!options.enabled())return;
        const wait=Math.max(0,(options.minGapMs??22000)-(now()-lastStarted));
        if(wait){options.state('waiting',pending.clip,Math.ceil(wait/1000));timer=later(()=>{timer=null;drain();},wait);return;}
        const job=pending;pending=null;running=job;lastStarted=now();options.state('loading',job.clip);
        try{const result=await options.request(job.clip.text);
          if(job.generation===generation&&options.enabled()&&!pending){cache={result,clip:job.clip};await options.audio(result,job.clip);}
        }catch(error){if(job.generation===generation&&options.enabled())options.error(error);}
        finally{if(running===job)running=null;if(pending)drain();}
      }
      return {enqueue,stop,get busy(){return !!(running||pending||timer!==null);}};
    }
'''
