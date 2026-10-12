"""Conversational right panel plus an explicit read-only sample-bank page."""
CHAT_CSS = """
.friday-chat-log{display:grid;gap:10px;max-height:310px;overflow-y:auto;margin:16px 0;overscroll-behavior:contain}
.friday-chat-message{border-radius:15px;padding:12px 14px;background:#273854;font-size:13px;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere}
.friday-chat-message[data-speaker=user]{background:#fce0d5;color:#432b24;margin-left:22px}
.friday-chat-message b{display:block;font-size:11px;margin-bottom:5px;letter-spacing:.03em}
.friday-chat-consent{display:flex;gap:9px;font-size:11px;color:#d7e0ef;line-height:1.6;margin:14px 0;cursor:pointer}
.friday-chat-consent input{width:18px;height:18px;flex:none;accent-color:#f08869}
.friday-chat-tools{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}.friday-chat-tools button{font-size:11px;min-height:36px;border:1px solid #74839c;color:#f3f6ff;background:transparent;border-radius:12px;padding:7px 10px}
.friday-chat-tools button:hover{background:#314364}.friday-chat-message button{display:block;margin-top:10px;font-size:11px;min-height:36px;background:#e5edfa;color:#1a3158;border-radius:10px}
.friday-chat-status{color:#cfdbef;font-size:11px;line-height:1.6;min-height:24px}.bank-ledger-list{display:grid;gap:10px;margin-top:20px}.bank-ledger-row{display:flex;justify-content:space-between;gap:15px;border-bottom:1px solid var(--line);padding:14px 0}.bank-ledger-row small{display:block;color:var(--muted);font-size:12px;margin-top:6px}
"""

