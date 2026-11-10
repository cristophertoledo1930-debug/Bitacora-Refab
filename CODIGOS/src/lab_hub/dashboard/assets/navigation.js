(() => {
  const media = window.matchMedia('(max-width: 767px)');
  const apply = () => {
    for (const id of ['filters-panel', 'more-presets']) {
      const panel = document.getElementById(id);
      if (panel) panel.open = !media.matches;
    }
  };
  const labelInputs = () => {
    document.querySelectorAll('.filter .dash-dropdown').forEach(dropdown => {
      const label = document.getElementById('label-' + dropdown.id);
      if (dropdown.tagName === 'BUTTON' && label) {
        const ids = new Set((dropdown.getAttribute('aria-labelledby') || '').split(' ').filter(Boolean));
        ids.add(label.id);
        dropdown.setAttribute('aria-labelledby', [...ids].join(' '));
      } else {
        const input = dropdown.querySelector('input');
        if (input && label) { input.id = dropdown.id + '-input'; label.htmlFor = input.id; }
      }
    });
    for (const id of ['filter-start', 'filter-end']) {
      const input = document.getElementById(id);
      if (input) input.setAttribute('aria-describedby', 'date-error');
    }
    document.querySelectorAll('.dash-dropdown-search').forEach(input => { input.placeholder = 'Buscar…'; });
  };
  const capBars = (plot) => {
    if (plot.__refabSizing || !plot.data?.length || !plot._fullLayout) return;
    const horizontal = plot.data[0].orientation === 'h';
    const axis = horizontal ? plot._fullLayout.yaxis : plot._fullLayout.xaxis;
    const count = plot.data[0].x?.length || 1;
    const width = Math.min(.65, 24 * count / (axis?._length || 300));
    if (Math.abs((plot.data[0].width || 0) - width) < .001) return;
    plot.__refabSizing = true;
    window.Plotly.restyle(plot, {width}, [0]).finally(() => { plot.__refabSizing = false; });
  };
  const chartHooks = () => {
    document.querySelectorAll('.chart:not(.source-chart) .js-plotly-plot').forEach(plot => {
      if (!plot.__refabHooked && plot.on && window.Plotly) {
        plot.__refabHooked = true;
        plot.on('plotly_afterplot', () => capBars(plot));
        capBars(plot);
      }
    });
  };
  let initialized = false;
  const observer = new MutationObserver(() => {
    if (!initialized && document.getElementById('filters-panel')) { apply(); initialized = true; }
    labelInputs();
    chartHooks();
  });
  observer.observe(document.documentElement, {childList:true, subtree:true});
  media.addEventListener('change', apply);
})();
