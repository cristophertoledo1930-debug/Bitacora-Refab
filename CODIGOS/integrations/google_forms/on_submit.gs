/** Form-bound installable event, never a spreadsheet trigger. */
function onFormSubmit(event) {
  if (!event || !event.response) throw new Error('Requiere evento de envío del formulario.');
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    forwardResponse_(event.response);
  } finally {
    lock.releaseLock();
  }
}

function forwardResponse_(response) {
  const config = integrationConfig_();
  const form = FormApp.openById(config.props.getProperty('FORM_ID'));
  const ids = JSON.parse(config.props.getProperty('FORM_ITEM_IDS'));
  const answers = {};
  response.getItemResponses().forEach(function (answer) {
    answers[answer.getItem().getId()] = String(answer.getResponse());
  });
  const payload = {response_id: response.getId(), submitted_at: response.getTimestamp().toISOString()};
  Object.keys(FORM_FIELDS).forEach(function (key) { payload[key] = answers[ids[key]] || ''; });
  const body = JSON.stringify(payload);
  const signed = Utilities.computeHmacSha256Signature(body, config.secret, Utilities.Charset.UTF_8);
  const signature = signed.map(function (byte) { return ('0' + (byte & 255).toString(16)).slice(-2); }).join('');
  let lastCode = 'red';
  for (let attempt = 0; attempt < 3; attempt++) {
    let res;
    try {
      res = UrlFetchApp.fetch(config.base + '/api/v1/integrations/google-forms', {
        method: 'post', contentType: 'application/json; charset=utf-8', payload: body,
        headers: {'X-Forms-Signature': signature, 'Idempotency-Key': payload.response_id},
        muteHttpExceptions: true, followRedirects: false, validateHttpsCertificates: true
      });
    } catch (networkError) {
      // Never expose request data or secret via an exception or a log.
      res = null;
    }
    if (res) {
      lastCode = res.getResponseCode();
      if (lastCode === 200 || lastCode === 201) {
        let ack;
        try { ack = JSON.parse(res.getContentText()); } catch (parseError) { ack = null; }
        if (ack && ack.id && ack.source === 'google_forms' &&
            ack.idempotency_key === 'gform:' + payload.response_id) {
          // PostgreSQL has committed. Keep no linked Sheet or extra response copy.
          form.deleteResponse(payload.response_id);
          return true;
        }
        throw new Error('Confirmación API inválida. Respuesta conservada en Forms.');
      }
      if (lastCode < 500 && lastCode !== 429 && lastCode !== 408) break;
    }
    if (attempt < 2) Utilities.sleep(1000 * Math.pow(2, attempt));
  }
  throw new Error('Entrega pendiente; HTTP ' + lastCode + '. Respuesta conservada en Forms.');
}

function retryPending() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const config = integrationConfig_();
    const form = FormApp.openById(config.props.getProperty('FORM_ID'));
    // Bounded batch stays within Apps Script execution limits.
    let pending = 0;
    form.getResponses().slice(0, 20).forEach(function (response) {
      try { forwardResponse_(response); } catch (error) { pending++; }
    });
    if (pending) throw new Error(pending + ' entregas siguen pendientes. Revise configuración/API.');
  } finally {
    lock.releaseLock();
  }
}
