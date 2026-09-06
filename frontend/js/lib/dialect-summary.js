// 家乡话摘要：给画廊选中某一方言族后的一行结论文本提供纯计算。
export function summarizeDialectFilms(movies) {
    if (!Array.isArray(movies) || movies.length === 0) return null;
    let ratingSum = 0;
    let yearMin = null;
    let yearMax = null;
    let earliest = null;
    let latest = null;
    for (const movie of movies) {
        ratingSum += Number(movie.rating) || 0;
        const year = Number(movie.year);
        if (!Number.isFinite(year)) continue;
        if (yearMin === null || year < yearMin) {
            yearMin = year;
            earliest = movie;
        }
        if (yearMax === null || year > yearMax) {
            yearMax = year;
            latest = movie;
        }
    }
    return {
        n: movies.length,
        mean: ratingSum / movies.length,
        yearMin,
        yearMax,
        earliest: earliest ? { title: earliest.title, year: earliest.year } : null,
        latest: latest ? { title: latest.title, year: latest.year } : null
    };
}
