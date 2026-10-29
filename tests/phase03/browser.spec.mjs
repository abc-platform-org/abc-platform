import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8765';
test('synthetic Studio renders at three responsive viewports without document-level overflow',async({page})=>{
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:900});
  await page.goto(base+'/index.html');
  await expect(page.locator('.demo')).toContainText('نمایشی');
  await expect(page.locator('#title')).toHaveText('آغاز یک تجربهٔ شخصی');
  const shape=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));
  expect(shape.scrollWidth).toBeLessThanOrEqual(shape.clientWidth+2);
 }
});
test('complete synthetic salon journey never claims production execution',async({page})=>{
 await page.goto(base+'/index.html');
 await page.locator('#consent').check();await page.locator('#next').click();
 await page.locator('#next').click();
 await page.locator('#goal').selectOption('subtle');await page.locator('#maintenance').selectOption('low');await page.locator('#next').click();
 for(let i=0;i<3;i++)await page.locator('#next').click();
 await expect(page.locator('#title')).toHaveText('پیشنهادهای متناسب');
 await page.locator('#generate').click();
 await expect(page.locator('[data-select]').first()).toBeVisible();
 await page.locator('[data-select]').first().click();
 await expect(page.locator('#title')).toHaveText('ظاهر منتخب شما');
 await page.locator('#privacy').click();
 await expect(page.locator('#roleDialog')).toBeVisible();
 await page.locator('#enterPrivate').click();await expect(page.locator('#roleError')).toContainText('تأیید');
 await page.locator('#privateConfirm').check();await page.locator('#enterPrivate').click();
 await page.locator('#next').click();
 await page.locator('#feasible').check();await page.locator('#sop').check();await page.locator('#next').click();
 await page.locator('#qualified').check();await page.locator('#next').click();
 await page.locator('#next').click();await expect(page.locator('#title')).toHaveText('تحویل داخلی');
 await page.locator('#next').click();await expect(page.locator('#notice')).toContainText('رسید');
 await page.locator('#receipt').click();await page.locator('#next').click();
 await expect(page.locator('#title')).toHaveText('پایان جلسه');
 await expect(page.locator('#workspace')).toContainText('هیچ پرداخت، رزرو یا ارسال تصویری انجام نشده است.');
});
test('specialist modal restores focus; shared projection has no specialist SOP input',async({page})=>{
 await page.goto(base+'/index.html');
 await page.locator('#privacy').click();
 await page.locator('#roleDialog').press('Escape');
 await expect(page.locator('#roleDialog')).not.toBeVisible();
 await expect(page.locator('#privacy')).toBeFocused();
 await page.locator('#direction').click();
 await expect(page.locator('html')).toHaveAttribute('dir','ltr');
 await page.locator('#direction').click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.locator('#sop')).toHaveCount(0);
});
test('synthetic management permissions, branch switching, tentative booking and blocked receipt',async({page})=>{
 await page.goto(base+'/management.html');
 await page.locator('#role').selectOption('Client');
 await expect(page.locator('#heading')).toContainText('محدود');
 await expect(page.locator('#navigation button')).toHaveCount(0);
 await page.locator('#role').selectOption('Reception');
 await expect(page.locator('#branch')).toBeDisabled();
 await page.locator('[data-module="ABC-F03"]').click();
 await page.locator('#draft').click();
 await expect(page.locator('#notice')).toContainText('تداخل');
 await page.locator('#slot').selectOption('14:00');await page.locator('#draft').click();
 await expect(page.locator('#content')).toContainText('منتظر رسید');
 await page.locator('#confirm').click();
 await expect(page.locator('#notice')).toContainText('رسید معتبر');
 await page.locator('#role').selectOption('OrganizationOwner');
 await expect(page.locator('#branch')).toBeEnabled();
 await page.locator('#branch').selectOption('DEMO-BRANCH-02');
 await expect(page.locator('#notice')).toContainText('شعبهٔ نمایشی');
});
test('management module access cannot be elevated by reception to staff qualifications',async({page})=>{
 await page.goto(base+'/management.html');
 await expect(page.locator('[data-module="ABC-F07"]')).toHaveCount(0);
 await page.locator('#role').selectOption('SalonManager');
 await expect(page.locator('[data-module="ABC-F07"]')).toHaveCount(1);
 await page.locator('[data-module="ABC-F07"]').click();
 await expect(page.locator('#content')).toContainText('صلاحیت حرفه‌ای احراز نشده');
});
