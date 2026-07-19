import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ChartModule } from 'primeng/chart';

@Component({
    selector: 'app-admin-mrr-trend-chart',
    standalone: true,
    imports: [ChartModule],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `<p-chart type="line" [data]="data()" [options]="options()"></p-chart>`
})
export class AdminMrrTrendChartComponent {
    readonly data = input.required<Record<string, unknown>>();
    readonly options = input.required<Record<string, unknown>>();
}
