"""Compact conversational panel and guided, non-executing task entry."""
CHAT_CSS = """
.friday-chat-log{display:grid;gap:10px;max-height:310px;overflow-y:auto;margin:16px 0;overscroll-behavior:contain}
.friday-chat-message{border-radius:15px;padding:12px 14px;background:#273854;font-size:13px;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere}
.friday-chat-message[data-speaker=user]{background:#fce0d5;color:#432b24;margin-left:22px}
.friday-chat-message b{display:block;font-size:11px;margin-bottom:5px;letter-spacing:.03em}
.friday-chat-consent{display:flex;gap:9px;font-size:11px;color:#d7e0ef;line-height:1.6;margin:14px 0;cursor:pointer}
.friday-chat-consent input{width:18px;height:18px;flex:none;accent-color:#f08869}
.friday-chat-tools{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}.friday-chat-tools button{font-size:11px;min-height:36px;border:1px solid #74839c;color:#f3f6ff;background:transparent;border-radius:12px;padding:7px 10px}
.friday-chat-tools button:hover{background:#314364}.friday-chat-message button{display:block;margin-top:10px;font-size:11px;min-height:36px;background:#e5edfa;color:#1a3158;border-radius:10px}
.friday-chat-status{color:#cfdbef;font-size:11px;line-height:1.6;min-height:24px}
.everyday-assistant{padding:22px}.everyday-assistant-label{padding-right:88px;min-height:62px}.everyday-assistant{position:relative}.everyday-assistant .everyday-orb{position:absolute;right:16px;top:10px;width:86px;height:86px;margin:0}.everyday-assistant h2{font-size:23px;margin:10px 0 8px}.everyday-assistant>p{font-size:13px;margin-bottom:10px}.everyday-assistant textarea{min-height:72px;height:72px;max-height:130px;resize:vertical}.everyday-assistant .home-command{gap:8px}.everyday-assistant .run{min-height:42px}.friday-chat-log{min-height:96px;max-height:210px;margin:10px 0}.friday-chat-message{line-height:1.55}.friday-chat-consent{margin:10px 0}.friday-chat-tools{margin:8px 0}.friday-chat-privacy{font-size:11px;line-height:1.6;color:#d4dcef;margin-top:10px}.friday-chat-privacy summary{cursor:pointer;min-height:30px}.friday-chat-privacy .permission-note{margin:5px 0}.everyday-assistant-state{margin-top:12px;padding-top:10px}.friday-starter{margin:0 0 24px;padding:22px;border:1px solid var(--line);border-radius:22px;background:var(--paper,#fff)}.friday-starter h2{font-size:21px;margin:0 0 6px;letter-spacing:-.035em}.friday-starter>p{font-size:13px;color:var(--muted);line-height:1.65;margin:0 0 16px}.friday-start-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.friday-start-card{display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:10px;padding:16px;border-radius:16px;border:1px solid var(--line);background:transparent;color:var(--ink)}.friday-start-card b{font-size:13px;line-height:1.4}.friday-start-card small{font-size:12px;color:var(--muted);line-height:1.6}.friday-start-card:hover{transform:translateY(-2px);border-color:#a8b9d8}.friday-start-card .everyday-icon-tile{width:38px;height:38px;border-radius:12px}.friday-starter details{margin-top:16px;font-size:13px}.friday-starter summary{cursor:pointer;min-height:36px;display:flex;align-items:center;color:var(--blue)}.friday-starter details p{font-size:12px;color:var(--muted);line-height:1.7}.friday-example-actions{display:flex;gap:8px;flex-wrap:wrap}.friday-example-actions button{font-size:12px;min-height:40px}.friday-starter ol{padding-left:20px;font-size:12px;color:var(--muted);line-height:1.9}.everyday-side{position:static}
.friday-starter{background:var(--panel);color:var(--ink)}
.friday-command-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.everyday-assistant .friday-command-actions .run{min-height:46px;font-size:13px}.friday-prepare-button{background:#cbd9ff!important;color:#193765!important;border:1px solid #a9bdef!important;min-height:46px;font-size:13px}.friday-prepare-button:hover{background:#e1e9ff!important}.everyday-assistant .home-command label{color:#d7e0ef}.everyday-assistant textarea{color:#12223d}.friday-chat-log:has(>.friday-chat-status:only-child){min-height:0;max-height:none;margin:6px 0}.friday-chat-tools{justify-content:space-between}.friday-chat-tools button{min-height:40px}.friday-chat-consent{font-size:12px;margin:12px 0}.friday-chat-status{font-size:12px}.friday-chat-privacy{margin-top:8px}.everyday-assistant-state{font-size:11px}.everyday-assistant>p{line-height:1.6}.friday-chat-message button{min-height:40px}.friday-chat-tools button:hover{color:#fff}
@media(max-width:950px){.friday-start-grid{grid-template-columns:1fr}.friday-start-card{display:grid;grid-template-columns:38px 1fr;column-gap:12px}.friday-start-card .everyday-icon-tile{grid-row:span 2}.friday-start-card small{grid-column:2}.friday-start-card{row-gap:4px}}
@media(prefers-reduced-motion:reduce){.friday-start-card:hover{transform:none}}
"""

