import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ChartModule } from 'primeng/chart';

@Component({
    selector: 'app-admin-plan-revenue-chart',
    standalone: true,
    imports: [ChartModule],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `<p-chart type="doughnut" [data]="data()" [options]="options()"></p-chart>`
})
export class AdminPlanRevenueChartComponent {
    readonly data = input.required<Record<string, unknown>>();
    readonly options = input.required<Record<string, unknown>>();
}
