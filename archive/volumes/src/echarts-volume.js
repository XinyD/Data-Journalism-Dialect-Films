import * as echarts from 'echarts/core';
import { ScatterChart, BarChart, LineChart, BoxplotChart } from 'echarts/charts';
import {
    GridComponent,
    TooltipComponent,
    MarkLineComponent,
    DatasetComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import dark from 'echarts/theme/dark.js';

echarts.use([
    ScatterChart,
    BarChart,
    LineChart,
    BoxplotChart,
    GridComponent,
    TooltipComponent,
    MarkLineComponent,
    DatasetComponent,
    CanvasRenderer
]);
echarts.registerTheme('dark', dark);
window.echarts = echarts;
