/** Build a private draft. Publishing is an explicit action by the account owner. */
const FORM_FIELDS = {
  waste_type: 'Tipo de residuo', material: 'Material', machine: 'Máquina',
  cause: 'Causa del descarte', weight: 'Peso medido', unit: 'Unidad',
  station_code: 'Código de estación'
};

function integrationConfig_() {
  const props = PropertiesService.getScriptProperties();
  const base = (props.getProperty('API_BASE_URL') || '').replace(/\/$/, '');
  const secret = props.getProperty('GOOGLE_FORMS_SECRET');
  if (!/^https:\/\//i.test(base) || !secret) {
    throw new Error('Configure API_BASE_URL HTTPS y GOOGLE_FORMS_SECRET en propiedades.');
  }
  return {props: props, base: base, secret: secret};
}

function fetchCatalogs_() {
  const config = integrationConfig_();
  const res = UrlFetchApp.fetch(config.base + '/api/v1/catalogs', {
    muteHttpExceptions: true, followRedirects: false, validateHttpsCertificates: true
  });
  if (res.getResponseCode() !== 200) throw new Error('No se pudieron cargar los catálogos.');
  const catalogs = JSON.parse(res.getContentText());
  ['waste_types', 'materials', 'machines', 'causes'].forEach(function (key) {
    if (!Array.isArray(catalogs[key]) || !catalogs[key].length) {
      throw new Error('Catálogo vacío: ' + key);
    }
  });
  return catalogs;
}

function createForm() {
  const config = integrationConfig_();
  if (config.props.getProperty('FORM_ID')) {
    throw new Error('Ya existe FORM_ID. Use syncFormOptions; no se crear? un duplicado.');
  }
  const catalogs = fetchCatalogs_();
  const form = FormApp.create('Re-Fab · Lab881 | Registro de residuos', false);
  // Save immediately so a failure cannot silently create multiple forms.
  config.props.setProperty('FORM_ID', form.getId());
  form.setDescription('Registra tipo, material, máquina, causa y peso. La estación se precarga desde el QR. ' +
    'La respuesta queda pendiente hasta que el dashboard confirme su recepción.');
  form.setCollectEmail(false).setLimitOneResponsePerUser(false).setAllowResponseEdits(false);
  form.setConfirmationMessage('Respuesta recibida por Google Forms. El envío al dashboard se procesa en segundo plano.');
  const ids = {};
  [['waste_type', 'waste_types'], ['material', 'materials'], ['machine', 'machines'], ['cause', 'causes']]
    .forEach(function (pair) {
      const item = form.addListItem().setTitle(FORM_FIELDS[pair[0]]).setRequired(true)
        .setChoiceValues(catalogs[pair[1]].map(function (row) { return row.name; }));
      ids[pair[0]] = item.getId();
    });
  ids.weight = form.addTextItem().setTitle(FORM_FIELDS.weight).setRequired(true)
    .setHelpText('Número mayor que cero. Ejemplo: 125 g o 0.125 kg.')
    .setValidation(FormApp.createTextValidation().requireNumberGreaterThan(0)
      .setHelpText('Ingresa un peso numérico mayor que cero.').build()).getId();
  ids.unit = form.addListItem().setTitle(FORM_FIELDS.unit).setChoiceValues(['g', 'kg']).setRequired(true).getId();
  ids.station_code = form.addTextItem().setTitle(FORM_FIELDS.station_code).setRequired(false)
    .setHelpText('Precargado por QR. Déjalo vacío si no hay estación.').getId();
  config.props.setProperties({FORM_ITEM_IDS: JSON.stringify(ids), GOOGLE_FORM_URL: form.getPublishedUrl()});
  console.log('Borrador creado. Abrir y revisar: ' + form.getEditUrl());
  return form.getEditUrl();
}

function syncFormOptions() {
  const config = integrationConfig_();
  const form = FormApp.openById(config.props.getProperty('FORM_ID'));
  const ids = JSON.parse(config.props.getProperty('FORM_ITEM_IDS'));
  const catalogs = fetchCatalogs_();
  [['waste_type', 'waste_types'], ['material', 'materials'], ['machine', 'machines'], ['cause', 'causes']]
    .forEach(function (pair) {
      form.getItemById(ids[pair[0]]).asListItem().setChoiceValues(
        catalogs[pair[1]].map(function (row) { return row.name; }));
    });
}

function installTriggers() {
  const config = integrationConfig_();
  const form = FormApp.openById(config.props.getProperty('FORM_ID'));
  const existing = ScriptApp.getProjectTriggers().map(function (t) { return t.getHandlerFunction(); });
  if (existing.indexOf('onFormSubmit') < 0) ScriptApp.newTrigger('onFormSubmit').forForm(form).onFormSubmit().create();
  if (existing.indexOf('retryPending') < 0) ScriptApp.newTrigger('retryPending').timeBased().everyMinutes(5).create();
}

function stationPrefilledUrl() {
  const config = integrationConfig_();
  const station = config.props.getProperty('STATION_CODE');
  if (!station) throw new Error('Configure STATION_CODE en propiedades.');
  const form = FormApp.openById(config.props.getProperty('FORM_ID'));
  const ids = JSON.parse(config.props.getProperty('FORM_ITEM_IDS'));
  const stationItem = form.getItemById(ids.station_code).asTextItem();
  const url = form.createResponse().withItemResponse(stationItem.createResponse(station)).toPrefilledUrl();
  // The URL contains the real entry.<id>; item ID must not be assumed to be entry ID.
  console.log(url);
  return url;
}
