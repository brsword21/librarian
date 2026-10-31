import test from 'node:test';
import assert from 'node:assert/strict';
import {calibration,evidenceF1,isAbstain} from '../data.js';
test('abstention recognizes a recorded insufficient-evidence answer',()=>{
 assert.equal(isAbstain({answer:'INSUFFICIENT_EVIDENCE'}),true);
 assert.equal(isAbstain({answer:'Ana Ferreira',abstained:false}),false);
});
test('citation F1 handles duplicate citations and penalizes extra passages',()=>{
 assert.equal(evidenceF1({answer:'a',cited:['a','a','b'],gold:{evidence:['a']}}),2/3);
 assert.equal(evidenceF1({abstained:true,cited:['a'],gold:{evidence:['a']}}),0);
});
test('calibration excludes unlabeled test records and distinguishes missing samples',()=>{
 const c=calibration([
  {route:'ssu',answer:'Ana',cited:['s1'],gold:{answer:'Ana',evidence:['s1'],abstain:false}},
  {route:'ssu',answer:'INSUFFICIENT_EVIDENCE',cited:[],gold:{answer:'not known',evidence:[],abstain:true}},
  {route:'ku',answer:'a fabricated score must not count',cited:['s1']},
 ]);
 assert.equal(c.n,2);assert.equal(c.strict,1);assert.equal(c.f1,1);assert.equal(c.abstain,1);
 assert.equal(c.byRoute.ku.score,null);assert.equal(c.byRoute.ku.n,0);
});
