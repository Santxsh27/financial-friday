"""Original animated instrument aperture. Motion is not evidence of task success."""

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
      // Original concentric instrument aperture, not a movie asset or rotating PNG.
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
        const cx=size/2,cy=size/2,turn=t*(state==='working'?.48:.1),tau=Math.PI*2;
        const glow=c.createRadialGradient(cx,cy,size*.055,cx,cy,size*.47);glow.addColorStop(0,'rgba('+rgb+',.2)');glow.addColorStop(.58,'rgba('+rgb+',.045)');glow.addColorStop(1,'rgba('+rgb+',0)');c.fillStyle=glow;c.fillRect(0,0,size,size);
        // Front-facing concentric geometry: no planetary paths, spheres or orbital particles.
        c.save();c.translate(cx+core.x*size*.035,cy+core.y*size*.035);
        function arc(r,a,b,width,alpha){c.strokeStyle='rgba('+rgb+','+alpha+')';c.lineWidth=size*width;c.beginPath();c.arc(0,0,size*r,a,b);c.stroke();}
        function line(r1,r2,a,width,alpha){c.strokeStyle='rgba('+rgb+','+alpha+')';c.lineWidth=size*width;c.beginPath();c.moveTo(Math.cos(a)*size*r1,Math.sin(a)*size*r1);c.lineTo(Math.cos(a)*size*r2,Math.sin(a)*size*r2);c.stroke();}
        arc(.433,0,tau,.002,.18);arc(.39,0,tau,.002,.23);
        for(let i=0;i<96;i++)line(i%8===0?.414:.422,.433,i*tau/96,.002,i%8===0?.8:.3);
        // Offset arc lengths and notches are our own instrument pattern.
        for(let i=0;i<5;i++){const a=i*tau/5+turn;arc(.365,a+.08,a+.79,.012,.83);arc(.348,a+.09,a+.34,.002,.5);}
        for(let i=0;i<42;i++){const a=i*tau/42-turn*.7;arc(.306,a,a+.088,.025,i%7<3?.78:.24);}
        arc(.274,0,tau,.002,.3);
        for(let i=0;i<8;i++){const a=i*tau/8+turn*.45;arc(.246,a+.06,a+.58,.003,.75);line(.253,.264,a+.08,.002,.6);}
        // A scanning arc signals motion only. It is not a progress bar or AI activity claim.
        c.shadowColor='rgba('+rgb+',.8)';c.shadowBlur=size*.025;
        arc(.327,turn*2.3,turn*2.3+.34,.004,.95);c.shadowBlur=0;
        // Hollow aperture and breathing contour, rather than a luminous planetary ball.
        const pulse=animate?Math.sin(t*1.7)*.003:0;
        arc(.185+pulse,0,tau,.005,.95);arc(.17,0,tau,.002,.4);
        for(let i=0;i<12;i++){const a=i*tau/12-turn*.28;arc(.205,a+.03,a+.25,.011,i%3===0?.78:.32);}
        c.strokeStyle='rgba('+rgb+',.55)';c.lineWidth=size*.002;c.beginPath();
        for(let i=0;i<=120;i++){const a=i*tau/120;const wave=Math.sin(a*5-t*1.2)*Math.sin(a*3+t*.5)*(state==='working'?.009:.003);const r=size*(.134+wave);if(i===0)c.moveTo(Math.cos(a)*r,Math.sin(a)*r);else c.lineTo(Math.cos(a)*r,Math.sin(a)*r);}c.closePath();c.stroke();
        // Four discontinuous corner brackets give the aperture a device-like silhouette.
        c.strokeStyle='rgba('+rgb+',.4)';c.lineWidth=size*.003;
        for(let i=0;i<4;i++){c.save();c.rotate(i*Math.PI/2);c.beginPath();c.moveTo(size*.36,-size*.28);c.lineTo(size*.36,-size*.36);c.lineTo(size*.28,-size*.36);c.stroke();c.restore();}
        c.fillStyle='rgba('+rgb+',.8)';c.fillRect(-size*.012,-size*.002,size*.024,size*.004);c.fillRect(-size*.002,-size*.012,size*.004,size*.024);c.restore();
        core.canvas.dataset.frames=String(++core.frames);core.canvas.dataset.state=state;
      }
      function wakeFridayCore(){if(!coreFrame&&coreMotionAllowed()&&[...fridayCores.values()].some(c=>c.visible))coreFrame=requestAnimationFrame(renderFridayCores);}
      function renderFridayCores(time){coreFrame=0;if(!coreMotionAllowed())return;if(time-lastCoreFrame>=32){lastCoreFrame=time;fridayCores.forEach(c=>{if(c.visible&&c.host.isConnected&&!c.host.closest('[hidden]'))drawFridayCore(c,time);});}wakeFridayCore();}
      const coreVisibility=new IntersectionObserver(entries=>{entries.forEach(e=>{const core=fridayCores.get(e.target);if(core){core.visible=e.isIntersecting;if(core.visible)drawFridayCore(core,performance.now());}});wakeFridayCore();});
      const coreResize=new ResizeObserver(entries=>entries.forEach(e=>{const core=fridayCores.get(e.target);if(core?.visible)drawFridayCore(core,performance.now());}));
      function makeFridayCore(){const host=element('div',null,'friday-core');host.setAttribute('aria-hidden','true');const canvas=element('canvas');canvas.dataset.renderer='INSTRUMENT_APERTURE_CANVAS';host.append(canvas);const core={host,canvas,context:canvas.getContext('2d'),visible:false,x:0,y:0,frames:0};fridayCores.set(host,core);coreVisibility.observe(host);
        host.addEventListener('pointermove',e=>{if(!coreMotionAllowed()||e.pointerType==='touch')return;const rect=host.getBoundingClientRect();core.x=(e.clientX-rect.left)/rect.width*.45-.225;core.y=(e.clientY-rect.top)/rect.height*.35-.175;});host.addEventListener('pointerleave',()=>{core.x=0;core.y=0;});
        coreResize.observe(host);return host;}
      function repaintFridayCores(){if(coreFrame){cancelAnimationFrame(coreFrame);coreFrame=0;}fridayCores.forEach(c=>{if(c.visible)drawFridayCore(c,performance.now());});wakeFridayCore();}
      document.addEventListener('visibilitychange',repaintFridayCores);
      new MutationObserver(repaintFridayCores).observe(document.documentElement,{attributes:true,attributeFilter:['data-motion']});
      // Companion state changes repaint even when the user has disabled animation.
      new MutationObserver(records=>{if(records.some(r=>r.target.classList?.contains('journey-companion')))repaintFridayCores();}).observe(root,{subtree:true,attributes:true,attributeFilter:['data-state']});
"""
