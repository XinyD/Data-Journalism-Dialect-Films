import { DataService, renderLocalGallery } from './core.js';
import { isPerformanceEntry } from './lib/perf_entry.js';

document.addEventListener('DOMContentLoaded', async () => {
    await DataService.init({ slim: true });
    
    const filters = {
        decade: document.getElementById('filter-decade'),
        region: document.getElementById('filter-region'),
        language: document.getElementById('filter-language'),
        kind: document.getElementById('filter-kind')
    };

    function executeQuery() {
        const d = filters.decade.value;
        const r = filters.region.value;
        const l = filters.language.value;
        
        const kind = document.getElementById('filter-kind')?.value || 'films';
        let results = DataService.filter(d, r, l);
        if (kind === 'films') results = results.filter(movie => !isPerformanceEntry(movie));
        else if (kind === 'perf') results = results.filter(movie => isPerformanceEntry(movie));
        
        const titleParts = [];
        if(d !== 'All') titleParts.push(`年代: ${d}`);
        if(r !== 'All') titleParts.push(`地区: ${r.replace('_',' ')}`);
        if(l !== 'All') titleParts.push(`语言: ${filters.language.options[filters.language.selectedIndex].text}`);
        
        const queryTitle = titleParts.length > 0 
            ? `交叉筛选：${titleParts.join('；')}（n=${results.length.toLocaleString('zh-CN')}）`
            : `全部电影（n=${results.length.toLocaleString('zh-CN')}）`;

        renderLocalGallery(results, queryTitle, 'movie-grid', 50);
    }

    // Bind change events
    Object.values(filters).forEach(select => {
        select.addEventListener('change', executeQuery);
    });

    // Initial load
    executeQuery();
});
