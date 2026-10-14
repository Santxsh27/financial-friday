"""Bounded presentation-only motion. No network, telemetry or financial actions."""

FLOW_CSS = r"""
:root{--flow-ease:cubic-bezier(.22,.72,.24,1);--flow-fast:160ms;--flow-settle:280ms}
button,a,summary,input,textarea,select{transition:background-color var(--flow-fast) ease,border-color var(--flow-fast) ease,color var(--flow-fast) ease,box-shadow var(--flow-settle) var(--flow-ease),transform var(--flow-settle) var(--flow-ease)}
body,.topbar,.friday-buddy,.friday-starter,.everyday-inbox,.everyday-assistant,.money-section,.review-case,.card{transition:background-color 220ms ease,border-color 220ms ease,color 160ms ease,box-shadow var(--flow-settle) var(--flow-ease)}
button:disabled{transform:none;box-shadow:none}button[aria-disabled="true"]{cursor:not-allowed}
input:not([type=checkbox]):not([type=file]):focus,textarea:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 4px var(--live-bg)}
button:focus-visible,a:focus-visible,summary:focus-visible{outline-offset:5px}
.ff-feedback-host{position:relative}.ff-tap-feedback{position:absolute;inset:0;border-radius:inherit;background:radial-gradient(circle at var(--tap-x,50%) var(--tap-y,50%),currentColor,transparent 72%);pointer-events:none;opacity:0;z-index:1}
.friday-chat-log{scrollbar-width:thin;scrollbar-color:#828aab55 transparent;scroll-padding:12px;overflow-anchor:none}
.friday-chat-log::-webkit-scrollbar{width:5px}.friday-chat-log::-webkit-scrollbar-thumb{border-radius:9px;background:#828aab55}
.friday-nav button[aria-current="page"]{box-shadow:inset 0 0 0 1px var(--line),0 3px 10px #28376008}
form[aria-busy="true"] button[type=submit]{cursor:progress}
form[aria-busy="true"] button[type=submit]::after{content:"";display:inline-block;width:12px;height:12px;margin-left:9px;border:1.5px solid currentColor;border-right-color:transparent;border-radius:50%;vertical-align:middle}
@media(prefers-reduced-motion:no-preference){
  .friday-view{animation:flow-page-in 320ms var(--flow-ease) both}
  .friday-view .screen-heading,.simple-home .friday-buddy,.simple-home .friday-starter,.simple-home .everyday-inbox,.simple-home .everyday-assistant{animation:flow-content-in 380ms var(--flow-ease) both}
  .simple-home .friday-starter{animation-delay:35ms}.simple-home .everyday-inbox{animation-delay:60ms}.simple-home .everyday-assistant{animation-delay:25ms}
  .friday-view details[open]>:not(summary){animation:flow-detail-in 220ms var(--flow-ease) both}
  .friday-chat-message,.runway-result>.runway-status{animation:flow-content-in 280ms var(--flow-ease) both}
  .ff-tap-feedback{animation:flow-tap 360ms var(--flow-ease) both}
  form[aria-busy="true"] button[type=submit]::after{animation:flow-spin 900ms linear infinite}
  .toast{transition:opacity 180ms ease,transform 280ms var(--flow-ease);transform:translateY(8px)}.toast.show{transform:none}
  button:not(:disabled):not([aria-disabled="true"]):active{transform:translateY(0) scale(.985);transition-duration:85ms}
}
@media(hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference){
  button:not(:disabled):not([aria-disabled="true"]):hover{box-shadow:0 5px 14px #2837600d}
  .friday-nav button:not(:disabled):hover{transform:translateY(-1px)}
  .friday-start-card,.simple-home .task-tile,.simple-money-picker button{transition:transform 260ms var(--flow-ease),box-shadow 280ms var(--flow-ease),border-color 180ms ease;background-clip:padding-box}
  button.friday-start-card:not(:disabled):hover,.simple-home .task-tile:hover,.simple-money-picker button:hover{transform:perspective(850px) rotateX(var(--flow-rx,0deg)) rotateY(var(--flow-ry,0deg)) translateY(-3px);box-shadow:0 12px 26px #28376012;border-color:#adb5d1}
  button.friday-start-card:not(:disabled):active,.simple-home .task-tile:active,.simple-money-picker button:active{transform:translateY(-1px) scale(.99)}
  button:hover .everyday-arrow{transform:translateX(3px)}.everyday-arrow{transition:transform 220ms var(--flow-ease)}
  .everyday-icon-tile{transition:transform 260ms var(--flow-ease)}.friday-start-card:hover .everyday-icon-tile{transform:translateY(-2px)}
}
@keyframes flow-page-in{from{opacity:.6;transform:translateY(5px)}to{opacity:1;transform:none}}
@keyframes flow-content-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes flow-detail-in{from{opacity:.45;transform:translateY(3px)}to{opacity:1;transform:none}}
@keyframes flow-tap{0%{opacity:.11}100%{opacity:0}}
@keyframes flow-spin{to{transform:rotate(360deg)}}
html[data-motion="off"] .ff-tap-feedback{display:none}
html[data-motion="off"] *,html[data-motion="off"] *::before,html[data-motion="off"] *::after{animation:none!important;transition:none!important;transform:none!important;scroll-behavior:auto!important}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;transform:none!important;scroll-behavior:auto!important}.ff-tap-feedback{display:none}}
"""

