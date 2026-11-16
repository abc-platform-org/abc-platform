// Synthetic UX state model only. Production authority remains server-side.
export const journey=['CREATED','CONSENTED','INTENT_DEFINED','INPUTS_COLLECTING','INPUT_READY','ANALYZED','OPTIONS_READY','PREVIEW_REVIEW','LOOK_SELECTED','FEASIBILITY_REVIEW','PLAN_DRAFTED','SPECIALIST_REVIEW','HANDOFF','CLOSED'];
export const fresh=()=>({state:'CREATED',checkpoint:null,consent:false,textOnly:false,service:'hair',answers:{},quality:'PASS',qa:'PASS',role:'shared',privateScreen:false,qualified:false,sop:false,feasible:false,validated:null,receipt:false,online:true,version:1,selected:null,looks:[],active:null,redo:[],favorite:[],job:0,pending:null,locked:true,privacyRequests:[],events:[],notice:''});
const error=(s,n)=>({...s,notice:n});
export function reduce(s,a){
 let n=structuredClone(s); n.notice='';
 const terminal=['CLOSED','CLOSED_WITHOUT_DECISION','CANCELLED'].includes(s.state);
 if(a.type==='reset')return fresh();
 if(a.type==='requestPrivacyReview'){n.privacyRequests=[...s.privacyRequests,{kind:'REQUEST_NOT_SENT',sourceState:s.state}];n.notice='درخواست حریم خصوصی فقط در حافظهٔ نمونه ثبت شد؛ برای ارسال واقعی به سامانهٔ احراز هویت و حقوق داده نیاز است.';return n;}
 if(a.type==='shared'){n.role='shared';n.privateScreen=false;return n;}
 if(a.type==='role'){if(a.role!=='specialist'||!a.privateScreen||!s.online||terminal)return error(s,'ورود نمایشی متخصص نیازمند نمایشگر خصوصی و جلسهٔ فعال است.');n.role='specialist';n.privateScreen=true;return n;}
 if(a.type==='offline'){n.online=!s.online;return n;}
 if(terminal)return error(s,'جلسه پایان یافته است؛ جلسهٔ تازه بسازید.');
 if(a.type==='revoke'){n.consent=false;n.pending=null;n.job++;n.selected=null;n.validated=null;n.looks=[];n.active=null;n.redo=[];n.favorite=[];n.role='shared';n.privateScreen=false;n.sop=false;n.feasible=false;n.qualified=false;n.state='SAFETY_BLOCKED';n.checkpoint=null;n.notice='رضایت پس گرفته شد؛ تصاویر و پردازش نمونه متوقف شدند.';return n;}
 if(!s.online)return error(s,'اتصال قطع است؛ تغییر ثبت نمی‌شود.');
 if(a.type==='pause'){if(['PAUSED','SAFETY_BLOCKED','FAILED_RECOVERABLE','HANDOFF'].includes(s.state))return error(s,'توقف در این وضعیت مجاز نیست.');n.checkpoint=s.state;n.state='PAUSED';n.pending=null;n.job++;return n;}
 if(a.type==='resume'){if(!['PAUSED','FAILED_RECOVERABLE'].includes(s.state)||!s.checkpoint)return error(s,'نقطهٔ بازیابی معتبر وجود ندارد.');n.state=s.checkpoint;n.checkpoint=null;return n;}
 if(a.type==='cancel'){n.state='CANCELLED';n.pending=null;return n;}
 if(a.type==='closeEmpty'){if(!journey.slice(1,8).includes(s.state))return error(s,'پایان بدون انتخاب در این مرحله مجاز نیست.');n.state='CLOSED_WITHOUT_DECISION';return n;}
 if(['PAUSED','SAFETY_BLOCKED','FAILED_RECOVERABLE'].includes(s.state))return error(s,'ابتدا وضعیت توقف را حل کنید.');
 if(a.type==='set'){
 const allowed={consent:['CREATED'],textOnly:['CREATED'],service:['CONSENTED'],quality:['INPUTS_COLLECTING'],qa:['OPTIONS_READY','PREVIEW_REVIEW'],sop:['FEASIBILITY_REVIEW'],feasible:['FEASIBILITY_REVIEW'],qualified:['PLAN_DRAFTED','SPECIALIST_REVIEW'],locked:['PREVIEW_REVIEW']};
 if(!allowed[a.key]?.includes(s.state))return error(s,'این ورودی در مرحلهٔ فعلی قابل تغییر نیست.');
 if(['sop','feasible','qualified'].includes(a.key)&&(s.role!=='specialist'||!s.privateScreen))return error(s,'این تصمیم به محیط محافظت‌شدهٔ متخصص نیاز دارد.');
 if(a.key==='locked'&&a.value!==true)return error(s,'حفظ ناحیه‌های محافظت‌شده در این خدمت اجباری است.');
 n[a.key]=a.value;
 if(a.key==='textOnly'&&a.value===true)n.consent=false;
 if(a.key==='consent'&&a.value===true)n.textOnly=false;
 return n;
 }
 if(a.type==='answer'){if(s.state!=='INTENT_DEFINED')return error(s,'مرحلهٔ پرسش فعال نیست.');n.answers[a.key]=a.value;return n;}
 if(a.type==='favorite'){if(!s.looks.some(l=>l.id===a.id))return error(s,'نسخه یافت نشد.');n.favorite=s.favorite.includes(a.id)?s.favorite.filter(id=>id!==a.id):[...s.favorite,a.id];return n;}
 if(a.type==='reviewVersion'){if(s.state!=='PREVIEW_REVIEW'||!s.looks.some(l=>l.id===a.id))return error(s,'نسخهٔ معتبر برای مرور لازم است.');n.active=a.id;return n;}
 if(a.type==='undo'){const current=s.looks.find(l=>l.id===s.active);if(s.state!=='PREVIEW_REVIEW'||!current?.parent)return error(s,'نسخهٔ قبلی وجود ندارد.');n.redo.push(s.active);n.active=current.parent;return n;}
 if(a.type==='redo'){if(s.state!=='PREVIEW_REVIEW'||!s.redo.length)return error(s,'نسخه‌ای برای بازگردانی نیست.');n.active=n.redo.pop();return n;}
 if(a.type==='reviseSelected'){
 if(!['LOOK_SELECTED','FEASIBILITY_REVIEW','PLAN_DRAFTED','SPECIALIST_REVIEW'].includes(s.state)||s.role!=='specialist'||!s.privateScreen||!s.consent||!s.selected||!s.looks.some(l=>l.id===s.selected&&l.qa==='PASS')||s.receipt)return error(s,'اصلاح انتخاب نیازمند متخصص، وضعیت خصوصی، رضایت معتبر و نسخهٔ انتخاب‌شده است.');
 n.active=s.selected;n.selected=null;n.validated=null;n.sop=false;n.feasible=false;n.qualified=false;n.receipt=false;n.pending=null;n.job++;n.state='REVISION_REQUESTED';n.notice='انتخاب و تأییدهای وابسته نامعتبر شدند؛ نسخهٔ پیشین محفوظ است.';return n;
 }
 if(a.type==='generate'){
 if(!['OPTIONS_READY','PREVIEW_REVIEW','REVISION_REQUESTED'].includes(s.state)||!s.consent||s.textOnly||!s.locked)return error(s,'برای پیش‌نمایش، رضایت تصویری و قفل ناحیهٔ محافظت‌شده لازم است.');
 n.job++;n.pending=n.job;n.notice='در حال آماده‌سازی تصویر نمایشی…';return n;
 }
 if(a.type==='result'){
 if(!Number.isInteger(s.pending)||a.job!==s.pending||!s.consent||!['OPTIONS_READY','PREVIEW_REVIEW','REVISION_REQUESTED'].includes(s.state))return error(s,'نتیجهٔ بدون درخواست معتبر، قدیمی یا لغوشده کنار گذاشته شد.');
 n.pending=null;
 if(a.qa!=='PASS'){n.notice='کنترل کیفیت ناموفق؛ این نتیجه قابل انتخاب نیست.';return n;}
 const len=a.length??50,mode=a.mode??'transform',palette=a.palette??'natural',view=a.view??'front',region=a.region??(s.service==='beard'?'beard':'hair');
 if(!Number.isFinite(len)||len<10||len>90||!['transform','tryon','compare','inspiration'].includes(mode)||!['natural','warm','cool'].includes(palette)||view!=='front'||region!==(s.service==='beard'?'beard':'hair')){n.notice='پارامتر نامعتبر یا نمای بدون شواهد رد شد؛ نسخه‌ای ساخته نشد.';return n;}
 const lookSpec={service:s.service,mode,palette,region,view,provenance:'SYNTHETIC_ONLY'};
 n.looks.push({id:'LOOK-'+(s.looks.length+1),parent:s.active??s.looks.at(-1)?.id??null,qa:'PASS',length:len,locked:s.locked,lookSpec});n.active=n.looks.at(-1).id;n.redo=[];n.state='PREVIEW_REVIEW';return n;
 }
 if(a.type==='select'){if(s.state!=='PREVIEW_REVIEW'||!s.looks.some(l=>l.id===a.id&&l.qa==='PASS'))return error(s,'فقط نسخهٔ دارای کیفیت پذیرفته‌شده قابل انتخاب است.');n.selected=a.id;n.validated=null;n.state='LOOK_SELECTED';return n;}
 if(a.type==='fail'){if(!journey.slice(4,12).includes(s.state))return error(s,'این مرحله خطای پردازشی ندارد.');n.checkpoint=s.state;n.state='FAILED_RECOVERABLE';n.pending=null;return n;}
 if(a.type==='next'){
 const i=journey.indexOf(s.state);if(i<0||i===journey.length-1)return error(s,'گذار نامعتبر است.');
 if(s.state==='CREATED'&&!s.consent&&!s.textOnly)return error(s,'رضایت تصویری یا مسیر بدون تصویر را مشخص کنید.');
 if(s.state==='CONSENTED'&&!['hair','men','beard'].includes(s.service))return error(s,'این خدمت هنوز در دسترس نیست.');
 if(s.state==='INTENT_DEFINED'&&(!s.answers.goal||!s.answers.maintenance))return error(s,'هدف و زمان نگهداری را مشخص کنید.');
 if(s.state==='INPUTS_COLLECTING'&&s.quality!=='PASS'&&!s.textOnly)return error(s,'کیفیت ورودی کافی نیست؛ تصویر نمونه را بازبینی کنید.');
 if(s.state==='OPTIONS_READY')return error(s,s.textOnly?'مشاورهٔ متنی پایان یافته؛ بدون انتخاب تصویری جلسه را ببندید.':'ابتدا پیش‌نمایش را ایجاد کنید.');
 if(s.state==='PREVIEW_REVIEW')return error(s,'نسخهٔ مورد نظر را از گالری انتخاب کنید.');
 if(['LOOK_SELECTED','FEASIBILITY_REVIEW','PLAN_DRAFTED','SPECIALIST_REVIEW','HANDOFF'].includes(s.state)&&(s.role!=='specialist'||!s.privateScreen))return error(s,'برای ادامه وارد محیط محافظت‌شدهٔ متخصص شوید.');
 if(s.state==='FEASIBILITY_REVIEW'&&(!s.sop||!s.feasible))return error(s,'شواهد امکان‌پذیری و پروتکل معتبر لازم است.');
 if(s.state==='PLAN_DRAFTED'&&!s.qualified)return error(s,'صلاحیت متخصص هنوز تأیید نشده است.');
 if(s.state==='SPECIALIST_REVIEW'){if(!s.qualified||!s.sop||!s.feasible||!s.selected||!s.looks.some(l=>l.id===s.selected&&l.qa==='PASS'))return error(s,'شواهد معتبر و نسخهٔ انتخاب‌شده برای تأیید لازم است.');n.validated=s.selected;}
 if(s.state==='HANDOFF'&&!s.receipt)return error(s,'رسید تحویل داخلی هنوز دریافت نشده است.');
 n.state=journey[i+1];n.version++;n.events.push({from:s.state,to:n.state});return n;
 }
 if(a.type==='receipt'){if(s.state!=='HANDOFF'||s.validated!==s.selected||s.role!=='specialist'||!s.privateScreen||!s.qualified||!s.sop)return error(s,'تحویل معتبر نیست.');n.receipt=true;return n;}
 return error(s,'عملیات ناشناخته است.');
}
export function projection(s){const base={state:s.state,selected:s.selected,looks:s.consent?s.looks:[],consent:s.consent};return s.role==='specialist'&&s.privateScreen?{...base,sop:s.sop,qualified:s.qualified,validated:s.validated}:base;}
