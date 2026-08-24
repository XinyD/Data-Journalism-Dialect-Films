export function normalizeDetailText(value) {
    const text = String(value || '').trim();
    if (!text) return '';
    const normalized = text.toLocaleLowerCase();
    const missing = new Set(['nan', 'null', 'none', 'unknown', '<na>', '未知', '暂无数据', '暂无简介', '\\n', '\n']);
    return missing.has(normalized) ? '' : text;
}

export async function populateMovieDetail(movie, view) {
    const rating = Number(movie.rating);
    view.setField('year', `${movie.year || '未知'} · ${movie.decade || '未知年代'}`);
    view.setField('title', `《${movie.title || '未知'}》`);
    view.setField('rating', Number.isFinite(rating) ? `★ ${rating.toFixed(1)}` : '★ --');
    view.setField('genres', movie.genres);
    view.setField('votes', `${Number(movie.votes || 0).toLocaleString('zh-CN')} 人`);
    view.setField('groups', view.formatGroups(movie));
    view.setField('id', movie.movieId);
    ['director', 'countries', 'languages', 'source'].forEach(name => view.setField(name, '正在加载…'));
    view.setSynopsisVisible(true);
    view.setGeminiVisible(false);
    view.setField('synopsis', '正在加载简介…');
    view.applySourceLink(view.getSourceLink(), view.resolveSourceUrl(movie));
    view.setBusy(true);
    view.open();

    try {
        const details = await view.getMovieDetails(movie.movieId);
        if (!view.isCurrent(movie.movieId)) return;
        if (!details) throw new Error('Movie detail record is missing');

        view.setField('director', details.director || '暂无数据');
        view.setField('countries', details.productionCountries || '暂无数据');
        view.setField('languages', details.originalLanguages || '暂无数据');
        view.setField('source', details.source || '暂无数据');
        const summary = normalizeDetailText(details.summary);
        const generated = details.summaryKind === 1 && Boolean(summary);
        view.setSynopsisVisible(!generated);
        view.setGeminiVisible(generated);
        view.setField('synopsis', summary || '暂无可用简介');
        view.setField('gemini', summary || '暂无可用短评');
        view.applySourceLink(view.getSourceLink(), view.resolveSourceUrl(movie, details));
    } catch (error) {
        console.warn('Movie detail load failed', movie.movieId, error);
        if (!view.isCurrent(movie.movieId)) return;
        ['director', 'countries', 'languages', 'source'].forEach(name => view.setField(name, '暂无数据'));
        view.setSynopsisVisible(true);
        view.setGeminiVisible(false);
        view.setField('synopsis', '暂无可用简介');
        view.applySourceLink(view.getSourceLink(), view.resolveSourceUrl(movie));
    } finally {
        if (view.isCurrent(movie.movieId)) view.setBusy(false);
    }
}