FLOW_HELPERS = r"""
      function fridayFlowAllowed(preference,systemReduced,finePointer,hidden){return preference==='on'&&!systemReduced&&finePointer&&!hidden;}
      function fridayFlowOffset(x,y,width,height){
        if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0)return {rx:0,ry:0,x:50,y:50};
        const px=Math.max(0,Math.min(1,x/width)),py=Math.max(0,Math.min(1,y/height));
        return {rx:(.5-py)*1.4,ry:(px-.5)*1.4,x:px*100,y:py*100};
      }
      function fridayFlowController(options){
        let target=null,point=null,pending=null;
        function reset(){if(pending!==null)options.cancel(pending);pending=null;if(target)options.clear(target);target=null;point=null;}
        function move(next,x,y){
          if(!next||!options.enabled()){reset();return;}
          if(next!==target){reset();target=next;}point={x,y};
          if(pending===null)pending=options.frame(()=>{pending=null;if(!options.enabled()||!target){reset();return;}
            const box=options.measure(target);options.apply(target,fridayFlowOffset(point.x-box.left,point.y-box.top,box.width,box.height));});
        }
        return {move,reset};
      }
"""

FLOW_JS = FLOW_HELPERS + r"""
      // Existing actions remain the only event handlers that navigate or execute.
      const flowEnabled=()=>fridayFlowAllowed(document.documentElement.dataset.motion,reduced.matches,fine.matches,document.hidden);
      const flow=fridayFlowController({enabled:flowEnabled,frame:callback=>requestAnimationFrame(callback),cancel:id=>cancelAnimationFrame(id),
        measure:card=>card.getBoundingClientRect(),apply:(card,point)=>{card.style.setProperty('--flow-rx',point.rx.toFixed(2)+'deg');card.style.setProperty('--flow-ry',point.ry.toFixed(2)+'deg');},
        clear:card=>{card.style.removeProperty('--flow-rx');card.style.removeProperty('--flow-ry');}});
      document.addEventListener('pointermove',event=>{if(event.pointerType!=='mouse'){flow.reset();return;}
        flow.move(event.target.closest?.('.friday-start-card,.simple-home .task-tile,.simple-money-picker button'),event.clientX,event.clientY);},{passive:true});
      document.addEventListener('pointerout',event=>{const card=event.target.closest?.('.friday-start-card,.simple-home .task-tile,.simple-money-picker button');if(!event.relatedTarget||(card&&!card.contains(event.relatedTarget)))flow.reset();},{passive:true});
      document.addEventListener('visibilitychange',()=>{if(document.hidden)flow.reset();});
      function flowReset(){flow.reset();document.querySelectorAll('.ff-tap-feedback').forEach(pulse=>pulse.remove());}
      reduced.addEventListener('change',flowReset);fine.addEventListener('change',flowReset);
      new MutationObserver(flowReset).observe(document.documentElement,{attributes:true,attributeFilter:['data-motion']});
      const flowPreviousShow=show;show=function(name,push=true){flowReset();return flowPreviousShow(name,push);};
      function flowTap(button,x,y){
        if(!button||button.disabled||button.getAttribute('aria-disabled')==='true'||document.documentElement.dataset.motion!=='on'||reduced.matches||document.hidden)return;
        button.querySelector('.ff-tap-feedback')?.remove();
        if(getComputedStyle(button).position==='static')button.classList.add('ff-feedback-host');
        const box=button.getBoundingClientRect();
        const pulse=element('span',null,'ff-tap-feedback');pulse.setAttribute('aria-hidden','true');
        pulse.style.setProperty('--tap-x',Math.max(0,Math.min(100,((x??box.left+box.width/2)-box.left)/Math.max(1,box.width)*100))+'%');
        pulse.style.setProperty('--tap-y',Math.max(0,Math.min(100,((y??box.top+box.height/2)-box.top)/Math.max(1,box.height)*100))+'%');
        button.append(pulse);setTimeout(()=>pulse.remove(),400);
      }
      document.addEventListener('pointerdown',event=>{if(event.button===0)flowTap(event.target.closest?.('button'),event.clientX,event.clientY);},{passive:true});
      document.addEventListener('keydown',event=>{if(!event.repeat&&(event.key==='Enter'||event.key===' '))flowTap(event.target.closest?.('button'));});
"""
