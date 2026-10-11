"""Presentation-only soft midnight palette. Financial semantics stay untouched."""

SOFT_CSS = r"""<style id="friday-soft-theme">
:root{--ink:#171522;--surface:#242033;--muted:#c0b8ce;--line:#494059;--jade:#a7e9cd;--lime:#cbb9ff;--cyan:#cbb9ff;--red:#ff9fae;--friday-live:#a7e9cd;--friday-held:#ff9fae;--friday-review:#ffd6a7;--soft-text:#faf5ff;--soft-lilac:#cbb9ff;--soft-peach:#ffcfb5}
body{background:#171522!important;background-image:radial-gradient(ellipse at 82% 5%,rgba(164,130,217,.12),transparent 50%)!important;color:var(--soft-text)}
.topbar{background:#1b1827!important;border-color:#3f374e!important}.brand{color:var(--soft-text)}.brand small{color:#c0b8ce}
.friday-nav button{color:#d2c8e0!important;border-radius:999px!important;font-weight:500}
.friday-nav button[aria-current="page"]{background:#3d315a!important;color:#e8deff!important;border-color:#8f78b6!important}
.simple-more>summary{color:#d2c8e0}.simple-more[open]>div{background:#282237;border-color:#625375;border-radius:20px;box-shadow:0 18px 50px #0e0b1c66}
.topbar .pill{background:#292338;border-color:#5d4d75;color:#e2d4ef}.journey-sandbox{color:#ffe0c5!important;border-color:#8e6c5a!important;background:#332831;border-radius:999px}
button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible,textarea:focus-visible{outline-color:#d9c8ff!important}
.screen-heading h1,.journey-plan-heading h2,.journey-budget dd{color:var(--soft-text);font-weight:650}
.screen-heading p,.friday-view p,.friday-view small,.friday-view label,.journey-plan-heading p{color:#c0b8ce}
.simple-home .hero{gap:28px!important;min-height:285px!important}
.simple-home .hero h2{color:#faf5ff!important;font-weight:650!important;font-size:clamp(32px,3.5vw,48px)!important;letter-spacing:-.045em!important;line-height:1.14!important}
.simple-home .hero p{color:#c9bfd7!important}.simple-home .permission-note{color:#beb3ce!important}
.simple-home .home-command{padding:7px!important;border:1px solid #645575!important;background:#262031!important;border-radius:24px!important;gap:8px!important}
.simple-home .home-command input{border:0!important;background:transparent!important;border-radius:18px!important;min-width:0;padding-left:16px!important;color:var(--soft-text)!important}
.friday-view .run,.friday-primary-plan .run,.simple-home .home-command .run,.journey-handle{background:#cbb9ff!important;border-color:#cbb9ff!important;color:#291e3e!important;border-radius:18px!important;font-weight:650;box-shadow:0 4px 16px #b692ff18!important}
.friday-view .planner,.planRefresh,.screen-back,.simple-money-picker button,.activity-tools button{background:#2c253a!important;color:#e5d9f4!important;border-color:#645375!important;border-radius:16px}
.friday-view .card,.money-section,.simple-fold,.friday-work,.outcome-summary,.assurance-board,.run-source,.permission-card,.demo-controls,.scenario,.metric,.brief-main,.money-stat{background:#242033!important;border-color:#494059!important;border-radius:24px!important;box-shadow:0 8px 30px #0b08191c!important}
.friday-view .field,.friday-view textarea,.activity-tools input,.form-grid input,.form-grid select{background:#1c1929!important;border-color:#655876!important;color:var(--soft-text)!important;border-radius:16px}
input::placeholder,textarea::placeholder{color:#ada1bd!important}
.journey-companion b{font-weight:600;color:#e5d6ff}.journey-companion p,.journey-companion small{color:#c3b5d0!important}
.journey-home-assistant{padding:16px;border-radius:32px;background:radial-gradient(ellipse at 50% 40%,#b59bff0d,transparent 70%)}
.journey-home-assistant b{font-size:23px!important}.journey-companion[data-state="complete"] b{color:#a7e9cd}.journey-companion[data-state="held"] b{color:#ffafbb}.journey-companion[data-state="attention"] b{color:#ffd6a7}
.simple-home .task-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px!important}
.simple-home .task-tile{min-height:88px!important;padding:20px!important;border-radius:22px!important;text-align:left;border-color:#756197!important;background:#322746!important;color:#efddff!important;position:relative}
.simple-home .task-tile:nth-child(1){background:#322746!important;border-color:#756197!important;color:#efddff!important}
.simple-home .task-tile:nth-child(2){background:#3c2935!important;border-color:#8c6575!important;color:#ffdfdd!important}
.simple-home .task-tile:nth-child(3){background:#233934!important;border-color:#568579!important;color:#c8f1e2!important}
.simple-home .task-tile:nth-child(4){background:#3b3226!important;border-color:#88775b!important;color:#ffe4be!important}
.simple-home .task-tile b{font-size:15px!important;font-weight:550!important;display:block;padding-right:18px}
.simple-home .task-tile:after{content:'';position:absolute;right:20px;top:24px;width:8px;height:8px;border-top:1.5px solid currentColor;border-right:1.5px solid currentColor;opacity:.7}
.simple-home .task-tile:before{content:'';position:absolute;right:19px;top:29px;width:12px;height:1.5px;background:currentColor;transform:rotate(-45deg);opacity:.7}
.simple-home .task-tile:hover{filter:brightness(1.12);border-color:#e1caff!important}
.journey-home-overview{padding:24px!important;border:1px solid #494059!important;border-radius:24px;background:#242033!important;margin:24px 0!important}
.journey-home-overview h2{font-size:21px;font-weight:600;color:#f3eaff}.journey-home-overview .money-row{border-color:#494059!important}
.journey-home-overview button{background:#3b3050!important;border-color:#807090!important;color:#eedfff!important;border-radius:16px}
.journey-home-status,.journey-detail-status{color:#ffd6a7!important}
.journey-budget{background:#242033;border-color:#53465f;border-radius:24px}.journey-budget>div+div{border-color:#53465f}.journey-budget dt,.journey-budget .budget-note,.journey-budget .meter-label{color:#c7bbd5}.journey-budget meter{accent-color:#cbb9ff}
.journey-bill-select{color:#f2eaff;border-bottom-color:#494059;border-radius:18px;margin-bottom:8px}
.journey-bill-select[aria-pressed="true"]{background:#352a49!important;border-color:#947cbb!important;border-left-color:#cbb9ff!important;border-radius:18px}
.journey-bill-select small,.journey-steps small{color:#c6b7d1}.journey-date-tag{background:#ffcfb5;color:#492c31}
.journey-bill-detail,.journey-selected-facts{border-color:#53465f}.journey-steps li{color:#e6dced;border-left-color:#756583}.journey-steps li:before{background:#171522;border-color:#d4c3e7}
.journey-attention{background:#3b2d27;border-color:#a87b5e;color:#ffe1c1;border-radius:20px}
.activity-list{gap:12px}.activity-entry{border:1px solid #494059!important;border-radius:20px!important;background:#242033!important}.activity-tools button[aria-pressed="true"]{background:#46335e!important;border-color:#cbb9ff!important}
.activity-entry .status{background:#342a42}.activity-entry .status.good{color:#a7e9cd}.activity-entry .status.held{color:#ffafbb}
.friday-work dl>div{background:#30283f;border-color:#594b68;border-radius:16px}.friday-work dd{color:#d9c5ff}.friday-work dt{color:#c8bad5}
[data-state="complete"] .outcome-summary,[data-state="complete"] .verdict{background:#233a34!important;border-color:#75b69e!important}
[data-state="held"] .outcome-summary,[data-state="held"] .verdict{background:#422933!important;border-color:#c67c8d!important}
[data-state="attention"] .outcome-summary{background:#3e3027!important;border-color:#c19d72!important}
.stage{border-radius:18px!important}.stage.done{background:#253b35!important;border-color:#709c8d!important}.stage.blocked{background:#422b34!important;border-color:#b67b8b!important}
@media(hover:hover) and (prefers-reduced-motion:no-preference){button{transition:transform .18s ease,background-color .18s ease,border-color .18s ease,box-shadow .18s ease}button:not(:disabled):hover{transform:translateY(-2px)}button:not(:disabled):active{transform:translateY(0)}}
html[data-motion="off"] button{transition:none!important;transform:none!important}
@media(max-width:720px){.simple-home .task-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.simple-home .task-tile{min-width:0!important;padding:17px!important;min-height:80px!important}.simple-home .home-command{border-radius:22px!important}.simple-home .hero h2{font-size:34px!important}.journey-home-assistant{padding:10px!important}.journey-home-overview{padding:20px!important}.journey-budget{border-radius:20px}.journey-bill-detail{border-color:#53465f}}
</style>"""
