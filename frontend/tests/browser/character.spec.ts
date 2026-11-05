import {test,expect} from '@playwright/test';
import path from 'node:path';
test('template-capability-driven character choices are visual, keyboard usable and multilingual',async({page},info)=>{
 await page.goto('/#/personalize/sky-whale');await page.getByLabel('Child’s name',{exact:true}).fill('Maya');
 await page.getByRole('button',{name:'Deep',exact:true}).click();await page.getByRole('button',{name:'Long',exact:true}).click();await page.getByLabel('Glasses',{exact:true}).check();await page.getByLabel('Freckles',{exact:true}).check();
 await expect(page.locator('.character-intro [data-character]')).toHaveAttribute('data-character',/"skin":"deep"/);
 await expect(page.getByRole('button',{name:'Deep',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Adventure hat'}).focus();await page.keyboard.press('Enter');await expect(page.getByRole('button',{name:'Adventure hat'})).toHaveAttribute('aria-pressed','true');
 await page.screenshot({path:path.resolve(`../docs/frontend-screenshots/character-premium-${info.project.name}.png`),fullPage:true,animations:'disabled'});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByLabel('Interface language').selectOption('he');await expect(page.getByRole('button',{name:'כהה',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.goto('/#/personalize/bear-hug');await expect(page.locator('.character-builder')).toHaveCount(0);
 await page.getByLabel('שפת הממשק').selectOption('en');await page.goto('/#/books');await page.getByLabel('Sort books').selectOption('title');await expect(page.locator('.book-card h3').first()).toContainText('A Hug');
 await page.goto('/#/books/sky-whale');await page.getByRole('button',{name:'Character preview',exact:true}).click();await expect(page.locator('.product-stage .character-portrait')).toBeVisible();
});
