// Execute the real Apps Script sender with local service doubles.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const sender = fs.readFileSync('integrations/google_forms/on_submit.gs', 'utf8');
const fields = {waste_type:'Tipo', material:'Material', machine:'Máquina', cause:'Causa',
  weight:'Peso', unit:'Unidad', station_code:'Estación'};
function run(codes, networkFailure=false, validAck=true) {
  let calls=0, removed=0, waits=[];
  const response = {getId:()=> 'synthetic-id', getTimestamp:()=>new Date('2026-11-03T12:00:00Z'),
    getItemResponses:()=>Object.keys(fields).map(key=>({getItem:()=>({getId:()=>key}),
      getResponse:()=>({weight:'0.125',unit:'kg',station_code:'Láser 1'}[key] || 'code')}))};
  const props = {getProperty:key=>key==='FORM_ITEM_IDS' ? JSON.stringify(Object.fromEntries(Object.keys(fields).map(k=>[k,k]))) : 'synthetic-form'};
  const context = {FORM_FIELDS:fields, integrationConfig_:()=>({base:'https://example.test',secret:'test-secret',props}),
    FormApp:{openById:()=>({deleteResponse:id=>{assert.equal(id,'synthetic-id');removed++},getResponses:()=>[response]})},
    Utilities:{Charset:{UTF_8:'utf8'},computeHmacSha256Signature:(body,secret)=>Array.from(crypto.createHmac('sha256',secret).update(body).digest()),sleep:ms=>waits.push(ms)},
    LockService:{getScriptLock:()=>({waitLock:()=>{},tryLock:()=>true,releaseLock:()=>{}})},
    UrlFetchApp:{fetch:(url, options)=>{
      assert.equal(url,'https://example.test/api/v1/integrations/google-forms');
      assert.equal(options.followRedirects,false);
      assert.equal(options.headers['X-Forms-Signature'],crypto.createHmac('sha256','test-secret').update(options.payload).digest('hex'));
      const data=JSON.parse(options.payload);
      assert.equal(data.station_code,'Láser 1');
      assert.equal(options.headers['Idempotency-Key'],data.response_id);
      calls++;
      if(networkFailure) throw new Error('network');
      return {getResponseCode:()=>codes[Math.min(calls-1,codes.length-1)],
        getContentText:()=>JSON.stringify({id:'record-id',source:'google_forms',idempotency_key:validAck?'gform:synthetic-id':'incorrect'})};
    }}};
  vm.createContext(context); vm.runInContext(sender,context);
  let failed=false;
  try {context.onFormSubmit({response})} catch {failed=true}
  return {calls,removed,waits,failed};
}
assert.deepEqual(run([201]),{calls:1,removed:1,waits:[],failed:false});
assert.deepEqual(run([503,503,200]),{calls:3,removed:1,waits:[1000,2000],failed:false});
assert.deepEqual(run([401]),{calls:1,removed:0,waits:[],failed:true});
assert.deepEqual(run([409]),{calls:1,removed:0,waits:[],failed:true});
assert.deepEqual(run([422]),{calls:1,removed:0,waits:[],failed:true});
assert.deepEqual(run([429,201]),{calls:2,removed:1,waits:[1000],failed:false});
assert.deepEqual(run([],true),{calls:3,removed:0,waits:[1000,2000],failed:true});
assert.deepEqual(run([201],false,false),{calls:1,removed:0,waits:[],failed:true});
console.log('8 sender scenarios passed: UTF-8 HMAC, retries, ACK, retention/deletion.');
