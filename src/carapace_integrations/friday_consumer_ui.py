"""Statement-first consumer composition; server admission is the safety boundary."""

CONSUMER_JS = r'''
    if(consumerOnly){
      const supported=new Set(['home','statements','statement-review','dashboard','coach','profile','plan','rehearsal','privacy','settings','tools','review','document']);
      const safeShow=show;
      show=function(name,push=true){if(!supported.has(name)){safeShow('home',push);toast('This site is for statement guidance. Payment demonstrations are not enabled.');return;}safeShow(name,push);};
      for(const [name,panel] of Object.entries(views)){if(!supported.has(name)){panel.hidden=true;panel.dataset.consumerExcluded='true';}}
      root.querySelectorAll('[data-screen-link]').forEach(b=>{if(!supported.has(b.dataset.screenLink))b.remove();});
      // Keep dormant legacy nodes available to shared presentation handlers.
      // They are hidden/inert, never an admission boundary or pretend data.
      const tools=views.tools;const diary=document.getElementById('friday-money-diary');const runway=document.getElementById('friday-runway');
      if(tools){
        const dormant=element('div');dormant.hidden=true;dormant.inert=true;
        while(tools.firstChild)dormant.append(tools.firstChild);
        tools.append(element('h1','Optional money tools'),element('p','These user-entered plans are separate from your imported statements.','statement-subtle'));
        if(diary)tools.append(diary);if(runway)tools.append(runway);tools.append(dormant);
      }
      const sandbox=document.getElementById('review-sandbox-mode');if(sandbox){sandbox.checked=false;sandbox.disabled=true;const label=sandbox.closest('label');if(label)label.hidden=true;}
      document.querySelectorAll('.friday-prepare-button').forEach(b=>{b.hidden=true;b.disabled=true;});
    }
'''