CHAT_JS = r"""
    {
      hero.querySelector('.everyday-illustration')?.remove();
      everydayRecent.remove(); // Activity has its own live, read-only page.
      inboxHead.append(inboxLink); // Avoid a large, duplicate navigation tile.
      reviewHeading.remove(); // The page already has an accessible h1.
      titles.bill='Check financial details';
      function updateReviewHeading(){shortHeading(bill,sandboxMode.checked?'Review an artificial payment task':'Check financial details',sandboxMode.checked?'This separate sandbox mode can execute under your saved rules. No real bank is connected.':'Paste a bill or receipt. Gemini reads it and exact checks compare the claims. This review never pays.');}
      sandboxMode.addEventListener('change',updateReviewHeading);updateReviewHeading();
      // Navigation suggestions never execute a financial action.
      // Retired customer bank route resolves to the existing artificial-money overview.
      const priorChatShow=show;show=function(name,push=true){priorChatShow(name==='bank'?'money':name,push);};
      const chatLog=element('div',null,'friday-chat-log');chatLog.id='friday-chat-log';chatLog.setAttribute('role','log');chatLog.setAttribute('aria-label','Conversation with Friday');chatLog.setAttribute('aria-live','polite');
      const chatConsent=element('input');chatConsent.type='checkbox';chatConsent.id='friday-chat-workspace';
      const chatConsentLabel=element('label',' Include my recent financial inbox and sandbox summary in Gemini’s answer','friday-chat-consent');chatConsentLabel.prepend(chatConsent);
      const chatStatus=element('p','Your request stays read-only.','friday-chat-status');chatStatus.setAttribute('role','status');
      let chatBusy=false;let chatHistory=[];let chatGeneration=0;
      function chatMessage(speaker,text){const follow=speaker==='user'||chatLog.scrollHeight-chatLog.scrollTop-chatLog.clientHeight<80;const card=element('article',null,'friday-chat-message');card.dataset.speaker=speaker;card.append(element('b',speaker==='user'?'You':'Friday'),element('div',text));chatLog.append(card);if(follow)chatLog.scrollTo({top:chatLog.scrollHeight,behavior:document.documentElement.dataset.motion==='off'?'auto':'smooth'});return card;}
      function clearChat(){chatGeneration+=1;chatHistory=[];chatLog.replaceChildren();chatStatus.textContent='Conversation cleared from this page. No payment or bank action was performed.';}
      chatConsent.addEventListener('change',clearChat);
      const cashflowConsent=element('input');cashflowConsent.type='checkbox';cashflowConsent.id='friday-chat-cashflow';
      const cashflowConsentLabel=element('label',' Include my saved cash-flow assumptions and calculator summary in Gemini’s answer','friday-chat-consent');cashflowConsentLabel.prepend(cashflowConsent);cashflowConsent.addEventListener('change',clearChat);
      document.addEventListener('friday:preferences-changed',clearChat);
      document.addEventListener('friday:cashflow-updated',clearChat);
      document.addEventListener('friday:diary-updated',clearChat);
      document.addEventListener('friday:cashflow-cleared',()=>{cashflowConsent.checked=false;clearChat();});
      const chatTools=element('div',null,'friday-chat-tools');const chatClear=element('button','Clear chat');chatClear.type='button';chatClear.addEventListener('click',clearChat);
      const reviewFromChat=element('button','Review a bill or receipt');reviewFromChat.type='button';reviewFromChat.dataset.screenLink='bill';
      chatTools.append(reviewFromChat,chatClear);
      everydayAssistant.querySelector('h2').textContent='Ask Friday.';
      everydayAssistant.querySelector('h2').nextElementSibling.textContent='A question, a risk check or a message you need help writing.';
      everydayAssistant.insertBefore(chatLog,command);everydayAssistant.insertBefore(chatConsentLabel,command);command.after(chatStatus,chatTools);
      everydayAssistant.insertBefore(cashflowConsentLabel,command);
      $('home-command').placeholder='Ask about a charge, a bill or a money concept…';$('home-command').maxLength=1600;$('home-command').rows=2;
      command.querySelector('label').textContent='Your question';
      $('home-command').setAttribute('aria-label','Message Friday');command.querySelector('button[type=submit]').textContent='Ask Friday';
      permissionNote.textContent='Chat text goes to Gemini on Google Cloud. Messages are not saved by Friday; replies may be wrong. Never enter a PIN, OTP or password.';
      const chatPrivacy=element('details',null,'friday-chat-privacy');chatPrivacy.append(element('summary','Privacy & limits'),permissionNote);everydayAssistant.append(chatPrivacy);
      separator.remove();docAction.remove();
      const chatWelcome=element('p','Try: “Check this refund request before I pay.”','friday-chat-status');chatLog.append(chatWelcome);
      function prepareChat(message){show('home');$('home-command').value=message;$('home-command').focus();chatStatus.textContent='Question ready. Choose Ask Friday to send it to Gemini.';}
      const starter=element('section',null,'friday-starter');starter.setAttribute('aria-label','Start with Friday');starter.append(element('h2','What can I help you with?'),element('p','Start with a question, your own document or a guided example. You don’t need to connect a bank.'));
      const startGrid=element('div',null,'friday-start-grid');
      [['book-open','rose','Understand a charge','Get a practical checklist and a message you can send.',()=>prepareChat('I see an unfamiliar charge. What should I check, and can you draft a short message to ask about it?')],['file-text','peach','Check a bill','Read a photo or PDF. Compare totals and recipient claims.',()=>show('document')],['shield','sage','Try a guided example','See how Friday spots conflicting bill and receipt details.',()=>{examples.open=true;examples.scrollIntoView({block:'nearest'});}]].forEach(([icon,tint,title,copy,action])=>{const button=element('button',null,'friday-start-card');button.type='button';button.append(everydayTile(icon,tint),element('b',title),element('small',copy));button.addEventListener('click',action);startGrid.append(button);});starter.append(startGrid);
      const examples=element('details');examples.append(element('summary','Guided example · artificial documents, real Gemini review'),element('p','Load the bill first, then choose Review this financial input. Return here and load the matching or changed-recipient receipt. Each check runs Gemini and stores the extracted claims in your private inbox. No money moves. You can edit every input before checking.'));
      const exampleButtons=element('div',null,'friday-example-actions');
      const exampleBill='ARTIFICIAL EXAMPLE — not a real bill. Unpaid invoice FRIDAY-DEMO-101. Supplier: Example Electricity. Total: INR 1780.00. Payee: example-electricity@upi. Line item: Electricity, quantity 1, unit price INR 1780.00, line total INR 1780.00.';
      const exampleReceipt='ARTIFICIAL EXAMPLE — not a real payment. Customer account debit: INR 1780.00 paid out by the customer to Example Electricity for invoice FRIDAY-DEMO-101. Document type: payment receipt. Supplier: Example Electricity. Amount paid: INR 1780.00. Payee: example-electricity@upi. Transaction reference: DEMO-RECEIPT-101. This is an outgoing bill payment, not an incoming refund or credit.';
      [['1. Load bill',exampleBill],['2. Load matching receipt',exampleReceipt],['3. Load changed recipient',exampleReceipt.replace('example-electricity@upi','different-recipient@upi')]].forEach(([label,text])=>{const button=element('button',label,'planner');button.type='button';button.addEventListener('click',()=>{sandboxMode.checked=false;updateReviewHeading();$('check-live').textContent='Review this financial input';$('live-input').value=text;show('bill');$('live-input').focus();toast('Artificial example loaded. Review it before sending to Gemini.');});exampleButtons.append(button);});examples.append(exampleButtons,element('p','Expected: a bill awaiting confirmation; matching document claims for step 2; a recipient conflict for step 3. These are expected checks, not precomputed results or proof of fraud.'));starter.append(examples);
      const startHelp=element('details');const steps=element('ol');['Choose an input. Nothing is sent or paid just by opening a page.','Review with Gemini. Friday extracts claims; exact checks compare amounts and recipients.','Open Financial inbox for evidence and a prepared verification message.','For artificial payment execution only, use Bills and your saved rules. Real bank payments are not supported.'].forEach(text=>steps.append(element('li',text)));startHelp.append(element('summary','How Friday works · four steps'),steps);starter.append(startHelp);everydayMain.insertBefore(starter,everydayInbox);
      everydayIntroCopy.textContent='Less financial admin. Clearer next steps. Ask Friday, check a bill or explore a safe demonstration.';
      scopeCopy.querySelector('p').textContent='Questions and document checks work without bank access. Only the separate payment demo uses artificial funds.';
      async function sendFridayChat(){const field=$('home-command');const message=field.value.trim();if(!message)return;if(chatBusy){toast('Friday is still replying.');return;}
        chatBusy=true;const button=command.querySelector('button[type=submit]');button.disabled=true;chatClear.disabled=true;chatConsent.disabled=true;chatMessage('user',message);field.value='';chatStatus.textContent='Friday is thinking with Gemini… No financial action is being performed.';
        cashflowConsent.disabled=true;if($('friday-chat-diary'))$('friday-chat-diary').disabled=true;command.setAttribute('aria-busy','true');
        const sentGeneration=chatGeneration;
        try{const result=await jsonRequest('/api/friday/chat','POST',{message,history:chatHistory.slice(-8),include_workspace:chatConsent.checked,include_preferences:$('buddy-use-style')?.checked===true,include_cashflow:cashflowConsent.checked,include_diary:$('friday-chat-diary')?.checked===true});
          if(result.read_only!==true||result.money_moved!==false||result.payment_authorized!==false||!Array.isArray(result.actions_executed)||result.actions_executed.length)throw new Error('Unexpected chat authority');
          if(sentGeneration!==chatGeneration)return;
          const card=chatMessage('assistant',result.reply);if(result.evidence_ids.length)card.append(element('small',result.evidence_ids.length+' cited saved source(s) · user-supplied evidence or calculator scenario'));
          const screenLabels={review:'Open financial inbox',document:'Read a document',money:'View sandbox overview',activity:'Review recorded activity',settings:'Review my rules'};
          if(screenLabels[result.next_screen]){const next=element('button',screenLabels[result.next_screen]);next.type='button';next.dataset.screenLink=result.next_screen;card.append(next);}
          chatHistory.push({role:'user',text:message},{role:'assistant',text:result.reply});chatHistory=chatHistory.slice(-8);
          chatStatus.textContent=result.mode+' · '+result.model+' · Guidance only; no action executed.';
        }catch(error){if(sentGeneration!==chatGeneration)return;chatMessage('assistant','I couldn’t get a live Gemini reply. No payment or other action was performed. You can still review saved evidence.');chatStatus.textContent='Live chat unavailable. No canned financial answer was substituted.';}
        finally{chatBusy=false;button.disabled=false;chatClear.disabled=false;chatConsent.disabled=false;cashflowConsent.disabled=false;if($('friday-chat-diary'))$('friday-chat-diary').disabled=false;command.setAttribute('aria-busy','false');}}
      // Intercept the old bill form before its legacy execution handler runs.
      command.addEventListener('submit',event=>{event.preventDefault();event.stopImmediatePropagation();sendFridayChat();},true);
      $('home-command').addEventListener('keydown',event=>{if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){event.preventDefault();sendFridayChat();}});
      assistantState.replaceChildren(element('span','Chat on request · no background bank monitoring'));
    }
"""
