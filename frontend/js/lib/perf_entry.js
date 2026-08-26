// Presentation-layer classifier: douban's wide catalog mixes stand-up comedy
// specials and concert recordings with films. They stay in the data, but
// rating-ranked surfaces hide them by default (toggle via the explorer).
const PERF_GENRE_PATTERN = /脱口秀|真人秀|演唱会|音乐会|演奏会|戏曲|演出/;
const PERF_TITLE_PATTERN = /栋笃笑|棟篤笑|演唱会|音[乐樂]会|演奏会/;

export function isPerformanceEntry(movie) {
    if (!movie) return false;
    if (PERF_GENRE_PATTERN.test(String(movie.genres || ''))) return true;
    return PERF_TITLE_PATTERN.test(String(movie.title || ''));
}
