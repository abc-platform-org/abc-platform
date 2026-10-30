/* ABC in-salon prototype: deliberately offline, synthetic and ephemeral. */
"use strict";
(() => {
  const lookNames = Object.freeze({
    cool: "قهوه‌ای سرد", warm: "مسی گرم", dark: "تیره طبیعی"
  });
  const $ = (id) => document.getElementById(id);
  const state = { mode: "transform", look: "cool", selected: null };
  const modes = {
    transform: "Transform", tryon: "Try On", compare: "Compare",
    inspiration: "Inspiration", plan: "Technical Plan"
  };
  const setLabel = (id,text) => { $(id).textContent = text; };
  function render() {
    document.querySelectorAll("[data-mode]").forEach(button => {
      const active = button.dataset.mode === state.mode;
      button.classList.toggle("active",active);
      button.setAttribute("aria-pressed",String(active));
    });
    document.querySelectorAll("[data-look]").forEach(button => {
      const active=button.dataset.look === state.look;
      button.classList.toggle("active",active);
      button.setAttribute("aria-pressed",String(active));
    });
    $("after-hair").className="hair-shape "+(state.look==="cool"?"":state.look);
    setLabel("look-caption",lookNames[state.look]+" — فقط مدل شماتیک");
    setLabel("canvas-mode",modes[state.mode]+" / Demo");
    const activeRegions = ["HAIR"];
    if ($("skin").checked) activeRegions.push("SKIN");
    setLabel("region-label", "Editable: "+activeRegions.join(" + ")+" | FACE / BACKGROUND: LOCKED");
    setLabel("lock-status",state.selected
      ? "انتخاب آزمایشی: "+lookNames[state.selected]+
        " | فاقد امضای متخصص، رضایت معتبر و نسخه عملیاتی"
      : "هیچ گزینه‌ای انتخاب نشده");
    setLabel("evidence-text",$("service").value==="HAIR_COLOR"
      ?"سابقه شیمیایی و حساسیت: نامشخص"
      :"وضعیت اولیه و موارد منع خدمت: تأییدنشده");
    setLabel("plan-status","گیت ENG-06: BLOCKED — "+
      (state.selected?"Look فقط در نمونه انتخاب شده؛ ":"هنوز Look انتخاب نشده؛ ")+
      "شواهد، رضایت، SOP و اعتبارسنجی متخصص موجود نیست.");
    $("lock-look").textContent="انتخاب Look در نمونه آزمایشی";
    $("check-plan").disabled=false;
  }
  document.querySelectorAll("[data-mode]").forEach(button=>{
    button.addEventListener("click",()=>{state.mode=button.dataset.mode;render();});
  });
  document.querySelectorAll("[data-look]").forEach(button=>{
    button.addEventListener("click",()=>{state.look=button.dataset.look;render();});
  });
  $("lock-look").addEventListener("click",()=>{
    state.selected=state.look;render();
  });
  $("check-plan").addEventListener("click",()=>{
    state.mode="plan";render();
    setLabel("canvas-warning",
      "Technical Plan: BLOCKED. این صفحه هیچ دستور اجرایی یا پارامتر شیمیایی تولید نمی‌کند.");
  });
  $("service").addEventListener("change",()=>{
    state.selected=null;render();
  });
  ["hair","skin"].forEach(id=>$(id).addEventListener("change",render));
  $("reset").addEventListener("click",()=>{
    state.mode="transform";state.look="cool";state.selected=null;
    $("service").value="HAIR_COLOR";
    $("hair").checked=true;$("skin").checked=false;
    setLabel("canvas-warning","این شکل‌ها پیش‌نمایش شماتیک هستند، نه نتیجه تولیدشده از عکس مراجعه‌کننده.");
    render();
  });
  render();
})();
