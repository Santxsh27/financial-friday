"""Device-local presentation preferences. No financial or network authority."""

PREFERENCES_CSS = r"""
.friday-preference-actions{display:flex;gap:7px;flex:none;margin-left:auto}
.friday-preference-actions button{width:44px;height:44px;padding:0;display:grid;place-items:center;border-radius:50%;font-size:21px;background:var(--panel2);border-color:transparent}
.friday-preference-actions button:hover{box-shadow:0 4px 16px #172b4a20;border-color:var(--line)}
.friday-preferences{width:min(460px,calc(100% - 32px));max-height:85vh;overflow:auto;border:1px solid var(--line);border-radius:24px;padding:26px;background:var(--panel);color:var(--ink);box-shadow:0 24px 90px #0005}
.friday-preferences::backdrop{background:#10203870;backdrop-filter:blur(5px)}
.friday-preferences header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}
.friday-preferences h2{font-size:23px;letter-spacing:-.035em;margin:0}.friday-preferences p{font-size:13px;color:var(--muted)}
.friday-preference-row{padding:18px 0;border-top:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:16px}
.friday-preference-row>div{min-width:0}.friday-preference-row b{font-size:14px;display:block}.friday-preference-row small{display:block;color:var(--muted);font-size:12px;line-height:1.6;margin-top:5px}
.friday-preference-row select{min-width:120px;max-width:145px}.friday-preference-row button{white-space:nowrap;margin:0!important;font-size:12px!important;border-color:var(--line)!important;color:var(--ink)!important;background:var(--panel2)}
.friday-preferences .preference-note{margin-bottom:0;font-size:11px}
.friday-preference-actions button:focus-visible{outline:3px solid var(--blue);outline-offset:3px}
@media(hover:hover) and (pointer:fine){button:not(:disabled):hover,summary:hover{box-shadow:0 4px 14px #16243d12}.simple-home .task-tile:hover,.activity-entry:hover,.journey-bill-select:hover{transform:translateY(-3px);box-shadow:0 8px 24px #16243d14;border-color:#b3bfe2}button .everyday-arrow{transition:transform .2s ease}button:hover .everyday-arrow{transform:translateX(3px)}}
html[data-theme="dark"]{color-scheme:dark;--bg:#111827;--panel:#1b2536;--panel2:#253247;--ink:#edf1fa;--muted:#b2bfd3;--line:#3a4960;--blue:#afbdff;--lime:#afbdff;--cyan:#94dcbc;--red:#ffadbf;--amber:#f3cc88;--friday-pass:#94dcbc;--friday-held:#ffadbf;--friday-review:#f3cc88;--friday-live:#afbdff}
html[data-theme="dark"] :is(.topbar,.everyday-inbox,.everyday-bill-row,.everyday-scope,.card,.money-section,.simple-fold,.friday-work,.outcome-summary,.assurance-board,.run-source,.permission-card,.demo-controls,.scenario,.metric,.money-stat,.journey-budget,.journey-plan-body,.journey-bill-select,.mission-details,.activity-entry,.simple-home .task-tile,.friday-help,.simple-more>div,.promise>div){background:var(--panel);color:var(--ink);border-color:var(--line)}
html[data-theme="dark"] :is(button,input,textarea,select,input::file-selector-button,pre,.provider-setup,.customer-examples,.journey-bill-detail,.badge,.brief-main){background:var(--panel2);color:var(--ink);border-color:var(--line)}
html[data-theme="dark"] :is(.everyday-date,input::placeholder,textarea::placeholder,.simple-more>summary){color:var(--muted)}
html[data-theme="dark"] .simple-more>summary{background:var(--panel2)}
html[data-theme="dark"] .friday-nav button{background:transparent;color:var(--ink)}
html[data-theme="dark"] .friday-nav button[aria-current="page"]{background:#49372e;color:#ffd0b7}
html[data-theme="dark"] :is(button:not(:disabled):hover,.friday-nav button:hover,.simple-more button:hover,.simple-home .task-tile:hover){background:#30405a}
html[data-theme="dark"] :is(.run,.journey-handle,.everyday-assistant .run,.everyday-bill-row>button){background:#e6ab85;color:#241a16;border-color:#e6ab85}
html[data-theme="dark"] :is(.run:hover,.journey-handle:hover,.everyday-assistant .run:hover,.everyday-bill-row>button:hover){background:#f3c1a1}
html[data-theme="dark"] .everyday-assistant{background:#202c44;border:1px solid #435574}
html[data-theme="dark"] .everyday-document-action{background:transparent;color:#f3f6ff}
html[data-theme="dark"] :is(.stage,.help-scope,.receipt code){background:var(--panel2);border-color:var(--line)}
html[data-theme="dark"] :is(.activity-tools button[aria-pressed="true"],.scenario[aria-pressed="true"],.stage.active){background:#2c3b58;color:#dce4ff;border-color:#9aabec}
html[data-theme="dark"] :is(.everyday-warning,.journey-attention){background:#3a3021;color:#ffdda4;border-color:#6e5635}
html[data-theme="dark"] .everyday-warning p{color:#e6c793}html[data-theme="dark"] .everyday-warning button{background:#4b3d28;color:#ffe0ae;border-color:#7d623e}
html[data-theme="dark"] :is(.everyday-status,.run-signal,.badge){background:#2b3b5b;color:#c7d1ff;border-color:#6574a2}
html[data-theme="dark"] :is(.everyday-status.review,.status.review){background:#413523;color:#ffdb9b}
html[data-theme="dark"] .journey-bill-select[aria-pressed="true"]{background:#2c3b58;border-color:#9aabec}
html[data-theme="dark"] .everyday-icon-tile{background:#dce2fb}html[data-theme="dark"] .everyday-icon-tile.sage{background:#d7eddc}html[data-theme="dark"] .everyday-icon-tile.peach{background:#f5dcc8}html[data-theme="dark"] .everyday-icon-tile.rose{background:#f4d9e2}html[data-theme="dark"] .everyday-icon-tile.sky{background:#dbe7ff}
html[data-theme="dark"] :is(.everyday-arrow,.everyday-document-action>img){filter:brightness(0) invert(1)}
html[data-theme="dark"] [data-state="complete"] :is(.outcome-summary,.run-signal),html[data-theme="dark"] :is(.stage.done,.activity-entry .status.good){background:#193c30;color:#b9f4d6;border-color:#5e9c7c}
html[data-theme="dark"] [data-state="held"] :is(.outcome-summary,.run-signal),html[data-theme="dark"] :is(.stage.blocked,.activity-entry .status.held){background:#422a36;color:#ffc5d1;border-color:#ac7587}
html[data-theme="dark"] [data-state="attention"] :is(.outcome-summary,.run-signal){background:#3a3021;color:#ffdda4;border-color:#9c7a47}
@media(min-width:1250px){.friday-nav{margin-left:22px;margin-right:0}}
@media(max-width:1150px){.topbar{height:auto}.topbar>.shell{flex-wrap:wrap;padding:12px 0;gap:9px}.friday-nav{order:3;flex-basis:100%;justify-content:flex-start;overflow:auto;margin:2px 0 0}.simple-more{margin-left:0}}
@media(max-width:720px){.friday-preference-actions{gap:4px}.friday-preference-actions button{width:40px;height:44px;font-size:19px}.topbar>.shell{gap:7px}.simple-more>summary{width:36px}.brand{font-size:17px}.brand small{font-size:10px}}
@media(prefers-reduced-motion:reduce){button:hover .everyday-arrow{transform:none!important}}html[data-motion="off"] button:hover .everyday-arrow{transform:none!important}
"""

