import * as echarts from 'echarts/core';
import { ScatterChart, EffectScatterChart } from 'echarts/charts';
import {
    GridComponent,
    TooltipComponent,
    GraphicComponent,
    MarkLineComponent,
    MarkAreaComponent,
    DatasetComponent,
    GeoComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import dark from 'echarts/theme/dark.js';

echarts.use([
    ScatterChart,
    EffectScatterChart,
    GridComponent,
    TooltipComponent,
    GraphicComponent,
    MarkLineComponent,
    MarkAreaComponent,
    DatasetComponent,
    GeoComponent,
    CanvasRenderer
]);
echarts.registerTheme('dark', dark);
window.echarts = echarts;
