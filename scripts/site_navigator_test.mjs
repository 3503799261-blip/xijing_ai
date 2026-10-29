/** Free deterministic routing tests; browser navigation is verified separately. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { TOPICS, findDestinations } from '../js/site-navigator.js';
const results = [];
const test = async (name, action) => { try { await action(); results.push({ name, pass: true }); } catch (error) { results.push({ name, pass: false, error: error.message }); } };
for (const [query, id] of [
  ['想了解京剧脸谱的含义', 'facial'], ['我想了解京剧历史', 'history'], ['四大徽班', 'origin'], ['梅兰芳', 'mei'], ['程砚秋', 'cheng'], ['谭鑫培', 'tan'],
  ['生旦净丑有什么区别', 'roles'], ['武生', 'sheng'], ['青衣', 'dan'], ['净角', 'jing'], ['小花脸', 'chou'], ['我想听西皮', 'xipi'], ['二黄', 'erhuang'],
  ['看看京胡', 'jinghu'], ['锣鼓经', 'percussion'], ['听唱段', 'audio'], ['演出录像', 'video'], ['戏服', 'costume'], ['演员照片', 'photos'],
  ['数字戏台', 'stage'], ['我想看３Ｄ模型', 'stage'], ['看周瑜的模型', 'zhouyu'], ['杜丽娘', 'duliniang'], ['穆桂英', 'muguiying'], ['智能问答', 'qa'], ['京剧', 'home'],
]) await test(`${query} -> ${id}`, () => assert.equal(findDestinations(query)[0]?.id, id));
await test('empty and unsupported query do not invent destinations', () => { for (const value of ['', '  ', null, {}, '没有收录的专题xyz', 'a'.repeat(121)]) assert.deepEqual(findDestinations(value), []); });
await test('multiple equally specific topics remain explicit choices', () => { const matches = findDestinations('西皮和二黄'); assert.equal(matches[0].score, matches[1].score); assert.deepEqual(new Set(matches.slice(0, 2).map((item) => item.id)), new Set(['xipi', 'erhuang'])); });
await test('single role characters cannot match arbitrary unrelated words', () => assert.equal(findDestinations('学生考试什么时候开始').length, 0));
await test('all destinations are fixed local pages with unique topic IDs', () => { assert.equal(new Set(TOPICS.map((item) => item.id)).size, TOPICS.length); for (const item of TOPICS) assert.match(item.href, /^(index|history|roles|facial|music|video|gallery|about)\.html(?:[?#].*)?$/); });
await test('every destination page and all eight integration links exist', async () => { const files = new Set(TOPICS.map((item) => item.href.split(/[?#]/)[0])); for (const file of files) { const html = await readFile(new URL('../' + file, import.meta.url), 'utf8'); assert.equal(html.split('css/site-navigator.css').length - 1, 1); assert.equal(html.split('js/site-navigator.js').length - 1, 1); } });
await test('navigator has no external or paid business call path', async () => { const source = await readFile(new URL('../js/site-navigator.js', import.meta.url), 'utf8'); assert.equal(/fetch\(|XMLHttpRequest|innerHTML|askOperaQuestion\(|submitModel|startAgentWorkflow/.test(source), false); });
const result = { at: new Date().toISOString(), kind: 'OFFLINE_LOCAL_NAVIGATION_ROUTING', results, passed: results.filter((item) => item.pass).length, failed: results.filter((item) => !item.pass).length, paidApiCalls: 0, neural4dCalls: 0 };
const index = process.argv.indexOf('--output'); if (index >= 0) await writeFile(process.argv[index + 1], JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2)); if (result.failed) process.exitCode = 1;
