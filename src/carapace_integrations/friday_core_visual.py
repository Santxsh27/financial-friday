"""Code-native 3D status visual. Animation is not evidence of AI or payment success."""

CORE_CSS = r"""<style>
.friday-core{width:156px;height:156px;position:relative;flex:none;isolation:isolate}
.friday-core canvas{width:100%;height:100%;display:block;pointer-events:none}
.journey-home-assistant .friday-core{width:240px;height:240px}
.mark .friday-core{width:48px;height:48px}
.journey-companion{gap:12px}.journey-home-assistant{flex-direction:column;text-align:center}
.journey-home-assistant b{font-size:24px}.journey-home-assistant p{max-width:240px}
.journey-run-assistant .friday-core{width:138px;height:138px}
@media(max-width:720px){.journey-home-assistant{flex-direction:row;text-align:left}.journey-home-assistant .friday-core{width:110px;height:110px}.journey-companion .friday-core{width:106px;height:106px}.mark .friday-core{width:44px;height:44px}}
</style>"""

CORE_JS = r"""
      // Procedural projection, not a rotating PNG; one bounded render loop for all cores.
      const fridayCores=new Map();let coreFrame=0,lastCoreFrame=0;
      function coreMotionAllowed(){return document.documentElement.dataset.motion!=='off'&&!document.hidden;}
      function drawFridayCore(core,time){
        const c=core.context;if(!c)return;
        const size=core.host.clientWidth||156;const scale=Math.min(window.devicePixelRatio||1,2);
        const pixels=Math.round(size*scale);if(core.canvas.width!==pixels){core.canvas.width=pixels;core.canvas.height=pixels;}
        c.setTransform(scale,0,0,scale,0,0);c.clearRect(0,0,size,size);c.shadowBlur=0;
        const state=core.host.closest('.journey-companion')?.dataset.state||'idle';
        const rgb=state==='held'?'255,122,135':state==='attention'?'255,207,120':state==='complete'?'108,242,191':state==='working'?'97,211,255':'115,207,241';
        const animate=coreMotionAllowed();const t=animate?time/1000:0;
        const angle=t*(state==='working'?.65:.18);const radius=size*.32;const cx=size/2,cy=size/2;
        const glow=c.createRadialGradient(cx,cy,0,cx,cy,size*.47);glow.addColorStop(0,'rgba('+rgb+',.26)');glow.addColorStop(.6,'rgba('+rgb+',.065)');glow.addColorStop(1,'rgba('+rgb+',0)');c.fillStyle=glow;c.fillRect(0,0,size,size);
        function project(x,y,z,tilt,turn){const y1=y*Math.cos(tilt)-z*Math.sin(tilt),z1=y*Math.sin(tilt)+z*Math.cos(tilt);const x2=x*Math.cos(turn)+z1*Math.sin(turn),z2=-x*Math.sin(turn)+z1*Math.cos(turn);const p=3/(3-z2*.4);return [cx+x2*radius*p,cy+y1*radius*p,z2];}
        // Three differently tilted segmented orbits create actual foreground/background depth.
        const segments=[];[[-.9,.25,1], [.75,1.35,.93], [1.6,-.6,.82]].forEach(([tilt,turn,r],ring)=>{
          for(let i=0;i<100;i++){if(i%25>20)continue;const a=i*Math.PI*2/100+angle*(ring===1?-1:1);const b=a+.046;const p=project(Math.cos(a)*r,Math.sin(a)*r,0,tilt+core.y,turn+core.x);const q=project(Math.cos(b)*r,Math.sin(b)*r,0,tilt+core.y,turn+core.x);segments.push({p,q,ring});}
        });segments.sort((a,b)=>a.p[2]-b.p[2]);c.shadowColor='rgba('+rgb+',.6)';segments.forEach(({p,q,ring})=>{c.shadowBlur=p[2]>0?5:0;c.strokeStyle='rgba('+rgb+','+(.25+(p[2]+1)*.3)+')';c.lineWidth=ring===0?1.8:1.2;c.beginPath();c.moveTo(p[0],p[1]);c.lineTo(q[0],q[1]);c.stroke();});c.shadowBlur=0;
        // Fixed outer instrument ticks: subtle, readable, no fake telemetry numbers.
        c.lineWidth=.7;for(let i=0;i<48;i++){const a=i*Math.PI/24;const r=size*.43;c.strokeStyle='rgba('+rgb+','+(i%4===0?.55:.17)+')';c.beginPath();c.moveTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);c.lineTo(cx+Math.cos(a)*(r+(i%4===0?4:2)),cy+Math.sin(a)*(r+(i%4===0?4:2)));c.stroke();}
        const pulse=animate?1+Math.sin(t*2)*.035:1;
        const inner=c.createRadialGradient(cx-size*.04,cy-size*.04,0,cx,cy,size*.15);inner.addColorStop(0,'rgba(230,252,255,.95)');inner.addColorStop(.2,'rgba('+rgb+',.8)');inner.addColorStop(.6,'rgba('+rgb+',.2)');inner.addColorStop(1,'rgba('+rgb+',0)');c.fillStyle=inner;c.beginPath();c.arc(cx,cy,size*.15*pulse,0,Math.PI*2);c.fill();
        c.strokeStyle='rgba('+rgb+',.85)';c.lineWidth=1.2;c.beginPath();c.arc(cx,cy,size*.095,0,Math.PI*2);c.stroke();
        c.strokeStyle='rgba('+rgb+',.65)';c.lineWidth=1;c.beginPath();for(let i=0;i<=80;i++){const a=i*Math.PI/40;const wave=Math.sin(a*6-t*2)*Math.cos(a*3+t)*size*(state==='working'?.015:.006);const r=size*.18+wave;const x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;if(i===0)c.moveTo(x,y);else c.lineTo(x,y);}c.stroke();
        // Moving orbital particles respond to real pending/held/completed UI state.
        for(let i=0;i<7;i++){const a=angle*2+i*Math.PI*2/7;const p=project(Math.cos(a),Math.sin(a),0,.75+core.y,1.35+core.x);c.fillStyle='rgba('+rgb+','+(.35+(p[2]+1)*.3)+')';c.beginPath();c.arc(p[0],p[1],p[2]>0?2.1:1.1,0,Math.PI*2);c.fill();}
        core.canvas.dataset.frames=String(++core.frames);core.canvas.dataset.state=state;
      }
      function wakeFridayCore(){if(!coreFrame&&coreMotionAllowed()&&[...fridayCores.values()].some(c=>c.visible))coreFrame=requestAnimationFrame(renderFridayCores);}
      function renderFridayCores(time){coreFrame=0;if(!coreMotionAllowed())return;if(time-lastCoreFrame>=32){lastCoreFrame=time;fridayCores.forEach(c=>{if(c.visible&&c.host.isConnected&&!c.host.closest('[hidden]'))drawFridayCore(c,time);});}wakeFridayCore();}
      const coreVisibility=new IntersectionObserver(entries=>{entries.forEach(e=>{const core=fridayCores.get(e.target);if(core){core.visible=e.isIntersecting;if(core.visible)drawFridayCore(core,performance.now());}});wakeFridayCore();});
      const coreResize=new ResizeObserver(entries=>entries.forEach(e=>{const core=fridayCores.get(e.target);if(core?.visible)drawFridayCore(core,performance.now());}));
      function makeFridayCore(){const host=element('div',null,'friday-core');host.setAttribute('aria-hidden','true');const canvas=element('canvas');canvas.dataset.renderer='PROJECTED_3D_CANVAS';host.append(canvas);const core={host,canvas,context:canvas.getContext('2d'),visible:false,x:0,y:0,frames:0};fridayCores.set(host,core);coreVisibility.observe(host);
        host.addEventListener('pointermove',e=>{if(!coreMotionAllowed()||e.pointerType==='touch')return;const rect=host.getBoundingClientRect();core.x=(e.clientX-rect.left)/rect.width*.45-.225;core.y=(e.clientY-rect.top)/rect.height*.35-.175;});host.addEventListener('pointerleave',()=>{core.x=0;core.y=0;});
        coreResize.observe(host);return host;}
      function repaintFridayCores(){if(coreFrame){cancelAnimationFrame(coreFrame);coreFrame=0;}fridayCores.forEach(c=>{if(c.visible)drawFridayCore(c,performance.now());});wakeFridayCore();}
      document.addEventListener('visibilitychange',repaintFridayCores);
      new MutationObserver(repaintFridayCores).observe(document.documentElement,{attributes:true,attributeFilter:['data-motion']});
      // Companion state changes repaint even when the user has disabled animation.
      new MutationObserver(records=>{if(records.some(r=>r.target.classList?.contains('journey-companion')))repaintFridayCores();}).observe(root,{subtree:true,attributes:true,attributeFilter:['data-state']});
"""