CHAT_JS = r"""
      // Navigation suggestions never execute a financial action.
      titles.bank='Your sandbox bank';
      const bankView=view('bank','Live read-only records from a provisioned Bank of Anthos sample account.');
      const bankStatus=element('p','No account is assumed until the connector responds.','screen-note');bankStatus.setAttribute('role','status');
      const bankRefresh=element('button','Refresh sandbox bank','planner');bankRefresh.type='button';
      const bankContents=element('div');bankView.append(bankStatus,bankRefresh,bankContents);
      const bankNav=element('button','Sandbox bank');bankNav.type='button';bankNav.dataset.screenLink='bank';nav.append(bankNav);
      let bankBusy=false;
      async function refreshBank(){if(bankBusy)return;bankBusy=true;bankRefresh.disabled=true;bankStatus.textContent='Reading your provisioned sample account. No money is being moved.';bankContents.replaceChildren();
        try{const data=await jsonRequest('/api/friday/bank');if(data.scope!=='BANK_OF_ANTHOS_ARTIFICIAL_MONEY'||data.read_only!==true||data.money_moved!==false)throw new Error('Unexpected bank scope');
          bankStatus.textContent=data.status+' · '+data.reason;
          if(data.status==='CONNECTED'){const summary=element('article',null,'money-section');summary.append(element('h2','Sample account ending '+data.account_last4),element('p','Ledger balance: '+data.balance_minor.toLocaleString('en-IN')+' minor ledger units'),element('p','Currency is not recorded by Anthos. These are not your Friday INR sandbox funds.'),element('small','Snapshot: '+data.as_of+' · Last '+data.transactions.length+' of '+data.total_records+' records'));bankContents.append(summary);
            const rows=element('div',null,'bank-ledger-list');data.transactions.forEach(t=>{const row=element('article',null,'bank-ledger-row');const detail=element('div');detail.append(element('b',t.direction+' · transaction '+t.transaction_id),element('small','Other account ending '+t.counterparty_last4+' · '+t.timestamp));row.append(detail,element('span',t.amount_minor.toLocaleString('en-IN')+' minor units'));rows.append(row);});bankContents.append(rows);
          }else bankContents.append(element('p','Google sign-in opens your private Friday workspace. It does not authenticate a bank account. An operator must provision a separate artificial account; no shared visitor account is used.','screen-note'));
          data.limits.forEach(line=>bankContents.append(element('p',line,'screen-note')));
        }catch(error){bankStatus.textContent='Bank snapshot unavailable. No balance or successful payment is assumed.';}finally{bankBusy=false;bankRefresh.disabled=false;}}
      bankRefresh.addEventListener('click',refreshBank);
      const priorChatShow=show;show=function(name,push=true){priorChatShow(name,push);if(name==='bank')refreshBank();};
      const chatLog=element('div',null,'friday-chat-log');chatLog.id='friday-chat-log';chatLog.setAttribute('role','log');chatLog.setAttribute('aria-label','Conversation with Friday');chatLog.setAttribute('aria-live','polite');
      const chatConsent=element('input');chatConsent.type='checkbox';chatConsent.id='friday-chat-workspace';
      const chatConsentLabel=element('label',' Include my recent financial inbox and sandbox summary in Gemini’s answer','friday-chat-consent');chatConsentLabel.prepend(chatConsent);
      const chatStatus=element('p','Replies use Gemini. Chat cannot submit payments or change bank records.','friday-chat-status');chatStatus.setAttribute('role','status');
      let chatBusy=false;let chatHistory=[];
      function chatMessage(speaker,text){const card=element('article',null,'friday-chat-message');card.dataset.speaker=speaker;card.append(element('b',speaker==='user'?'You':'Friday'),element('div',text));chatLog.append(card);chatLog.scrollTop=chatLog.scrollHeight;return card;}
      function clearChat(){chatHistory=[];chatLog.replaceChildren();chatStatus.textContent='Conversation cleared from this page. No payment or bank action was performed.';}
      chatConsent.addEventListener('change',clearChat);
      const chatTools=element('div',null,'friday-chat-tools');const chatClear=element('button','Clear chat');chatClear.type='button';chatClear.addEventListener('click',clearChat);
      const reviewFromChat=element('button','Review a bill or receipt');reviewFromChat.type='button';reviewFromChat.dataset.screenLink='bill';
      const bankFromChat=element('button','My sandbox bank');bankFromChat.type='button';bankFromChat.dataset.screenLink='bank';chatTools.append(reviewFromChat,bankFromChat,chatClear);
      everydayAssistant.querySelector('h2').textContent='Ask Friday.';
      everydayAssistant.querySelector('h2').nextElementSibling.textContent='Ask about a bill, an unfamiliar charge or what to check next. I’ll guide you through the evidence.';
      everydayAssistant.insertBefore(chatLog,command);everydayAssistant.insertBefore(chatConsentLabel,command);command.after(chatStatus,chatTools);
      $('home-command').placeholder='Why does this bill need checking? What should I do next?';$('home-command').maxLength=1600;
      $('home-command').setAttribute('aria-label','Message Friday');command.querySelector('button[type=submit]').textContent='Ask Friday';
      permissionNote.textContent='Chat text goes to Gemini on Google Cloud. Messages are not saved by Friday; replies may be wrong. Never enter a PIN, OTP or password.';
      async function sendFridayChat(){const field=$('home-command');const message=field.value.trim();if(!message)return;if(chatBusy){toast('Friday is still replying.');return;}
        chatBusy=true;const button=command.querySelector('button[type=submit]');button.disabled=true;chatClear.disabled=true;chatConsent.disabled=true;chatMessage('user',message);field.value='';chatStatus.textContent='Friday is thinking with Gemini… No financial action is being performed.';
        try{const result=await jsonRequest('/api/friday/chat','POST',{message,history:chatHistory.slice(-8),include_workspace:chatConsent.checked});
          if(result.read_only!==true||result.money_moved!==false||result.payment_authorized!==false||!Array.isArray(result.actions_executed)||result.actions_executed.length)throw new Error('Unexpected chat authority');
          const card=chatMessage('assistant',result.reply);if(result.evidence_ids.length)card.append(element('small',result.evidence_ids.length+' cited inbox case(s) · user-supplied evidence'));
          const screenLabels={review:'Open financial inbox',document:'Read a document',money:'View sandbox overview',activity:'Review recorded activity',settings:'Review my rules',bank:'Open sandbox bank'};
          if(screenLabels[result.next_screen]){const next=element('button',screenLabels[result.next_screen]);next.type='button';next.dataset.screenLink=result.next_screen;card.append(next);}
          chatHistory.push({role:'user',text:message},{role:'assistant',text:result.reply});chatHistory=chatHistory.slice(-8);
          chatStatus.textContent=result.mode+' · '+result.model+' · Guidance only; no action executed.';
        }catch(error){chatMessage('assistant','I couldn’t get a live Gemini reply. No payment or other action was performed. You can still review saved evidence.');chatStatus.textContent='Live chat unavailable. No canned financial answer was substituted.';}
        finally{chatBusy=false;button.disabled=false;chatClear.disabled=false;chatConsent.disabled=false;}}
      // Intercept the old bill form before its legacy execution handler runs.
      command.addEventListener('submit',event=>{event.preventDefault();event.stopImmediatePropagation();sendFridayChat();},true);
      $('home-command').addEventListener('keydown',event=>{if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){event.preventDefault();sendFridayChat();}});
      assistantState.replaceChildren(element('span','Chat on request · no background bank monitoring'));
"""