PREFERENCES_JS = r"""
      // Cosmetic settings are device-local and never sent to the financial API.
      function fridayPreferenceRuntime(storage,scheme,onTheme,AudioType,isHidden,clock){
        function read(key,fallback){try{return storage.getItem(key)||fallback;}catch{return fallback;}}
        function save(key,value){try{storage.setItem(key,value);}catch{}}
        let theme=read('friday-theme','light');if(!['light','dark','system'].includes(theme))theme='light';
        let sound=read('friday-sound','off')==='on',audio=null,lastTone=-Infinity;
        function resolved(){return theme==='system'?(scheme.matches?'dark':'light'):theme;}
        function apply(){onTheme(resolved(),theme);}
        function setTheme(value){if(!['light','dark','system'].includes(value))return;theme=value;save('friday-theme',value);apply();}
        function setSound(value){sound=value===true;save('friday-sound',sound?'on':'off');}
        function tone(trusted){
          if(!trusted||!sound||isHidden()||!AudioType||clock()-lastTone<120)return false;
          try{audio=audio||new AudioType();if(audio.state==='suspended')audio.resume().catch(()=>{});
            const osc=audio.createOscillator(),gain=audio.createGain(),now=audio.currentTime;
            osc.type='sine';osc.frequency.setValueAtTime(640,now);osc.frequency.exponentialRampToValueAtTime(420,now+.07);
            gain.gain.setValueAtTime(.0001,now);gain.gain.exponentialRampToValueAtTime(.035,now+.008);gain.gain.exponentialRampToValueAtTime(.0001,now+.08);
            osc.connect(gain);gain.connect(audio.destination);osc.start(now);osc.stop(now+.09);
            osc.onended=()=>{osc.disconnect();gain.disconnect();};lastTone=clock();return true;
          }catch{setSound(false);return false;}
        }
        scheme.addEventListener?.('change',apply);apply();
        return {setTheme,setSound,tone,apply,getTheme:()=>theme,getSound:()=>sound,resolved};
      }
      const preferenceActions=element('div',null,'friday-preference-actions');
      const themeButton=element('button');themeButton.type='button';themeButton.id='friday-theme-toggle';
      const preferencesButton=element('button','⚙');preferencesButton.type='button';preferencesButton.setAttribute('aria-label','Open appearance and sound settings');preferencesButton.title='Appearance & sound';
      preferenceActions.append(themeButton,preferencesButton);top.insertBefore(preferenceActions,more);
      const preferences=element('dialog',null,'friday-preferences');preferences.setAttribute('aria-labelledby','friday-preferences-title');
      const preferencesHead=element('header');const preferencesTitle=element('h2','Make Friday yours.');preferencesTitle.id='friday-preferences-title';const closePreferences=element('button','Close');closePreferences.type='button';preferencesHead.append(preferencesTitle,closePreferences);
      preferences.append(preferencesHead,element('p','Your display preferences. Your financial rules stay unchanged.'));
      function preferenceRow(title,copy,control){const row=element('div',null,'friday-preference-row');const label=element('div');label.append(element('b',title),element('small',copy));row.append(label,control);preferences.append(row);}
      const themeSelect=element('select');themeSelect.setAttribute('aria-label','Colour theme');[['light','Daylight'],['dark','Midnight'],['system','Use device']].forEach(([value,label])=>{const option=element('option',label);option.value=value;themeSelect.append(option);});
      preferenceRow('Colour theme','Warm daylight or a calm midnight workspace.',themeSelect);
      const soundButton=element('button');soundButton.type='button';soundButton.id='friday-sound-toggle';soundButton.setAttribute('aria-label','Interface sounds');
      preferenceRow('Interface sounds','Soft clicks, not payment confirmations. No microphone access.',soundButton);
      preferenceRow('Gentle motion','Turn animations off. Device reduced-motion settings always take priority.',$('motion-toggle'));
      const preferenceNote=element('p','Saved only in this browser. Sound starts muted and never plays on page load.','preference-note');preferences.append(preferenceNote);document.body.append(preferences);
      const preferenceRuntime=fridayPreferenceRuntime({getItem:key=>localStorage.getItem(key),setItem:(key,value)=>localStorage.setItem(key,value)},window.matchMedia('(prefers-color-scheme: dark)'),(theme,choice)=>{document.documentElement.dataset.theme=theme;themeSelect.value=choice;themeButton.textContent=theme==='dark'?'☀':'☾';themeButton.setAttribute('aria-label',theme==='dark'?'Switch to light mode':'Switch to dark mode');themeButton.setAttribute('aria-pressed',String(theme==='dark'));themeButton.title=theme==='dark'?'Light mode':'Dark mode';},window.AudioContext||window.webkitAudioContext,()=>document.hidden,()=>performance.now());
      const soundAvailable=Boolean(window.AudioContext||window.webkitAudioContext);if(!soundAvailable){preferenceRuntime.setSound(false);soundButton.disabled=true;}
      function soundLabel(){soundButton.textContent=!soundAvailable?'Unavailable':preferenceRuntime.getSound()?'On · tap to mute':'Off · tap to enable';soundButton.setAttribute('aria-pressed',String(preferenceRuntime.getSound()));}
      soundLabel();themeButton.addEventListener('click',()=>preferenceRuntime.setTheme(preferenceRuntime.resolved()==='dark'?'light':'dark'));
      themeSelect.addEventListener('change',()=>preferenceRuntime.setTheme(themeSelect.value));
      soundButton.addEventListener('click',e=>{preferenceRuntime.setSound(!preferenceRuntime.getSound());preferenceRuntime.tone(e.isTrusted);soundLabel();});
      preferencesButton.addEventListener('click',()=>{more.open=false;preferences.showModal();closePreferences.focus();});closePreferences.addEventListener('click',()=>preferences.close());
      preferences.addEventListener('close',()=>preferencesButton.focus());
      // Click-only feedback: no constant hover noises or receipt/replay success chimes.
      document.addEventListener('click',e=>{const button=e.target.closest('button');if(button&&!button.disabled&&button!==soundButton){preferenceRuntime.tone(e.isTrusted);soundLabel();}});
"""
