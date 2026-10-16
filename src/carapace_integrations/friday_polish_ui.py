"""Small presentation corrections for the approved Soft Studio theme.

Append after the Studio overlays. Existing tokens, assets and native controls
remain the source of truth; this module has no runtime or financial authority.
"""

POLISH_CSS = r'''
/* Match the browser's native popups and date/check controls to the chosen theme. */
:root{color-scheme:light}
html[data-theme=light]{color-scheme:light}
html[data-theme=dark]{color-scheme:dark}

/* The approved mark is opaque. Blend its paper into the header in each theme. */
.topbar .mark{isolation:isolate;background:var(--panel)}
.topbar .mark img.everyday-team-brand{mix-blend-mode:multiply;filter:contrast(1.15)}
html[data-theme=dark] .topbar .mark img.everyday-team-brand{mix-blend-mode:screen;filter:invert(1) hue-rotate(180deg) contrast(1.3)}

/* Beat the historical dark-theme overrides using the current Studio tokens. */
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) :is(input:not([type]),input[type=text],input[type=search],input[type=email],input[type=url],input[type=tel],input[type=password],input[type=number],input[type=date],input[type=time],input[type=datetime-local],input[type=month],input[type=week],select,textarea:not([id=home-command])){
  appearance:none;-webkit-appearance:none;box-sizing:border-box;min-width:0;max-width:100%;min-height:46px;
  border:1px solid var(--line);border-radius:13px;background:var(--panel);color:var(--ink);box-shadow:none;
  font:inherit;line-height:1.5;padding:13px 15px;color-scheme:inherit;
}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) select{
  appearance:auto;-webkit-appearance:auto;padding-right:32px;cursor:pointer;
}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) select option{background:var(--panel);color:var(--ink)}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) :is(input,textarea)::placeholder{color:var(--muted);opacity:1}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) :is(input,textarea,select):focus-visible{
  outline:3px solid var(--blue)!important;outline-offset:3px;border-color:var(--blue);
}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) :is(input,textarea,select):disabled{opacity:.65;cursor:not-allowed}

:root .studio-workspace input[type=file]{
  box-sizing:border-box;width:100%;min-width:0;max-width:100%;padding:20px;
  border:1px dashed var(--line);border-radius:13px;background:var(--panel2);color:var(--ink);font:inherit;line-height:1.5;
}
:root .studio-workspace input[type=file]::file-selector-button{
  font:inherit;line-height:1.5;min-height:40px;padding:9px 13px;margin-right:12px;cursor:pointer;
  border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);box-shadow:none;
}
:root .studio-workspace input[type=file]::file-selector-button:hover{background:var(--studio-lilac);border-color:var(--blue)}
:root :is(.studio-workspace,.friday-preferences,.studio-dialog) input:is([type=checkbox],[type=radio]){
  appearance:auto;-webkit-appearance:auto;box-sizing:border-box;width:18px;height:18px;min-height:18px;
  padding:0;accent-color:var(--blue);color-scheme:inherit;flex:none;box-shadow:none;
}

/* Wrapper labels describe fields; only the editable control has an outline. */
:root .studio-workspace label.field{background:transparent;border:0;border-radius:0;padding:0;box-shadow:none;color:var(--ink)}
.studio-chat-dock .everyday-assistant{min-height:560px;height:min(760px,calc(100svh - 130px));max-height:760px}
.work-refund .shield-range span{background:#b7a0ed;opacity:.7}.work-refund .shield-range span+span{background:#68b89c;opacity:1}
@media(max-width:950px){.statement-coach .everyday-assistant{min-height:560px;height:min(760px,calc(100svh - 200px));max-height:760px}}
@media(max-width:600px){:root .studio-workspace input[type=file]{padding:16px}}
@media(max-width:600px){.work-layout .work-task{grid-row:1}.work-layout .work-chart{grid-row:2}}
'''
