// ABC Phase 03: synthetic management-only UX state, NOT real backend authorization.
export const ROLES=['Client','Specialist','Reception','SalonManager','OrganizationOwner','PlatformOperator'];
export const MODULES=Object.freeze([
 ['ABC-F01','نمای کلی','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F02','جست‌وجو','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F03','تقویم','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F04','مشتریان','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F05','استودیوی هوش مصنوعی','MVP',['Specialist','SalonManager','OrganizationOwner']],
 ['ABC-F06','برنامهٔ فنی','MVP',['Specialist']],
 ['ABC-F07','تیم و صلاحیت‌ها','MVP',['SalonManager','OrganizationOwner']],
 ['ABC-F08','خدمات','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F09','فروش و صندوق','V2',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F10','موجودی','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F11','بازاریابی','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F12','تحلیل کسب‌وکار','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F13','اتوماسیون','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F14','بازخورد','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F15','Ask ABC','V2',['SalonManager','OrganizationOwner']],
 ['ABC-F16','اعلان‌ها','MVP',['Reception','SalonManager','OrganizationOwner']],
 ['ABC-F17','چندشعبه‌ای','V3',['OrganizationOwner']],
 ['ABC-F18','تنظیمات و حاکمیت','MVP',['SalonManager','OrganizationOwner']]
].map(([id,name,phase,roles])=>({id,name,phase,roles})));
const appts=Object.freeze([{id:'DEMO-A01',slot:'10:00',staff:'DEMO-STAFF-01'},{id:'DEMO-A02',slot:'11:30',staff:'DEMO-STAFF-02'}]);
const services=Object.freeze([{id:'hair',title:'کوتاهی مو'},{id:'men',title:'موی مردانه'},{id:'beard',title:'ریش'}]);
export const freshManagement=(role='Reception')=>({role:ROLES.includes(role)?role:'Client',module:'ABC-F01',branch:'DEMO-BRANCH-01',epoch:1,search:'',draft:null,notice:''});
export const allowed=(role,module)=>ROLES.includes(role)&&MODULES.some(m=>m.id===module&&m.roles.includes(role));
const issue=(s,notice)=>({...s,notice});
export function managementReduce(s,a){
 const n={...s,notice:''};
 if(a.type==='simulateRole'){if(!ROLES.includes(a.role))return issue(s,'نقش آزمایشی نامعتبر است.');return {...freshManagement(a.role),branch:s.branch,epoch:s.epoch+1,notice:'نقش نمایشی تغییر کرد؛ این احراز هویت نیست.'};}
 if(a.type==='navigate'){if(!allowed(s.role,a.module))return issue(s,'دسترسی این نقش به این صفحه مجاز نیست.');return {...n,module:a.module,draft:null};}
 if(a.type==='switchBranch'){if(s.role!=='OrganizationOwner'||!['DEMO-BRANCH-01','DEMO-BRANCH-02'].includes(a.branch))return issue(s,'تغییر شعبه نیازمند مجوز مالک سازمان است.');return {...n,branch:a.branch,epoch:s.epoch+1,draft:null,search:'',notice:'شعبهٔ نمایشی تغییر کرد و پیش‌نویس پیشین باطل شد.'};}
 if(a.type==='search'){if(!allowed(s.role,'ABC-F02')||s.module!=='ABC-F02')return issue(s,'جست‌وجو برای این نقش مجاز نیست.');return {...n,search:String(a.query??'').slice(0,80)};}
 if(a.type==='draftBooking'){
  if(!allowed(s.role,'ABC-F03')||s.module!=='ABC-F03')return issue(s,'ایجاد نوبت مجاز نیست.');
  if(!['10:00','11:30','14:00','16:00'].includes(a.slot)||!['DEMO-STAFF-01','DEMO-STAFF-02'].includes(a.staff))return issue(s,'بازه یا نیروی نمونه نامعتبر است.');
  if(appts.some(x=>x.slot===a.slot&&x.staff===a.staff))return issue(s,'تداخل نوبت در Fixture؛ هیچ نوبتی ایجاد نشد.');
  return {...n,draft:{type:'BOOKING_PROPOSAL',slot:a.slot,staff:a.staff,branch:s.branch,epoch:s.epoch,status:'AWAITING_REAL_RECEIPT'},notice:'فقط پیش‌نویس نمایشی؛ نوبت واقعی ثبت نشده است.'};
 }
 if(a.type==='requestConfirmation'){
  if(!allowed(s.role,'ABC-F03')||s.module!=='ABC-F03'||s.draft?.type!=='BOOKING_PROPOSAL'||s.draft.branch!==s.branch||s.draft.epoch!==s.epoch)return issue(s,'پیش‌نویس معتبر همین شعبه وجود ندارد.');
  return issue(s,'فقط API واقعی می‌تواند رسید معتبر بدهد؛ این نمونه هیچ نوبتی تأیید نمی‌کند.');
 }
 if(a.type==='proposeCampaign'){if(!allowed(s.role,'ABC-F11')||s.module!=='ABC-F11')return issue(s,'مجوز پیشنهاد کمپین وجود ندارد.');return {...n,draft:{type:'CAMPAIGN_PROPOSAL',branch:s.branch,status:'NEEDS_CONSENT_AND_APPROVAL'},notice:'پیشنهاد نمایشی؛ هیچ پیام تبلیغاتی ارسال نشد.'};}
 if(a.type==='executeSensitive')return issue(s,'پرداخت، تغییر موجودی، ارسال کمپین و تغییر نقش در نمونه مسدود است.');
 return issue(s,'عملیات نامعتبر است.');
}
export function managementProjection(s){
 const modules=MODULES.filter(m=>allowed(s.role,m.id));
 const module=allowed(s.role,s.module)?s.module:null;
 const common={role:s.role,module,branch:s.branch,modules,synthetic:true,notice:s.notice};
 if(!module)return {...common,denied:true};
 if(module==='ABC-F01')return {...common,kpis:null,schedule:appts.map(x=>({id:x.id,slot:x.slot,status:'SYNTHETIC'}))};
 if(module==='ABC-F02')return {...common,search:s.search,results:s.search.trim()?[{id:'DEMO-CLIENT-01',label:'پروندهٔ غیرواقعی بدون اطلاعات هویتی'}]:[]};
 if(module==='ABC-F03')return {...common,appointments:appts.map(x=>({...x,status:'SYNTHETIC'})),draft:s.draft?.type==='BOOKING_PROPOSAL'?{...s.draft}:null};
 if(module==='ABC-F04')return {...common,clients:[{id:'DEMO-CLIENT-01',consent:'NOT_GRANTED',history:'NOT_LOADED'}]};
 if(module==='ABC-F07')return {...common,team:[{id:'DEMO-STAFF-01',qualification:'NOT_VERIFIED'},{id:'DEMO-STAFF-02',qualification:'NOT_VERIFIED'}]};
 if(module==='ABC-F08')return {...common,services:services.map(x=>({...x,release:'NOT_RELEASED'}))};
 if(module==='ABC-F11')return {...common,draft:s.draft?.type==='CAMPAIGN_PROPOSAL'?{...s.draft}:null};
 if(module==='ABC-F16')return {...common,notifications:[{id:'DEMO-N01',text:'اعلان نمونه؛ رویداد واقعی دریافت نشده است.'}]};
 return {...common,empty:'این ماژول در نقشهٔ محصول تعریف شده اما اتصال اجرایی و دادهٔ واقعی در فاز بعدی توسعه می‌یابد.'};
}
