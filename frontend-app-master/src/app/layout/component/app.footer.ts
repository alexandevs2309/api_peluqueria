import { Component } from '@angular/core';
import { AppConfigService } from '../../core/services/app-config.service';

@Component({
    standalone: true,
    selector: 'app-footer',
    template: `<div class="layout-footer">
        {{ appConfig.platformName() }}
    </div>`
})
export class AppFooter {
    constructor(public appConfig: AppConfigService) {}
}
